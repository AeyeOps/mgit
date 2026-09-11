"""A stationary sync panel with repository and Git-stage progress."""

import asyncio
import re
from dataclasses import dataclass, replace
from time import monotonic
from types import TracebackType
from typing import Literal

from rich.console import Console, Group
from rich.text import Text

from mgit.git.progress import GitProgress
from mgit.ui.progress import ProgressDisplay, progress_console

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")


def _literal(value: str) -> Text:
    return Text(_CONTROL_CHARACTERS.sub(" ", value), no_wrap=True)


def _fit(text: Text, width: int) -> Text:
    result = text.copy()
    result.truncate(max(0, width), overflow="ellipsis", pad=True)
    return result


def _with_metrics(label: Text, metrics: Text, width: int) -> Text:
    if metrics.cell_len >= width:
        return _fit(metrics, width)
    return _fit(label, width - metrics.cell_len - 1) + Text(" ") + metrics


def _duration(seconds: float) -> str:
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


@dataclass(frozen=True)
class _Repository:
    name: str
    stage: str
    percentage: int | None
    last_activity: float


class SyncProgress(ProgressDisplay):
    """Keep totals, counters, and the latest Git activity in three fixed rows."""

    def __init__(
        self,
        total: int | None = None,
        *,
        phase: str = "Discovering",
        console: Console | None = None,
        disable: bool = False,
    ) -> None:
        # Rich asks for the first renderable before Progress.live is assigned.
        self._panel_console = console or progress_console
        self._started_at = monotonic()
        self._total = total
        self._completed = 0
        self._skipped = 0
        self._failed = 0
        self._phase = phase
        self._message = "No repositories" if total == 0 else phase
        self._active: dict[str, _Repository] = {}
        super().__init__(
            console=self._panel_console,
            disable=disable,
            auto_refresh=not disable,
            refresh_per_second=10,
            expand=True,
        )

    @property
    def completed(self) -> int:
        """Number of repositories resolved in the current phase."""
        with self._lock:
            return self._completed

    @property
    def skipped(self) -> int:
        """Number of repositories skipped in the current phase."""
        with self._lock:
            return self._skipped

    @property
    def failed(self) -> int:
        """Number of repositories that failed in the current phase."""
        with self._lock:
            return self._failed

    @property
    def active_count(self) -> int:
        """Number of running repositories, including undisplayed workers."""
        with self._lock:
            return len(self._active)

    def begin_phase(
        self,
        phase: str,
        *,
        total: int | None,
        completed: int = 0,
        skipped: int = 0,
        failed: int = 0,
    ) -> None:
        """Replace phase counters without adding rows or resetting elapsed time."""
        with self._lock:
            self._total = total
            self._completed = completed
            self._skipped = skipped
            self._failed = failed
            self._phase = phase
            self._message = "No repositories" if total == 0 else phase
            self._active.clear()
        self.refresh()

    def start_repository(self, key: str, name: str, stage: str) -> None:
        """Show a repository as active before its first measured Git event."""
        with self._lock:
            self._active[key] = _Repository(name, stage, None, monotonic())
        self.refresh()

    def update_repository(self, key: str, event: GitProgress) -> None:
        """Record a Git stage independently of the repository completion count."""
        with self._lock:
            repository = self._active.pop(key)
            self._active[key] = replace(
                repository,
                stage=event.stage,
                percentage=event.percentage,
                last_activity=monotonic(),
            )
        # The regular refresh samples Git events without painting every line.

    def finish_repository(
        self, key: str, outcome: Literal["success", "skipped", "failed"]
    ) -> None:
        """Resolve one repository and remove it from the active display."""
        with self._lock:
            self._active.pop(key)
            self._completed += 1
            if outcome == "skipped":
                self._skipped += 1
            elif outcome == "failed":
                self._failed += 1
            if not self._active and self._completed == self._total:
                self._message = "Finished with failures" if self._failed else "Complete"
        self.refresh()

    def set_message(self, message: str) -> None:
        """Set the status shown when no repository is currently active."""
        with self._lock:
            self._message = message
        self.refresh()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_val is not None:
            with self._lock:
                self._active.clear()
                self._message = (
                    "Cancelled"
                    if isinstance(exc_val, (KeyboardInterrupt, asyncio.CancelledError))
                    else "Stopped"
                )
        super().__exit__(exc_type, exc_val, exc_tb)

    def get_renderable(self) -> Group:
        """Build a fresh, cell-aware layout for the current terminal dimensions."""
        with self._lock:
            total, completed = self._total, self._completed
            active_count, skipped, failed = (
                len(self._active),
                self._skipped,
                self._failed,
            )
            current = next(reversed(self._active.values()), None)
            phase = self._phase
            message = self._message
        width, height = self._panel_console.size
        now = monotonic()

        if total is None:
            metrics = Text(f"{completed}/?")
            fraction = 0
        else:
            fraction = completed / total if total else 1
            metrics = Text(f"{int(fraction * 100):3d}% {completed}/{total}")
        label = _literal(phase)
        label_width = min(label.cell_len, 12, max(0, width - metrics.cell_len - 6))
        label = _fit(label, label_width)
        if label_width:
            label.append(" ")
        bar_width = max(0, width - label.cell_len - metrics.cell_len - 1)
        filled = int(bar_width * fraction)
        bar = Text("━" * filled, style="bar.complete")
        bar.append("─" * (bar_width - filled), style="bar.back")
        overall = _fit(label + bar + Text(" ") + metrics, width)

        counts = Text(f"Active:{active_count} Skipped:{skipped} Failed:{failed}")
        elapsed = Text(_duration(now - self._started_at))
        if counts.cell_len + elapsed.cell_len + 1 > width:
            counts = Text(f"A:{active_count} S:{skipped} F:{failed}")
        counters = _with_metrics(counts, elapsed, width)

        if current is None:
            activity = _fit(_literal(message), width)
        else:
            seconds = int(now - current.last_activity)
            age = f"{seconds}s ago" if seconds < 60 else f"{seconds // 60}m ago"
            measured = "" if current.percentage is None else f"{current.percentage}% "
            metrics = Text(measured + age)
            available = max(0, width - metrics.cell_len - 1)
            stage = _literal(current.stage)
            stage_width = min(stage.cell_len, max(0, available * 2 // 3))
            name = _literal(current.name)
            name_width = min(name.cell_len, max(0, available - stage_width - 1))
            label = _fit(name, name_width)
            label.append(" ")
            label += _fit(stage, stage_width)
            activity = _with_metrics(label, metrics, width)

        rows = max(1, min(3, height - 1))
        if rows == 1:
            return Group(overall)
        if rows == 2:
            return Group(overall, activity)
        return Group(overall, counters, activity)

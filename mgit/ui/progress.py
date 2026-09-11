"""Shared, compact progress displays and console logging coordination."""

import logging

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Column

progress_console = Console(stderr=True)
_active_displays: set[Progress] = set()


class ProgressDisplay(Progress):
    """Coordinate console logs and reusable indeterminate task rows."""

    def start(self) -> None:
        if self.disable or self in _active_displays:
            return
        super().start()
        _active_displays.add(self)

    def stop(self) -> None:
        try:
            super().stop()
        finally:
            _active_displays.discard(self)

    def start_indeterminate_task(self, task_id: TaskID, *, description: str) -> None:
        """Reuse a row for work whose completion cannot yet be measured."""
        # Rich reset treats total=None as "keep the previous total".
        with self._lock:
            self._tasks[task_id].total = None
        # Reset releases its lock before refreshing; preserve that ordering.
        self.reset(task_id, description=description, completed=0)


class ProgressLogFilter(logging.Filter):
    """Keep routine console logs out of active progress displays."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.WARNING or not _active_displays


def create_progress(
    *, console: Console | None = None, disable: bool = False
) -> ProgressDisplay:
    """Create a compact progress display that preserves completion metrics."""
    return ProgressDisplay(
        TextColumn(
            "[progress.description]{task.description}",
            table_column=Column(ratio=2, overflow="ellipsis", no_wrap=True),
        ),
        BarColumn(bar_width=None, table_column=Column(ratio=1)),
        TaskProgressColumn(table_column=Column(no_wrap=True)),
        MofNCompleteColumn(table_column=Column(no_wrap=True)),
        console=console or progress_console,
        disable=disable,
        auto_refresh=not disable,
        refresh_per_second=10,
        expand=True,
    )

"""Extract safe, measured activity from Git's stderr progress records."""

import re
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class GitProgress:
    """A Git operation stage and its measured percentage, when available."""

    stage: str
    percentage: int | None = None


ProgressCallback = Callable[[GitProgress], None]

_PROGRESS_RE = re.compile(
    rb"^\s*(?:remote:\s*)?"
    rb"(Enumerating objects|Counting objects|Compressing objects|Receiving objects|"
    rb"Writing objects|Resolving deltas|Updating files|Checking out files):"
    rb"\s*(?:(\d{1,3})%)?"
)


class GitProgressParser:
    """Parse carriage-return or newline records without exposing raw Git output."""

    def __init__(self) -> None:
        self._pending = b""

    def feed(self, chunk: bytes) -> list[GitProgress]:
        """Return recognized progress records completed by this byte chunk."""
        records = re.split(rb"[\r\n]", self._pending + chunk)
        # Only the leading label and percentage are relevant. Bounding the
        # unfinished record avoids retaining a second copy of arbitrary stderr.
        self._pending = records.pop()[:256]
        return self._parse_records(records)

    def finish(self) -> list[GitProgress]:
        """Parse a final record without a trailing newline at end of stream."""
        pending, self._pending = self._pending, b""
        return self._parse_records([pending])

    @staticmethod
    def _parse_records(records: list[bytes]) -> list[GitProgress]:
        events = []
        for record in records:
            match = _PROGRESS_RE.match(record)
            if match is None:
                continue
            percentage = int(match[2]) if match[2] is not None else None
            if percentage is not None and percentage > 100:
                continue
            # The stage comes only from the fixed allowlist, never arbitrary
            # remote output or URLs that might carry credentials.
            events.append(GitProgress(match[1].decode("ascii"), percentage))
        return events

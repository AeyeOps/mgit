"""Terminal capability detection for animation support."""

import os
import platform
import sys
from enum import Enum, auto

_IS_WINDOWS = platform.system() == "Windows"


class TerminalCaps(Enum):
    """Terminal capability levels."""

    PIPE = auto()  # Output is piped, no TTY
    DUMB = auto()  # Dumb terminal, no ANSI support
    BASIC = auto()  # Basic terminal, no ANSI colors
    ANSI = auto()  # Full ANSI support with cursor control


def get_terminal_capabilities() -> TerminalCaps:
    """
    Detect terminal capabilities for animation support.

    Returns appropriate capability level based on:
    - TTY detection (is stdout a terminal?)
    - TERM environment variable
    - CI/non-interactive environment detection
    """
    # Not a TTY = piped output, no animation
    if not sys.stdout.isatty():
        return TerminalCaps.PIPE

    # Check for CI environments
    ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "TRAVIS"]
    if any(os.environ.get(var) for var in ci_vars):
        return TerminalCaps.PIPE

    # Check TERM variable
    term = os.environ.get("TERM", "")
    if term in ("dumb", "emacs", "M-emacs") or (not term and not _IS_WINDOWS):
        return TerminalCaps.DUMB

    # Windows terminals often omit TERM but must still honor NO_COLOR.
    if os.environ.get("NO_COLOR"):
        return TerminalCaps.BASIC

    # Most modern terminals support ANSI
    return TerminalCaps.ANSI


def get_terminal_size() -> tuple[int, int]:
    """Get terminal dimensions (columns, rows)."""
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 80, 24  # Sensible defaults


def hide_cursor() -> None:
    """Hide the terminal cursor."""
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor() -> None:
    """Show the terminal cursor."""
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def move_cursor_up(lines: int) -> None:
    """Move cursor up by specified number of lines."""
    if lines > 0:
        sys.stdout.write(f"\033[{lines}A")
        sys.stdout.flush()


def move_cursor_to_column(col: int) -> None:
    """Move cursor to specified column."""
    sys.stdout.write(f"\033[{col}G")
    sys.stdout.flush()


def clear_line() -> None:
    """Clear the current line."""
    sys.stdout.write("\033[2K")
    sys.stdout.flush()


def move_to_start_of_frame(height: int) -> None:
    """Move cursor to start position for next frame overwrite."""
    # Move to beginning of line and up by frame height
    sys.stdout.write(f"\r\033[{height}A")
    sys.stdout.flush()

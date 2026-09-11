"""Help animation orchestration for mgit CLI."""

import contextlib
import platform
import signal
import sys
import time
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.text import Text

# Platform-specific imports for terminal handling
_IS_WINDOWS = platform.system() == "Windows"

if _IS_WINDOWS:
    try:
        import msvcrt
    except ImportError:
        msvcrt = None  # type: ignore
    termios = None  # type: ignore
    tty = None  # type: ignore
    select = None  # type: ignore
else:
    try:
        import select
        import termios
        import tty
    except ImportError:
        select = None  # type: ignore
        termios = None  # type: ignore
        tty = None  # type: ignore
    msvcrt = None  # type: ignore

from mgit.ui.ascii_tree import (  # noqa: E402
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    get_static_tree,
    render_tree_frame,
)
from mgit.ui.terminal import (  # noqa: E402
    TerminalCaps,
    get_terminal_capabilities,
)

# Animation settings
ANIMATION_DURATION = 7.0  # seconds
ANIMATION_FPS = 12  # frames per second
ROTATION_SPEED = 0.15  # radians per frame


class AnimationInterrupted(KeyboardInterrupt):
    """Raised when animation is interrupted by user."""


# Type alias for signal handler (signal module has complex types)
SignalHandler = Any


def _setup_signal_handler() -> SignalHandler:
    """Set up signal handler for clean Ctrl+C handling. Returns previous handler."""
    previous_handler: SignalHandler = None

    def handler(signum: int, frame: object) -> None:
        raise AnimationInterrupted()

    with contextlib.suppress(OSError, ValueError):
        previous_handler = signal.signal(signal.SIGINT, handler)

    return previous_handler


def _restore_signal_handler(previous: SignalHandler) -> None:
    """Restore previous signal handler."""
    if previous is not None:
        with contextlib.suppress(OSError, ValueError):
            signal.signal(signal.SIGINT, previous)


def _check_for_keypress() -> bool:
    """Check if any key has been pressed (non-blocking). Returns True if key pressed."""
    if _IS_WINDOWS:
        # Windows: use msvcrt for keyboard detection
        if msvcrt and msvcrt.kbhit():
            msvcrt.getch()  # Consume the character
            return True
        return False
    else:
        # Unix: use select on stdin
        try:
            if select and select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.read(1)  # Consume the character
                return True
        except Exception:
            pass
        return False


def _set_raw_mode() -> Any:
    """Set terminal to raw mode for keypress detection. Returns old settings."""
    if _IS_WINDOWS:
        # Windows doesn't need raw mode setup for msvcrt
        return None
    else:
        # Unix: use termios to set cbreak mode
        try:
            if termios and tty:
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                tty.setcbreak(fd)  # Use cbreak instead of raw - allows Ctrl+C
                return old_settings
        except Exception:
            pass
        return None


def _restore_terminal(old_settings: Any) -> None:
    """Restore terminal to previous settings."""
    if _IS_WINDOWS:
        # Windows doesn't need terminal restoration
        return
    if old_settings is not None:
        try:
            if termios:
                fd = sys.stdin.fileno()
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception:
            pass


def run_tree_animation(
    duration: float = ANIMATION_DURATION, fps: float = ANIMATION_FPS
) -> None:
    """
    Run the spinning tree animation.

    Displays an animated ASCII tree that rotates for the specified duration,
    then clears the animation area before returning. Press any key to skip.
    """
    frame_time = 1.0 / fps
    angle = 0.0  # Rotation around vertical axis

    console = Console(file=sys.stdout)
    start_time = time.monotonic()

    previous_handler = _setup_signal_handler()
    old_terminal_settings = None

    try:
        old_terminal_settings = _set_raw_mode()  # Enable keypress detection
        with contextlib.ExitStack() as stack:
            live: Live | None = None
            while time.monotonic() - start_time < duration:
                frame_start = time.monotonic()
                if _check_for_keypress():
                    break

                # Leave room for cursor cleanup and avoid wrapping the last column.
                # Read the dimensions each frame so terminal resizing takes effect.
                size = console.size
                frame = Text.from_ansi(
                    render_tree_frame(
                        angle,
                        use_color=not console.no_color,
                        width=max(1, min(SCREEN_WIDTH, size.width - 1)),
                        height=max(1, min(SCREEN_HEIGHT, size.height - 1)),
                    )
                )
                if live is None:
                    # Start only after the first key check: an immediate skip owns
                    # no terminal rows and must not erase previous command output.
                    live = Live(
                        frame,
                        console=console,
                        transient=True,
                        auto_refresh=False,
                        vertical_overflow="crop",
                        redirect_stdout=False,
                        redirect_stderr=False,
                    )
                    # Own cleanup before rendering: Ctrl+C can arrive during the
                    # first frame, before a Live context manager finishes entry.
                    stack.callback(live.stop)
                    live.start(refresh=True)
                else:
                    live.update(frame, refresh=True)

                angle += ROTATION_SPEED
                elapsed = time.monotonic() - frame_start
                sleep_time = frame_time - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

    except AnimationInterrupted:
        # Live clears its own frame before terminal settings are restored below.
        raise KeyboardInterrupt from None

    finally:
        _restore_terminal(old_terminal_settings)
        _restore_signal_handler(previous_handler)


def print_static_tree(use_color: bool = True) -> None:
    """Print the static ASCII tree (for non-animated contexts)."""
    # Use sys.stdout.write with explicit flush for guaranteed ordering
    sys.stdout.write(get_static_tree(use_color=use_color))
    sys.stdout.write("\n")
    sys.stdout.flush()


def _is_animation_enabled() -> bool:
    """Check whether the user explicitly enabled help animation."""
    from mgit.config.yaml_manager import get_global_setting

    return get_global_setting("help_animation", False)


def show_animated_help(help_text: str) -> None:
    """
    Show help with optional animation based on terminal capabilities.

    In capable terminals with animation enabled: shows spinning tree animation,
    then static tree on top of help text.
    In limited terminals: shows static tree on top of help text.
    In pipes: shows static tree on top of help text (no color).

    Animation is opt-in via config: global.help_animation = true
    """
    caps = get_terminal_capabilities()
    use_color = caps == TerminalCaps.ANSI

    try:
        if caps == TerminalCaps.ANSI and _is_animation_enabled():
            run_tree_animation()
        # Tree always appears on top, then help text below
        print_static_tree(use_color=use_color)
        sys.stdout.write(help_text)
        sys.stdout.flush()

    except KeyboardInterrupt:
        # User interrupted - just show help without tree
        sys.stdout.write("\n")
        sys.stdout.write(help_text)
        sys.stdout.write("\n")
        sys.stdout.flush()
        raise

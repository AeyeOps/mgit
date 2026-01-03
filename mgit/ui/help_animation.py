"""Help animation orchestration for mgit CLI."""

import contextlib
import select
import signal
import sys
import termios
import time
import tty
from typing import Any

from mgit.ui.ascii_tree import get_static_tree, get_tree_height, render_tree_frame
from mgit.ui.terminal import (
    TerminalCaps,
    get_terminal_capabilities,
    hide_cursor,
    move_to_start_of_frame,
    show_cursor,
)

# Animation settings
ANIMATION_DURATION = 7.0  # seconds
ANIMATION_FPS = 12  # frames per second
ROTATION_SPEED = 0.15  # radians per frame


class AnimationInterrupted(Exception):
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
    try:
        # Check if stdin has data available (non-blocking)
        if select.select([sys.stdin], [], [], 0)[0]:
            sys.stdin.read(1)  # Consume the character
            return True
    except Exception:
        pass
    return False


def _set_raw_mode() -> Any:
    """Set terminal to raw mode for keypress detection. Returns old settings."""
    try:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)  # Use cbreak instead of raw - allows Ctrl+C
        return old_settings
    except Exception:
        return None


def _restore_terminal(old_settings: Any) -> None:
    """Restore terminal to previous settings."""
    if old_settings is not None:
        try:
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

    tree_height = get_tree_height()
    start_time = time.monotonic()
    first_frame = True

    previous_handler = _setup_signal_handler()
    old_terminal_settings = _set_raw_mode()  # Enable keypress detection

    try:
        hide_cursor()

        while time.monotonic() - start_time < duration:
            frame_start = time.monotonic()

            # Check for keypress to skip animation
            if _check_for_keypress():
                break

            # Render frame with current rotation angle
            frame = render_tree_frame(angle)

            # Move cursor back to start for overwrite (except first frame)
            if not first_frame:
                move_to_start_of_frame(tree_height)
            first_frame = False

            # Output frame
            sys.stdout.write(frame)
            sys.stdout.write("\n")
            sys.stdout.flush()

            # Advance rotation
            angle += ROTATION_SPEED

            # Maintain frame rate
            elapsed = time.monotonic() - frame_start
            sleep_time = frame_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        # Clear animation area after completion
        move_to_start_of_frame(tree_height)
        for _ in range(tree_height):
            sys.stdout.write(" " * 65 + "\n")
        move_to_start_of_frame(tree_height)
        sys.stdout.flush()

    except AnimationInterrupted:
        # Clean exit on Ctrl+C - clear animation and re-raise as KeyboardInterrupt
        move_to_start_of_frame(tree_height)
        for _ in range(tree_height):
            sys.stdout.write(" " * 65 + "\n")
        move_to_start_of_frame(tree_height)
        sys.stdout.flush()
        show_cursor()
        _restore_terminal(old_terminal_settings)
        _restore_signal_handler(previous_handler)
        raise KeyboardInterrupt from None

    finally:
        show_cursor()
        _restore_terminal(old_terminal_settings)
        _restore_signal_handler(previous_handler)


def print_static_tree(use_color: bool = True) -> None:
    """Print the static ASCII tree (for non-animated contexts)."""
    # Use sys.stdout.write with explicit flush for guaranteed ordering
    sys.stdout.write(get_static_tree(use_color=use_color))
    sys.stdout.write("\n")
    sys.stdout.flush()


def _is_animation_enabled() -> bool:
    """Check if help animation is enabled in config."""
    try:
        from mgit.config.yaml_manager import get_global_setting

        return get_global_setting("help_animation", True)
    except Exception:
        return True  # Default to enabled if config unavailable


def show_animated_help(help_text: str) -> None:
    """
    Show help with optional animation based on terminal capabilities.

    In capable terminals: shows spinning tree animation, then static tree on top of help text.
    In limited terminals: shows static tree on top of help text.
    In pipes: shows static tree on top of help text (no color).

    Animation can be disabled via config: global.help_animation = false
    """
    caps = get_terminal_capabilities()
    use_color = caps in (TerminalCaps.ANSI, TerminalCaps.BASIC)

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

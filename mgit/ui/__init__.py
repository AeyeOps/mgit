"""UI module for mgit - ASCII art animation and terminal utilities."""

from mgit.ui.ascii_tree import get_static_tree, render_tree_frame
from mgit.ui.help_animation import show_animated_help
from mgit.ui.terminal import TerminalCaps, get_terminal_capabilities

__all__ = [
    "render_tree_frame",
    "get_static_tree",
    "TerminalCaps",
    "get_terminal_capabilities",
    "show_animated_help",
]

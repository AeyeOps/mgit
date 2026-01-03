"""Unit tests for terminal capability detection."""

import os
import sys
from unittest.mock import MagicMock

from mgit.ui.terminal import (
    TerminalCaps,
    get_terminal_capabilities,
    get_terminal_size,
    hide_cursor,
    move_cursor_up,
    move_to_start_of_frame,
    show_cursor,
)


class TestTerminalCapabilities:
    """Tests for terminal capability detection."""

    def test_pipe_detection(self, monkeypatch):
        """Non-TTY stdout should be detected as pipe."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False
        monkeypatch.setattr(sys, "stdout", mock_stdout)

        caps = get_terminal_capabilities()
        assert caps == TerminalCaps.PIPE

    def test_dumb_terminal(self, monkeypatch):
        """TERM=dumb should trigger DUMB capability."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        monkeypatch.setattr(sys, "stdout", mock_stdout)
        monkeypatch.setenv("TERM", "dumb")
        # Clear CI variables
        for var in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "TRAVIS"]:
            monkeypatch.delenv(var, raising=False)

        caps = get_terminal_capabilities()
        assert caps == TerminalCaps.DUMB

    def test_empty_term(self, monkeypatch):
        """Empty TERM should trigger DUMB capability."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        monkeypatch.setattr(sys, "stdout", mock_stdout)
        monkeypatch.setenv("TERM", "")
        for var in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "TRAVIS"]:
            monkeypatch.delenv(var, raising=False)

        caps = get_terminal_capabilities()
        assert caps == TerminalCaps.DUMB

    def test_ci_environment_detection(self, monkeypatch):
        """CI environment should be detected as PIPE."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        monkeypatch.setattr(sys, "stdout", mock_stdout)
        monkeypatch.setenv("TERM", "xterm-256color")
        monkeypatch.setenv("CI", "true")

        caps = get_terminal_capabilities()
        assert caps == TerminalCaps.PIPE

    def test_github_actions_detection(self, monkeypatch):
        """GitHub Actions should be detected as PIPE."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        monkeypatch.setattr(sys, "stdout", mock_stdout)
        monkeypatch.setenv("TERM", "xterm-256color")
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setenv("GITHUB_ACTIONS", "true")

        caps = get_terminal_capabilities()
        assert caps == TerminalCaps.PIPE

    def test_ansi_terminal(self, monkeypatch):
        """Normal terminal should be detected as ANSI."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        monkeypatch.setattr(sys, "stdout", mock_stdout)
        monkeypatch.setenv("TERM", "xterm-256color")
        # Clear all CI/NO_COLOR vars
        for var in [
            "CI",
            "GITHUB_ACTIONS",
            "GITLAB_CI",
            "JENKINS_URL",
            "TRAVIS",
            "NO_COLOR",
        ]:
            monkeypatch.delenv(var, raising=False)

        caps = get_terminal_capabilities()
        assert caps == TerminalCaps.ANSI

    def test_no_color_environment(self, monkeypatch):
        """NO_COLOR environment variable should trigger BASIC."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        monkeypatch.setattr(sys, "stdout", mock_stdout)
        monkeypatch.setenv("TERM", "xterm-256color")
        monkeypatch.setenv("NO_COLOR", "1")
        for var in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "TRAVIS"]:
            monkeypatch.delenv(var, raising=False)

        caps = get_terminal_capabilities()
        assert caps == TerminalCaps.BASIC


class TestTerminalSize:
    """Tests for terminal size detection."""

    def test_terminal_size_returns_tuple(self):
        """get_terminal_size should return tuple of two ints."""
        cols, rows = get_terminal_size()
        assert isinstance(cols, int)
        assert isinstance(rows, int)

    def test_terminal_size_positive(self):
        """Terminal size should be positive."""
        cols, rows = get_terminal_size()
        assert cols > 0
        assert rows > 0

    def test_terminal_size_fallback(self, monkeypatch):
        """Should return sensible defaults if size detection fails."""

        def raise_oserror(*args, **kwargs):
            raise OSError("No terminal")

        monkeypatch.setattr(os, "get_terminal_size", raise_oserror)

        cols, rows = get_terminal_size()
        assert cols == 80
        assert rows == 24


class TestCursorControl:
    """Tests for ANSI cursor control functions."""

    def test_hide_cursor_writes_escape(self, monkeypatch):
        """hide_cursor should write ANSI escape sequence."""
        output = []
        mock_stdout = MagicMock()
        mock_stdout.write = lambda s: output.append(s)
        mock_stdout.flush = lambda: None
        monkeypatch.setattr(sys, "stdout", mock_stdout)

        hide_cursor()

        assert "\033[?25l" in "".join(output)

    def test_show_cursor_writes_escape(self, monkeypatch):
        """show_cursor should write ANSI escape sequence."""
        output = []
        mock_stdout = MagicMock()
        mock_stdout.write = lambda s: output.append(s)
        mock_stdout.flush = lambda: None
        monkeypatch.setattr(sys, "stdout", mock_stdout)

        show_cursor()

        assert "\033[?25h" in "".join(output)

    def test_move_cursor_up_writes_escape(self, monkeypatch):
        """move_cursor_up should write correct escape sequence."""
        output = []
        mock_stdout = MagicMock()
        mock_stdout.write = lambda s: output.append(s)
        mock_stdout.flush = lambda: None
        monkeypatch.setattr(sys, "stdout", mock_stdout)

        move_cursor_up(5)

        assert "\033[5A" in "".join(output)

    def test_move_cursor_up_zero_no_output(self, monkeypatch):
        """move_cursor_up with 0 should not write."""
        output = []
        mock_stdout = MagicMock()
        mock_stdout.write = lambda s: output.append(s)
        mock_stdout.flush = lambda: None
        monkeypatch.setattr(sys, "stdout", mock_stdout)

        move_cursor_up(0)

        assert len(output) == 0

    def test_move_to_start_of_frame(self, monkeypatch):
        """move_to_start_of_frame should move cursor appropriately."""
        output = []
        mock_stdout = MagicMock()
        mock_stdout.write = lambda s: output.append(s)
        mock_stdout.flush = lambda: None
        monkeypatch.setattr(sys, "stdout", mock_stdout)

        move_to_start_of_frame(10)

        combined = "".join(output)
        assert "\r" in combined  # Carriage return
        assert "10A" in combined  # Move up 10 lines

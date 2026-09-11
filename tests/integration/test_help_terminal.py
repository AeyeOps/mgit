"""Real terminal coverage for default help and opt-in animation lifecycle."""

import os
import re
import selectors
import signal
import struct
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
from rich.cells import get_character_cell_size

if os.name == "posix":
    import fcntl
    import pty
    import termios

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.name != "posix", reason="Requires a POSIX terminal"),
]

_CURSOR_HIDE = b"\x1b[?25l"
_CURSOR_SHOW = b"\x1b[?25h"
_CSI = re.compile(r"\x1b\[([0-?]*)([ -/]*)([@-~])")
_ATTACH_TERMINAL = """
import fcntl
import os
import sys
import termios

fcntl.ioctl(0, termios.TIOCSCTTY, 0)
print("PRIOR", flush=True)
os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
"""


class _Screen:
    """Interpret the cursor, erase, color and text operations emitted by Live."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.rows = [[" "] * width for _ in range(height)]
        self.history = []
        self.x = self.y = 0
        self.visible = True
        self.wraps = 0

    def resize(self, width, height):
        if height < self.height:
            removed = self.height - height
            self.history.extend("".join(row) for row in self.rows[:removed])
            self.rows = self.rows[removed:]
            self.y = max(0, self.y - removed)
        else:
            self.rows.extend([[" "] * self.width for _ in range(height - self.height)])
        self.rows = [(row + [" "] * width)[:width] for row in self.rows]
        self.width, self.height = width, height
        self.x = min(self.x, width - 1)

    def _linefeed(self):
        self.y += 1
        if self.y == self.height:
            self.history.append("".join(self.rows.pop(0)))
            self.rows.append([" "] * self.width)
            self.y -= 1

    def feed(self, output):
        text = output.decode("utf-8")
        index = 0
        while index < len(text):
            char = text[index]
            if char == "\x1b":
                match = _CSI.match(text, index)
                assert match is not None, repr(text[index : index + 20])
                params, _, operation = match.groups()
                if operation == "A":
                    self.y = max(0, self.y - int(params or "1"))
                elif operation == "K":
                    assert params == "2", match.group()
                    assert "PRIOR" not in "".join(self.rows[self.y])
                    self.rows[self.y] = [" "] * self.width
                elif params == "?25" and operation in "hl":
                    self.visible = operation == "h"
                else:
                    assert operation == "m", match.group()
                index = match.end()
                continue
            if char == "\r":
                self.x = 0
            elif char == "\n":
                self._linefeed()
            else:
                cells = get_character_cell_size(char)
                if cells == 0:
                    if self.x:
                        self.rows[self.y][self.x - 1] += char
                    index += 1
                    continue
                if self.x + cells > self.width:
                    self.wraps += 1
                    self.x = 0
                    self._linefeed()
                self.rows[self.y][self.x] = char
                if cells == 2:
                    self.rows[self.y][self.x + 1] = ""
                self.x += cells
            index += 1

    def assert_restored(self):
        assert self.visible
        lines = self.history + ["".join(row) for row in self.rows]
        assert "PRIOR" in [line.rstrip() for line in lines]


class _TerminalProcess:
    def __init__(self, process, master, slave, original_settings):
        self.process = process
        self.master, self.slave = master, slave
        self.original_settings = original_settings
        self.output = bytearray()
        self.started = time.monotonic()

    def resize(self, width, height):
        fcntl.ioctl(
            self.slave,
            termios.TIOCSWINSZ,
            struct.pack("HHHH", height, width, 0, 0),
        )

    def send(self, data):
        os.write(self.master, data)

    def read_until(self, marker, *, offset=0, timeout=10):
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(self.master, selectors.EVENT_READ)
            while marker not in self.output[offset:]:
                remaining = deadline - time.monotonic()
                assert remaining > 0, f"Terminal did not emit {marker!r}"
                for _, _ in selector.select(min(remaining, 0.1)):
                    self.output.extend(os.read(self.master, 65536))
                assert self.process.poll() is None or marker in self.output[offset:], (
                    self.output.decode("utf-8", errors="replace")
                )

    def finish(self, timeout=10):
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(self.master, selectors.EVENT_READ)
            while self.process.poll() is None:
                remaining = deadline - time.monotonic()
                assert remaining > 0, "Terminal command did not finish"
                for _, _ in selector.select(min(remaining, 0.1)):
                    self.output.extend(os.read(self.master, 65536))
            while selector.select(0):
                self.output.extend(os.read(self.master, 65536))
        assert termios.tcgetattr(self.slave) == self.original_settings
        return bytes(self.output)


@pytest.fixture
def terminal_env(tmp_path):
    """Keep subprocesses away from the operator's config and Git settings."""
    home = tmp_path / "home"
    home.mkdir()
    config_dir = home / ".config" / "mgit"
    config_dir.mkdir(parents=True)
    return {
        "HOME": str(home),
        "USERPROFILE": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "PATH": os.environ["PATH"],
        "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "TERM": "xterm-256color",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }


@contextmanager
def _command_in_terminal(env, args, width=30, height=10):
    master, slave = pty.openpty()
    original_settings = termios.tcgetattr(slave)
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))
    process = subprocess.Popen(
        [sys.executable, "-c", _ATTACH_TERMINAL, "-m", "mgit", *args],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=env["HOME"],
        env=env,
        start_new_session=True,
    )
    try:
        yield _TerminalProcess(process, master, slave, original_settings)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        os.close(master)
        os.close(slave)


def _help_in_terminal(env, width=30, height=10):
    return _command_in_terminal(env, ["--help"], width=width, height=height)


def _enable_animation(env):
    config = Path(env["HOME"]) / ".config" / "mgit" / "config.yaml"
    config.write_text("global:\n  help_animation: true\n", encoding="utf-8")


def _animation_end(output):
    """Include transient cleanup after cursor restoration, before static help."""
    shown = output.index(_CURSOR_SHOW) + len(_CURSOR_SHOW)
    cleanup = re.match(rb"(?:\r|\x1b\[[0-9;]*[AK])*", output[shown:])
    assert cleanup is not None
    return shown + cleanup.end()


def test_default_help_is_immediate_and_static_in_a_terminal(terminal_env):
    """The real help command must not opt fresh users into a seven-second wait."""
    with _help_in_terminal(terminal_env, width=80, height=30) as terminal:
        output = terminal.finish()
        elapsed = time.monotonic() - terminal.started
        assert terminal.process.returncode == 0
        assert elapsed < 6, f"Default help took {elapsed:.2f}s"
        assert _CURSOR_HIDE not in output
        assert b"\x1b[2K" not in output
        plain = _CSI.sub("", output.decode("utf-8"))
        assert "M   G   I   T" in plain
        assert "Usage:" in plain


@pytest.mark.parametrize("key,exit_code", [(b"x", 0), (b"\x03", 130)])
def test_opt_in_help_restores_narrow_terminal(terminal_env, key, exit_code):
    """Real keypress and Ctrl+C restore terminal mode, cursor and prior output."""
    _enable_animation(terminal_env)
    with _help_in_terminal(terminal_env) as terminal:
        terminal.read_until(b"\x1b[2K")  # At least one complete frame was rendered.
        terminal.send(key)
        output = terminal.finish()
        assert terminal.process.returncode == exit_code
        assert output.count(_CURSOR_HIDE) == 1
        assert output.count(_CURSOR_SHOW) == 1
        screen = _Screen(30, 10)
        screen.feed(output[: _animation_end(output)])
        assert screen.wraps == 0
        screen.assert_restored()


def test_opt_in_help_adapts_to_terminal_resize(terminal_env):
    """A smaller real PTY produces smaller frames and still cleans up safely."""
    _enable_animation(terminal_env)
    with _help_in_terminal(terminal_env) as terminal:
        terminal.read_until(b"\x1b[2K")
        before_resize = bytes(terminal.output)
        screen = _Screen(30, 10)
        screen.feed(before_resize)
        terminal.resize(20, 6)
        screen.resize(20, 6)
        # Rich's next frame starts with a blank row at the new 19-cell width.
        terminal.read_until(b"\x1b[2K" + b" " * 19 + b"\r\n", offset=len(before_resize))
        terminal.send(b"x")
        output = terminal.finish()
        assert terminal.process.returncode == 0
        assert output.count(_CURSOR_SHOW) == 1
        screen.feed(output[len(before_resize) : _animation_end(output)])
        assert screen.wraps == 0
        screen.assert_restored()

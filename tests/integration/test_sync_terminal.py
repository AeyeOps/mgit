"""Real Git transfers through the CLI's stationary sync terminal panel."""

import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from rich.text import Text

from tests.integration.test_help_terminal import (
    _CSI,
    _CURSOR_HIDE,
    _CURSOR_SHOW,
    _command_in_terminal,
    _Screen,
)
from tests.integration.test_help_terminal import terminal_env as terminal_env

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.name != "posix", reason="Requires a POSIX terminal"),
]

_THROTTLED_UPLOAD = """
import os
import subprocess
import sys
import time

with subprocess.Popen(["git-upload-pack", *sys.argv[1:]], stdout=subprocess.PIPE) as git:
    while chunk := os.read(git.stdout.fileno(), 16384):
        os.write(sys.stdout.fileno(), chunk)
        time.sleep(0.025)
    sys.exit(git.wait())
"""
_SLEEPING_UPLOAD = """
import os
import time
from pathlib import Path

Path(os.environ["SYNC_HELPER_PID"]).write_text(str(os.getpid()))
time.sleep(30)
"""


def _git(env, cwd, *args):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()


def _write_helper(path, code):
    path.write_text(f"#!{sys.executable}\n{code}", encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture
def sync_workspace(tmp_path, terminal_env):
    """Two real clones receive one MiB of new, incompressible upstream objects."""
    env = {
        **terminal_env,
        "GIT_AUTHOR_NAME": "Terminal Test",
        "GIT_AUTHOR_EMAIL": "terminal@mgit.test",
        "GIT_COMMITTER_NAME": "Terminal Test",
        "GIT_COMMITTER_EMAIL": "terminal@mgit.test",
    }
    seed, remote, workspace = (
        tmp_path / "seed",
        tmp_path / "remote.git",
        tmp_path / "workspace",
    )
    seed.mkdir()
    workspace.mkdir()
    _git(env, seed, "init", "--initial-branch=main")
    (seed / "README.md").write_text("Initial revision\n", encoding="utf-8")
    _git(env, seed, "add", ".")
    _git(env, seed, "commit", "-m", "Initial revision")
    _git(env, tmp_path, "clone", "--bare", str(seed), str(remote))
    repositories = [
        workspace / "[red]文件 long repository A",
        workspace / "ñ [link] repository B with a long name",
    ]
    for repository in repositories:
        _git(env, tmp_path, "clone", remote.as_uri(), str(repository))
        _git(env, repository, "config", "fetch.unpackLimit", "1")
    payloads = {}
    for index in range(16):
        name = f"payload_{index:02d}.bin"
        payloads[name] = os.urandom(65536)
        (seed / name).write_bytes(payloads[name])
    _git(env, seed, "add", ".")
    _git(env, seed, "commit", "-m", "Add transfer payload")
    _git(env, seed, "push", str(remote), "main")
    return env, workspace, repositories, payloads


def _frames(output):
    """Split Rich refreshes into their visible, cell-countable rows."""
    output = output.replace(_CURSOR_HIDE, b"").replace(_CURSOR_SHOW, b"")
    chunks = re.split(rb"\r(?:\x1b\[[0-9]*[AK])+", output)
    frames = [
        Text.from_ansi(chunk.decode("utf-8").replace("\r\n", "\n")).split("\n")
        for chunk in chunks
    ]
    return [frame for frame in frames if any(line.plain.strip() for line in frame)]


def _assert_panel_bounds(output, width):
    for frame in _frames(output):
        assert len(frame) <= 3, [line.plain for line in frame]
        assert all(line.cell_len <= width for line in frame)


def _sync_args(workspace):
    return ["sync", str(workspace), "--concurrency", "2", "--no-summary"]


def test_sync_streams_real_git_progress_and_resizes(sync_workspace, tmp_path):
    """A real transfer updates before exit, stays in three rows and reaches 100%."""
    env, workspace, repositories, payloads = sync_workspace
    helper = _write_helper(tmp_path / "throttled-upload-pack", _THROTTLED_UPLOAD)
    for repository in repositories:
        _git(env, repository, "config", "remote.origin.uploadpack", str(helper))

    with _command_in_terminal(
        env, _sync_args(workspace), width=40, height=10
    ) as terminal:
        terminal.read_until(b"Receiving")
        assert terminal.process.poll() is None
        before_resize = bytes(terminal.output)
        live_start = before_resize.index(_CURSOR_HIDE)
        plain = _CSI.sub("", before_resize.decode("utf-8"))
        percentages = re.findall(r"Receiving[^\r\n]*?\b(\d+)%", plain)
        assert any(0 < int(percentage) < 100 for percentage in percentages), plain
        _assert_panel_bounds(before_resize[live_start:], 40)
        # Begin at the panel so naturally wrapped, static path output is excluded.
        screen = _Screen(40, 10)
        screen.feed(b"PRIOR\r\n" + before_resize[live_start:])
        terminal.resize(20, 6)
        screen.resize(20, 6)
        output = terminal.finish()
        assert terminal.process.returncode == 0, output.decode("utf-8")
        assert output.count(_CURSOR_HIDE) == output.count(_CURSOR_SHOW) == 1
        live_end = output.index(_CURSOR_SHOW) + len(_CURSOR_SHOW)
        after_resize = output[len(before_resize) : live_end]
        _assert_panel_bounds(after_resize, 20)
        screen.feed(after_resize)
        assert screen.wraps == 0
        screen.assert_restored()
        final_frame = _frames(output[live_start:live_end])[-1]
        assert re.search(r"100%\s+2/2", final_frame[0].plain)

    for repository in repositories:
        for name, contents in payloads.items():
            assert (repository / name).read_bytes() == contents


def _helper_running(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    status = Path(f"/proc/{pid}/stat")
    if status.exists():
        return status.read_text().split(")", 1)[1].split()[0] != "Z"
    return True


def test_sync_ctrl_c_cleans_up_sleeping_git_helper(sync_workspace, tmp_path):
    """Actual terminal Ctrl+C cancels a blocked transport and restores the cursor."""
    env, workspace, repositories, _ = sync_workspace
    # One transport is enough to prove descendant cleanup; leave the other clone clean.
    _git(env, repositories[1], "pull", "--ff-only")
    pid_file = tmp_path / "helper.pid"
    env["SYNC_HELPER_PID"] = str(pid_file)
    helper = _write_helper(tmp_path / "sleeping-upload-pack", _SLEEPING_UPLOAD)
    _git(env, repositories[0], "config", "remote.origin.uploadpack", str(helper))

    pid = None
    try:
        with _command_in_terminal(
            env, _sync_args(workspace), width=40, height=10
        ) as terminal:
            terminal.read_until(b"Pulling")
            deadline = time.monotonic() + 5
            while not pid_file.exists() or pid_file.stat().st_size == 0:
                assert time.monotonic() < deadline, "Git transport did not start"
                time.sleep(0.02)
            pid = int(pid_file.read_text())
            interrupted_at = time.monotonic()
            terminal.send(b"\x03")
            output = terminal.finish(timeout=5)
            assert time.monotonic() - interrupted_at < 4
            assert terminal.process.returncode == 130, output.decode("utf-8")
            assert output.count(_CURSOR_HIDE) == output.count(_CURSOR_SHOW) == 1
            assert not _helper_running(pid)
    finally:
        if pid is not None and _helper_running(pid):
            os.kill(pid, signal.SIGKILL)


def test_redirected_sync_without_progress_has_no_live_output(sync_workspace):
    """The real quiet progress path leaves redirected streams free of frames."""
    env, workspace, repositories, payloads = sync_workspace
    result = subprocess.run(
        [sys.executable, "-m", "mgit", *_sync_args(workspace), "--no-progress"],
        cwd=env["HOME"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    output = result.stdout + result.stderr
    assert "\x1b[" not in output
    assert "Receiving objects" not in output
    assert "Active:" not in output
    for repository in repositories:
        assert (repository / "payload_00.bin").read_bytes() == payloads[
            "payload_00.bin"
        ]

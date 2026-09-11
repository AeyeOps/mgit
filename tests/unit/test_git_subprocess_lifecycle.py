"""Exercise timeout cleanup with real processes and inherited output pipes."""

import asyncio
import contextlib
import logging
import os
import shlex
import signal
import subprocess
import sys
import time

import pytest

from mgit.git.manager import GitManager

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
def spawned_processes(monkeypatch):
    processes = []
    create = asyncio.create_subprocess_exec

    async def record_process(*args, **kwargs):
        process = await create(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", record_process)
    return processes


def _is_running(pid):
    result = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True
    )
    return bool(result.stdout.strip()) and not result.stdout.lstrip().startswith("Z")


async def _cleanup(processes, pid_file):
    # Also clean up when exercising the broken implementation, where helpers
    # survive the parent or cancellation does not terminate either process.
    if pid_file.exists():
        with contextlib.suppress(ProcessLookupError):
            os.kill(int(pid_file.read_text()), signal.SIGKILL)
    for process in processes:
        if process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                process.kill()
        await asyncio.wait_for(process.communicate(), timeout=3)


@pytest.mark.skipif(os.name != "posix", reason="POSIX process group lifecycle")
@pytest.mark.parametrize("parent_exits", [False, True])
@pytest.mark.parametrize("streaming", [False, True])
async def test_timeout_kills_helpers_holding_output_pipes(
    tmp_path, spawned_processes, parent_exits, streaming
):
    pid_file = tmp_path / "helper.pid"
    script = (
        "import subprocess, sys, time; from pathlib import Path; "
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(2)']); "
        f"Path({str(pid_file)!r}).write_text(str(child.pid)); "
        + ("sys.exit(0)" if parent_exits else "time.sleep(2)")
    )
    start = time.monotonic()
    try:
        with pytest.raises(subprocess.CalledProcessError) as error:
            await GitManager()._run_subprocess(
                [sys.executable, "-c", script],
                tmp_path,
                timeout=0.3,
                max_retries=0,
                on_progress=(lambda event: None) if streaming else None,
            )
        elapsed = time.monotonic() - start
        assert error.value.returncode == 124
        assert elapsed < 1.5, f"Timeout cleanup took {elapsed:.2f}s"
        assert pid_file.exists(), "Helper must start before the timeout"
        assert not _is_running(int(pid_file.read_text()))
    finally:
        await _cleanup(spawned_processes, pid_file)


@pytest.mark.skipif(os.name != "posix", reason="POSIX process group lifecycle")
async def test_cancellation_terminates_git_and_helpers(tmp_path, spawned_processes):
    pid_file = tmp_path / "helper.pid"
    script = (
        "import subprocess, sys, time; from pathlib import Path; "
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)']); "
        f"Path({str(pid_file)!r}).write_text(str(child.pid)); time.sleep(10)"
    )
    task = asyncio.create_task(
        GitManager()._run_subprocess(
            [sys.executable, "-c", script], tmp_path, timeout=5, max_retries=0
        )
    )
    try:

        async def helper_started():
            while not pid_file.exists():
                await asyncio.sleep(0.01)

        await asyncio.wait_for(helper_started(), timeout=3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert spawned_processes[0].returncode is not None
        assert not _is_running(int(pid_file.read_text()))
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await _cleanup(spawned_processes, pid_file)


@pytest.mark.skipif(os.name != "posix", reason="POSIX process group lifecycle")
@pytest.mark.parametrize("streaming", [False, True])
async def test_cleanup_is_bounded_when_helper_leaves_process_group(
    tmp_path, spawned_processes, caplog, monkeypatch, streaming
):
    # CLI imports disable mgit propagation; let pytest capture the warning even
    # when this test runs after CLI tests in the full suite.
    monkeypatch.setattr(logging.getLogger("mgit"), "propagate", True)
    caplog.set_level(logging.DEBUG, logger="mgit.git.manager")
    pid_file = tmp_path / "helper.pid"
    script = (
        "import subprocess, sys, time; from pathlib import Path; "
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3)'], "
        "start_new_session=True); "
        f"Path({str(pid_file)!r}).write_text(str(child.pid)); time.sleep(3)"
    )
    start = time.monotonic()
    try:
        with pytest.raises(subprocess.CalledProcessError) as error:
            await GitManager()._run_subprocess(
                [sys.executable, "-c", script],
                tmp_path,
                timeout=0.3,
                max_retries=0,
                on_progress=(lambda event: None) if streaming else None,
            )
        elapsed = time.monotonic() - start
        assert error.value.returncode == 124
        assert elapsed < 2, f"Cleanup exceeded its bound: {elapsed:.2f}s"
        assert "cleanup" in caplog.text.lower()
    finally:
        await _cleanup(spawned_processes, pid_file)


@pytest.mark.skipif(os.name != "posix", reason="POSIX SSH command and process checks")
async def test_git_clone_timeout_terminates_ssh_helper(
    tmp_path, monkeypatch, spawned_processes
):
    pid_file = tmp_path / "ssh.pid"
    helper = tmp_path / "ssh_helper.py"
    helper.write_text(
        "import os, time\nfrom pathlib import Path\n"
        f"Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
        "time.sleep(10)\n"
    )
    monkeypatch.setenv("GIT_SSH_COMMAND", shlex.join([sys.executable, str(helper)]))
    monkeypatch.setenv("GIT_SSH_VARIANT", "ssh")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    start = time.monotonic()
    try:
        with pytest.raises(subprocess.CalledProcessError) as error:
            await GitManager()._run_subprocess(
                ["git", "clone", "ssh://mgit.invalid/repo.git", "clone"],
                tmp_path,
                timeout=0.3,
                max_retries=0,
            )
        assert error.value.returncode == 124
        assert time.monotonic() - start < 1.5
        assert pid_file.exists(), "Git must invoke the local SSH helper"
        assert not _is_running(int(pid_file.read_text()))
    finally:
        await _cleanup(spawned_processes, pid_file)

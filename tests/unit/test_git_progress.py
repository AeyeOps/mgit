"""Check measured Git progress against real pipes and local repositories."""

import asyncio
import contextlib
import logging
import os
import signal
import subprocess
import sys
import time
from unittest.mock import AsyncMock

import pytest

from mgit.git.manager import GitManager, _sanitize_cmd_for_log
from mgit.git.progress import GitProgress, GitProgressParser

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "stage",
    [
        "Enumerating objects",
        "Counting objects",
        "Compressing objects",
        "Receiving objects",
        "Writing objects",
        "Resolving deltas",
        "Updating files",
        "Checking out files",
    ],
)
def test_parser_recognizes_fragmented_local_and_remote_stages(stage):
    parser = GitProgressParser()
    payload = f"remote: {stage}: 43% (3/7)\r{stage}: 100% (7/7), done.\n"
    events = []
    for value in payload.encode():
        events.extend(parser.feed(bytes([value])))
    assert events == [GitProgress(stage, 43), GitProgress(stage, 100)]
    assert parser.finish() == []


def test_parser_exposes_only_fixed_stage_labels_and_valid_percentages():
    parser = GitProgressParser()
    events = parser.feed(
        b"fatal: https://user:token@example.invalid/repo\r"
        b"remote: Authorization: Bearer SECRET\n"
        b"remote: Enumerating objects: 7, done.\r\n"
        b"Receiving objects: 999% token\r"
        b"Receiving objects: 50% (1/2) https://user:token@host\n"
        b"Checking out files: 100% (2/2), done."
    )
    events.extend(parser.finish())
    assert events == [
        GitProgress("Enumerating objects"),
        GitProgress("Receiving objects", 50),
        GitProgress("Checking out files", 100),
    ]


@pytest.mark.asyncio
async def test_progress_arrives_before_exit_and_preserves_both_streams(tmp_path):
    released = tmp_path / "released"
    finished = tmp_path / "finished"
    stderr_chunks = [
        b"remote: Enumerating objects: 7, done.\r\nReceiv",
        b"ing objects: 4",
        b"3% (3/7)\r",
        b"Receiving objects: 100% (7/7), done.\n",
        b"fatal-looking private message with https://user:token@host/repo\n",
    ]
    stdout = b"x" * 256000 + "\nUnicode: 文件\n".encode()
    script = (
        "import os, time; from pathlib import Path\n"
        f"os.write(1, {stdout!r})\n"
        f"for chunk in {stderr_chunks[:3]!r}:\n"
        "    os.write(2, chunk)\n"
        "    time.sleep(0.01)\n"
        f"while not Path({str(released)!r}).exists(): time.sleep(0.01)\n"
        f"os.write(2, {b''.join(stderr_chunks[3:])!r})\n"
        f"Path({str(finished)!r}).touch()\n"
    )
    # Keep a large payload off argv, whose size limit differs across platforms.
    child = tmp_path / "child.py"
    child.write_text(script)
    events = []

    def on_progress(event):
        events.append(event)
        if event == GitProgress("Receiving objects", 43):
            assert not finished.exists(), "Progress must arrive before Git exits"
            released.touch()

    result = await GitManager()._run_subprocess(
        [sys.executable, str(child)],
        tmp_path,
        timeout=3,
        max_retries=0,
        capture_output=True,
        on_progress=on_progress,
    )
    assert result.stdout.encode() == stdout
    assert result.stderr.encode() == b"".join(stderr_chunks)
    assert events == [
        GitProgress("Enumerating objects"),
        GitProgress("Receiving objects", 43),
        GitProgress("Receiving objects", 100),
    ]
    assert finished.exists()


@pytest.mark.asyncio
async def test_real_local_clone_reports_measured_progress(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    seed = tmp_path / "seed"
    subprocess.run(["git", "init", str(seed)], check=True, capture_output=True)
    for index in range(8):
        (seed / f"file-{index}.txt").write_text(f"content {index}\n" * 100)
    subprocess.run(["git", "add", "."], cwd=seed, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "seed",
        ],
        cwd=seed,
        check=True,
        capture_output=True,
    )
    events = []
    await GitManager().git_clone(
        seed.as_uri(), tmp_path, "clone", on_progress=events.append
    )
    assert events[0] == GitProgress("Cloning")
    assert GitProgress("Receiving objects", 100) in events
    assert (tmp_path / "clone" / "file-7.txt").read_text() == "content 7\n" * 100


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["clone", "pull", "fetch"])
@pytest.mark.parametrize("enabled", [False, True])
async def test_git_requests_progress_only_for_subscribed_operations(
    tmp_path, monkeypatch, operation, enabled
):
    manager = GitManager()
    run = AsyncMock()
    monkeypatch.setattr(manager, "_run_subprocess", run)
    events = []
    callback = events.append if enabled else None
    if operation == "clone":
        await manager.git_clone("file:///seed", tmp_path, on_progress=callback)
    else:
        await getattr(manager, f"git_{operation}")(tmp_path, on_progress=callback)
    assert ("--progress" in run.call_args.args[0]) is enabled
    assert run.call_args.kwargs["on_progress"] == callback
    assert run.call_args.kwargs["log_level"] == (
        logging.DEBUG if enabled else logging.ERROR
    )
    initial_stage = {"clone": "Cloning", "pull": "Pulling", "fetch": "Fetching"}
    assert events == ([GitProgress(initial_stage[operation])] if enabled else [])


@pytest.mark.asyncio
async def test_progress_uses_c_locale_and_resets_activity_before_retry(
    tmp_path, monkeypatch
):
    manager = GitManager()
    events = []
    monkeypatch.setenv("LC_ALL", "fr_FR.UTF-8")
    calls = 0

    async def run(cmd, cwd, env, timeout, on_progress):
        nonlocal calls
        calls += 1
        assert env["LC_ALL"] == "C"
        on_progress(GitProgress("Receiving objects", 50 if calls == 1 else 100))
        if calls == 1:
            raise subprocess.CalledProcessError(128, cmd, stderr="Connection reset")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(manager, "_exec_once", run)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    await manager._run_subprocess(
        ["git", "fetch", "--progress"], tmp_path, on_progress=events.append
    )
    assert events == [
        GitProgress("Receiving objects", 50),
        GitProgress("Retrying"),
        GitProgress("Receiving objects", 100),
    ]
    assert os.environ["LC_ALL"] == "fr_FR.UTF-8"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["timeout", "retry", "permanent"])
async def test_progress_diagnostics_respect_debug_log_level(
    tmp_path, monkeypatch, caplog, failure
):
    monkeypatch.setattr(logging.getLogger("mgit"), "propagate", True)
    caplog.set_level(logging.DEBUG, logger="mgit.git.manager")
    manager = GitManager()
    cmd = ["git", "fetch", "--progress"]
    error = (
        subprocess.TimeoutExpired(cmd, 1)
        if failure == "timeout"
        else subprocess.CalledProcessError(
            128,
            cmd,
            stderr="Connection reset" if failure == "retry" else "Permission denied",
        )
    )
    monkeypatch.setattr(manager, "_exec_once", AsyncMock(side_effect=error))
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    with pytest.raises(subprocess.CalledProcessError):
        await manager._run_subprocess(
            cmd,
            tmp_path,
            log_level=logging.DEBUG,
            max_retries=1,
            on_progress=lambda event: None,
        )
    records = [record for record in caplog.records if record.name == "mgit.git.manager"]
    assert records
    assert all(record.levelno == logging.DEBUG for record in records)


@pytest.mark.asyncio
@pytest.mark.parametrize("returncode", [0, 1])
async def test_output_and_command_logs_mask_url_and_header_credentials(
    tmp_path, monkeypatch, caplog, returncode
):
    monkeypatch.setattr(logging.getLogger("mgit"), "propagate", True)
    caplog.set_level(logging.DEBUG, logger="mgit.git.manager")
    header = "Authorization: Basic private-token"
    url = "https://username:url-token@example.invalid/repo"
    stdout = f"stdout {header} {url}\n"
    stderr = f"Receiving objects: 25% (1/4)\r{header} {url}\n"
    script = (
        f"import sys; sys.stdout.write({stdout!r}); "
        f"sys.stderr.write({stderr!r}); sys.exit({returncode})"
    )
    child = tmp_path / "child.py"
    child.write_text(script)
    events = []
    cmd = [
        sys.executable,
        str(child),
        "-c",
        f"http.extraHeader={header}",
        f"--config=http.{url}.extraHeader={header}",
    ]
    run = GitManager()._run_subprocess(
        cmd, tmp_path, max_retries=0, on_progress=events.append
    )
    if returncode:
        with pytest.raises(subprocess.CalledProcessError) as error:
            await run
        assert error.value.stdout == stdout
        assert error.value.stderr == stderr
    else:
        result = await run
        assert result.stdout == stdout
        assert result.stderr == stderr
    assert events == [GitProgress("Receiving objects", 25)]
    assert "private-token" not in caplog.text
    assert "url-token" not in caplog.text
    assert "private-token" not in _sanitize_cmd_for_log(cmd)
    assert "url-token" not in _sanitize_cmd_for_log(cmd)


@pytest.mark.skipif(os.name != "posix", reason="POSIX process tree checks")
@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["cancel", "timeout", "callback"])
async def test_streaming_failure_terminates_git_and_helpers(tmp_path, failure):
    helper_pid = tmp_path / "helper.pid"
    parent_pid = tmp_path / "parent.pid"
    script = (
        "import os, subprocess, sys, time; from pathlib import Path\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(5)'])\n"
        f"Path({str(helper_pid)!r}).write_text(str(child.pid))\n"
        f"Path({str(parent_pid)!r}).write_text(str(os.getpid()))\n"
        "os.write(2, b'Receiving objects: 25% (1/4)\\r')\n"
        "time.sleep(5)\n"
    )
    started = asyncio.Event()

    def on_progress(event):
        started.set()
        if failure == "callback":
            raise ValueError("progress callback failed")

    task = asyncio.create_task(
        GitManager()._run_subprocess(
            [sys.executable, "-c", script],
            tmp_path,
            timeout=0.3 if failure == "timeout" else 5,
            max_retries=0,
            on_progress=on_progress,
        )
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=3)
        start = time.monotonic()
        if failure == "cancel":
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        elif failure == "callback":
            with pytest.raises(ValueError, match="progress callback failed"):
                await task
        else:
            with pytest.raises(subprocess.CalledProcessError) as error:
                await task
            assert error.value.returncode == 124
        assert time.monotonic() - start < 1.5
        for pid_file in (parent_pid, helper_pid):
            result = subprocess.run(
                ["ps", "-o", "stat=", "-p", pid_file.read_text()],
                capture_output=True,
                text=True,
            )
            assert not result.stdout.strip() or result.stdout.lstrip().startswith("Z")
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        for pid_file in (parent_pid, helper_pid):
            if pid_file.exists():
                with contextlib.suppress(ProcessLookupError):
                    os.kill(int(pid_file.read_text()), signal.SIGKILL)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("callback failure"),
        KeyboardInterrupt("callback failure"),
        asyncio.CancelledError("callback failure"),
        subprocess.TimeoutExpired("callback failure", 1),
        subprocess.CalledProcessError(7, "callback failure", stderr="Connection reset"),
    ],
)
async def test_callback_failures_keep_their_original_exception_without_retry(
    tmp_path, error
):
    calls = 0

    def fail(event):
        nonlocal calls
        calls += 1
        raise error

    with pytest.raises(type(error)) as observed_error:
        await GitManager()._run_subprocess(
            [
                sys.executable,
                "-c",
                "print('Counting objects: 50% (1/2)', file=__import__('sys').stderr)",
            ],
            tmp_path,
            on_progress=fail,
            max_retries=2,
            initial_delay=0,
        )
    assert observed_error.value is error
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("streaming", [False, True])
async def test_non_utf8_diagnostics_do_not_change_successful_exit(tmp_path, streaming):
    result = await GitManager()._run_subprocess(
        [
            sys.executable,
            "-c",
            "import os; os.write(1, b'path-\\xff'); os.write(2, b'hook-\\xff')",
        ],
        tmp_path,
        capture_output=True,
        on_progress=(lambda event: None) if streaming else None,
    )
    assert result.returncode == 0
    assert result.stdout == "path-\ufffd"
    assert result.stderr == "hook-\ufffd"

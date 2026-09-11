"""
Unit tests for local sync helper logic.
"""

import os
import subprocess
from pathlib import Path

import pytest

from mgit.commands.sync import (
    LOCAL_ACTION_FAILED,
    LOCAL_ACTION_PULL,
    LOCAL_ACTION_PULLED,
    LOCAL_ACTION_SKIP_DIRTY,
    LOCAL_ACTION_SKIP_NO_REMOTE,
    LocalRepoResult,
    LocalRepoState,
    _determine_local_action,
    _inspect_local_repository,
    _summarize_local_results,
)


def _make_state(
    *,
    remote_url: str | None = "https://example.com/org/repo.git",
    is_dirty: bool = False,
    error: str | None = None,
) -> LocalRepoState:
    return LocalRepoState(
        path=Path("/tmp/repo"),
        name="repo",
        remote_url=remote_url,
        provider="github",
        is_dirty=is_dirty,
        error=error,
    )


def test_determine_local_action_no_remote():
    state = _make_state(remote_url=None)
    assert _determine_local_action(state, force=False) == LOCAL_ACTION_SKIP_NO_REMOTE


def test_determine_local_action_dirty_without_force():
    state = _make_state(is_dirty=True)
    assert _determine_local_action(state, force=False) == LOCAL_ACTION_SKIP_DIRTY


def test_determine_local_action_dirty_with_force():
    state = _make_state(is_dirty=True)
    assert _determine_local_action(state, force=True) == LOCAL_ACTION_PULL


def test_determine_local_action_error():
    state = _make_state(error="git status failed")
    assert _determine_local_action(state, force=False) == LOCAL_ACTION_FAILED


def test_summarize_local_results_counts():
    state = _make_state()
    results = [
        LocalRepoResult(state=state, action=LOCAL_ACTION_PULL),
        LocalRepoResult(state=state, action=LOCAL_ACTION_PULLED),
        LocalRepoResult(state=state, action=LOCAL_ACTION_SKIP_DIRTY),
        LocalRepoResult(state=state, action=LOCAL_ACTION_SKIP_NO_REMOTE),
        LocalRepoResult(state=state, action=LOCAL_ACTION_FAILED),
    ]
    counts = _summarize_local_results(results)
    assert counts["total"] == 5
    assert counts["pulled"] == 2
    assert counts["skipped_dirty"] == 1
    assert counts["skipped_no_remote"] == 1
    assert counts["failed"] == 1


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="Arbitrary filename bytes require POSIX")
async def test_non_utf8_filename_is_dirty_instead_of_a_scan_failure(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "core.quotePath", "false"], cwd=tmp_path, check=True
    )
    (tmp_path / os.fsdecode(b"invalid-\xff.txt")).touch()
    subprocess.run(
        ["git", "remote", "add", "origin", "https://example.invalid/org/repo"],
        cwd=tmp_path,
        check=True,
    )
    state = await _inspect_local_repository(tmp_path)
    assert state.is_dirty
    assert state.error is None
    assert _determine_local_action(state, force=False) == LOCAL_ACTION_SKIP_DIRTY

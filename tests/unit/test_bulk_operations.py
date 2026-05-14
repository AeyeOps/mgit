"""Unit tests for BulkOperationProcessor case-collision force-sync."""

import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mgit.commands.bulk_operations import BulkOperationProcessor, OperationType


def _make_processor() -> BulkOperationProcessor:
    """Build a processor with a fully mocked GitManager (no real git calls)."""
    git_manager = MagicMock()
    git_manager.git_fetch = AsyncMock()
    git_manager.get_upstream_ref = AsyncMock(return_value="origin/main")
    git_manager.git_reset_hard = AsyncMock()
    return BulkOperationProcessor(
        git_manager=git_manager,
        provider_manager=MagicMock(),
        operation_type=OperationType.clone,
    )


def _commit_repo(path: Path) -> None:
    """Init a git repo with one committed file."""
    subprocess.run(
        ["git", "init", "-b", "main", str(path)], check=True, capture_output=True
    )
    (path / "f.txt").write_text("x\n")
    subprocess.run(["git", "add", "."], cwd=str(path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "c"], cwd=str(path), check=True, capture_output=True
    )


class TestForceSyncCaseCollision:
    """Test _force_sync_case_collision orchestration."""

    @pytest.mark.asyncio
    async def test_resets_pure_case_collision_to_upstream(self, monkeypatch):
        """A verified pure case-collision repo is fetched and hard-reset."""
        proc = _make_processor()
        monkeypatch.setattr(
            proc, "_is_pure_case_collision", AsyncMock(return_value=True)
        )
        await proc._force_sync_case_collision(
            Path("/tmp/repo"), "collide-repo", MagicMock(), 1, "collide-repo"
        )
        proc.git_manager.git_fetch.assert_awaited_once()
        proc.git_manager.git_reset_hard.assert_awaited_once_with(
            Path("/tmp/repo"), "origin/main"
        )
        assert proc.case_collision_synced == ["collide-repo"]
        assert proc.skipped == []
        assert proc.failures == []

    @pytest.mark.asyncio
    async def test_skips_when_genuine_edits_present(self, monkeypatch):
        """A repo with real edits alongside collisions is skipped, never reset."""
        proc = _make_processor()
        monkeypatch.setattr(
            proc, "_is_pure_case_collision", AsyncMock(return_value=False)
        )
        await proc._force_sync_case_collision(
            Path("/tmp/repo"), "collide-repo", MagicMock(), 1, "collide-repo"
        )
        proc.git_manager.git_fetch.assert_not_awaited()
        proc.git_manager.git_reset_hard.assert_not_awaited()
        assert proc.case_collision_synced == []
        assert len(proc.skipped) == 1
        assert proc.skipped[0][0] == "collide-repo"

    @pytest.mark.asyncio
    async def test_fetch_only_when_no_upstream(self, monkeypatch):
        """Without an upstream branch, fetch still runs but no reset is attempted."""
        proc = _make_processor()
        proc.git_manager.get_upstream_ref = AsyncMock(return_value=None)
        monkeypatch.setattr(
            proc, "_is_pure_case_collision", AsyncMock(return_value=True)
        )
        await proc._force_sync_case_collision(
            Path("/tmp/repo"), "collide-repo", MagicMock(), 1, "collide-repo"
        )
        proc.git_manager.git_fetch.assert_awaited_once()
        proc.git_manager.git_reset_hard.assert_not_awaited()
        assert proc.case_collision_synced == ["collide-repo"]

    @pytest.mark.asyncio
    async def test_records_failure_on_git_error(self, monkeypatch):
        """A git error during force-sync is recorded as a failure, not a crash."""
        proc = _make_processor()
        monkeypatch.setattr(
            proc, "_is_pure_case_collision", AsyncMock(return_value=True)
        )
        proc.git_manager.git_fetch = AsyncMock(
            side_effect=subprocess.CalledProcessError(
                1, ["git", "fetch"], stderr="fatal: boom"
            )
        )
        await proc._force_sync_case_collision(
            Path("/tmp/repo"), "collide-repo", MagicMock(), 1, "collide-repo"
        )
        assert proc.case_collision_synced == []
        assert len(proc.failures) == 1
        assert proc.failures[0][0] == "collide-repo"


class TestIsPureCaseCollision:
    """Test _is_pure_case_collision against real repos (filesystem-independent cases)."""

    @pytest.mark.asyncio
    async def test_false_for_clean_repo(self, tmp_path):
        """A clean repo has no dirty paths, so it is not a case-collision."""
        _commit_repo(tmp_path)
        assert await _make_processor()._is_pure_case_collision(tmp_path) is False

    @pytest.mark.asyncio
    async def test_false_for_genuine_edit(self, tmp_path):
        """A genuine edit with no colliding paths classifies as dirty, not collision."""
        _commit_repo(tmp_path)
        (tmp_path / "f.txt").write_text("edited\n")
        assert await _make_processor()._is_pure_case_collision(tmp_path) is False

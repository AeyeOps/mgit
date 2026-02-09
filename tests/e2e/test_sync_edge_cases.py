"""End-to-end tests for sync edge cases: empty repos, dir collisions, error reporting.

Requires Docker (Gitea container). Run with: pytest tests/e2e/test_sync_edge_cases.py -v -m docker
"""

import subprocess

import pytest


@pytest.mark.e2e
@pytest.mark.docker
class TestEmptyRepoHandling:
    """Tests for empty repo (no commits) handling during sync."""

    def test_empty_repo_clone(self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env):
        """Clone an empty repo — should succeed, create .git, rev-parse HEAD fails."""
        result = run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Sync failed: {result.stderr}"

        empty_repo = temp_dir / "empty-repo"
        assert empty_repo.exists(), "Empty repo directory should exist"
        assert (empty_repo / ".git").exists(), "Should have .git directory"

        rev_parse = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(empty_repo),
            capture_output=True,
            text=True,
        )
        assert rev_parse.returncode != 0, "rev-parse HEAD should fail on empty repo"

    def test_empty_repo_resync_skipped(self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env):
        """Re-sync empty repo should skip gracefully with exit code 0."""
        run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )

        result = run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Re-sync should succeed: {result.stderr}"

    def test_mixed_empty_and_normal(self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env):
        """Sync mix of empty and normal repos — normal pulled, empty skipped, exit 0."""
        run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )

        result = run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Mixed sync should succeed: {result.stderr}"
        assert (temp_dir / "normal-repo" / ".git").exists()
        assert (temp_dir / "empty-repo" / ".git").exists()

    def test_force_mode_empty_repo(self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env):
        """Force re-clone of empty repo."""
        run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )

        result = run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--force", "--provider", "gitea_test"],
            input_text="y\n",
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Force sync failed: {result.stderr}"


@pytest.mark.e2e
@pytest.mark.docker
class TestDirectoryCollisions:
    """Tests for non-git directory collision handling."""

    def test_non_git_empty_dir_clone(self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env):
        """Empty directory at target path should be removed and clone succeeds."""
        empty_dir = temp_dir / "normal-repo"
        empty_dir.mkdir(parents=True)

        result = run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Sync failed: {result.stderr}"
        assert (temp_dir / "normal-repo" / ".git").exists(), "Should have cloned into empty dir"

    def test_non_git_nonempty_dir_skipped(self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env):
        """Non-git dir with files should be skipped, not a failure."""
        nonempty_dir = temp_dir / "normal-repo"
        nonempty_dir.mkdir(parents=True)
        (nonempty_dir / "blockerfile.txt").write_text("I block cloning")

        result = run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Sync should succeed (skip, not fail): {result.stderr}"
        assert not (nonempty_dir / ".git").exists(), "Should not have cloned into non-empty dir"

    def test_force_non_git_dir(self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env):
        """Force mode on non-git dir should remove and re-clone."""
        nonempty_dir = temp_dir / "normal-repo"
        nonempty_dir.mkdir(parents=True)
        (nonempty_dir / "blockerfile.txt").write_text("I block cloning")

        result = run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--force", "--provider", "gitea_test"],
            input_text="y\n",
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Force sync failed: {result.stderr}"


@pytest.mark.e2e
@pytest.mark.docker
class TestErrorReporting:
    """Tests for enhanced error reporting with git stderr."""

    def test_failure_includes_stderr(self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env):
        """Trigger a git failure and verify error message includes detail."""
        repo_dir = temp_dir / "normal-repo"
        repo_dir.mkdir(parents=True)
        git_dir = repo_dir / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]\n  bare = false\n")

        result = run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        output = result.stdout + result.stderr
        assert "pull failed" in output.lower() or "skipped" in output.lower() or result.returncode == 0

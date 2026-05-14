"""End-to-end tests for sync edge cases: empty repos, dir collisions, error reporting.

Requires Docker (Gitea container). Run with: pytest tests/e2e/test_sync_edge_cases.py -v -m docker
"""

import re
import subprocess

import pytest


@pytest.mark.e2e
@pytest.mark.docker
class TestEmptyRepoHandling:
    """Tests for empty repo (no commits) handling during sync."""

    def test_empty_repo_clone(
        self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env
    ):
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

    def test_empty_repo_resync_skipped(
        self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env
    ):
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

    def test_mixed_empty_and_normal(
        self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env
    ):
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

    def test_force_mode_empty_repo(
        self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env
    ):
        """Force re-clone of empty repo."""
        run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )

        result = run_mgit(
            [
                "sync",
                "edge-test-org/*/*",
                str(temp_dir),
                "--force",
                "--provider",
                "gitea_test",
            ],
            input_text="y\n",
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Force sync failed: {result.stderr}"


@pytest.mark.e2e
@pytest.mark.docker
class TestDirectoryCollisions:
    """Tests for non-git directory collision handling."""

    def test_non_git_empty_dir_clone(
        self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env
    ):
        """Empty directory at target path should be removed and clone succeeds."""
        empty_dir = temp_dir / "normal-repo"
        empty_dir.mkdir(parents=True)

        result = run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Sync failed: {result.stderr}"
        assert (temp_dir / "normal-repo" / ".git").exists(), (
            "Should have cloned into empty dir"
        )

    def test_non_git_nonempty_dir_skipped(
        self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env
    ):
        """Non-git dir with files should be skipped, not a failure."""
        nonempty_dir = temp_dir / "normal-repo"
        nonempty_dir.mkdir(parents=True)
        (nonempty_dir / "blockerfile.txt").write_text("I block cloning")

        result = run_mgit(
            ["sync", "edge-test-org/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, (
            f"Sync should succeed (skip, not fail): {result.stderr}"
        )
        assert not (nonempty_dir / ".git").exists(), (
            "Should not have cloned into non-empty dir"
        )

    def test_force_non_git_dir(
        self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env
    ):
        """Force mode on non-git dir should remove and re-clone."""
        nonempty_dir = temp_dir / "normal-repo"
        nonempty_dir.mkdir(parents=True)
        (nonempty_dir / "blockerfile.txt").write_text("I block cloning")

        result = run_mgit(
            [
                "sync",
                "edge-test-org/*/*",
                str(temp_dir),
                "--force",
                "--provider",
                "gitea_test",
            ],
            input_text="y\n",
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Force sync failed: {result.stderr}"


@pytest.mark.e2e
@pytest.mark.docker
class TestErrorReporting:
    """Tests for enhanced error reporting with git stderr."""

    def test_failure_includes_stderr(
        self, run_mgit, temp_dir, gitea_edge_case_repos, gitea_mgit_env
    ):
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
        assert (
            "pull failed" in output.lower()
            or "skipped" in output.lower()
            or result.returncode == 0
        )


@pytest.mark.e2e
@pytest.mark.docker
class TestCaseCollisionReporting:
    """Tests for case-collision force-sync and complete summary reporting."""

    def _make_collision_dirty(self, temp_dir):
        """Make collide-repo dirty in a collision-only way.

        Writes content differing from HEAD to a case-colliding tracked path.
        Deterministic on both case-sensitive and case-insensitive filesystems:
        the only changed path is part of the case-collision set.
        """
        target = temp_dir / "collide-repo" / "teamcov5db" / "STATE.sql"
        target.write_text("-- locally changed\n")

    def test_case_collision_synced_to_origin(
        self, run_mgit, temp_dir, gitea_reporting_repos, gitea_mgit_env
    ):
        """A case-colliding repo is force-synced to origin, not abandoned."""
        org = gitea_reporting_repos["org"]
        run_mgit(
            ["sync", f"{org}/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        self._make_collision_dirty(temp_dir)

        result = run_mgit(
            ["sync", f"{org}/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, f"Sync should succeed: {output}"
        assert "case-colliding" in output, f"Expected case-collision label: {output}"
        assert "collide-repo" in output
        # The collision repo must NOT be reported as ordinary uncommitted changes.
        assert "uncommitted changes" not in output, (
            f"Case-collision repo mislabeled as uncommitted changes: {output}"
        )
        # The local artifact was discarded by the fetch + reset to origin: the
        # colliding file is back to its committed content, not the local edit.
        synced = (temp_dir / "collide-repo" / "teamcov5db" / "STATE.sql").read_text()
        assert synced != "-- locally changed\n", (
            f"Case-collision repo was not synced to origin: STATE.sql still {synced!r}"
        )

    def test_summary_counts_collision_repo_as_successful(
        self, run_mgit, temp_dir, gitea_reporting_repos, gitea_mgit_env
    ):
        """Summary reconciles and the collision repo lands in the successful tally."""
        org = gitea_reporting_repos["org"]
        run_mgit(
            ["sync", f"{org}/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        self._make_collision_dirty(temp_dir)

        result = run_mgit(
            ["sync", f"{org}/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, f"Sync should succeed: {output}"

        # Resolved total is 3: normal-repo, empty-repo, collide-repo.
        total = int(re.search(r"Total:\s*(\d+)", output).group(1))
        successful = int(re.search(r"Successful:\D*(\d+)", output).group(1))
        skipped = int(re.search(r"Skipped:\D*(\d+)", output).group(1))
        failed_match = re.search(r"Failed:\D*(\d+)", output)
        failed = int(failed_match.group(1)) if failed_match else 0

        assert total == 3, f"Expected resolved total of 3, got {total}: {output}"
        assert successful + skipped + failed == total, (
            f"Summary does not reconcile: {successful}+{skipped}+{failed} != {total}"
        )
        # normal-repo (pull) + collide-repo (force-sync) both succeed; only the
        # empty repo is skipped.
        assert successful == 2, (
            f"Expected collide-repo counted as successful, got {successful}: {output}"
        )
        assert skipped == 1, f"Only the empty repo should be skipped: {output}"


@pytest.mark.e2e
@pytest.mark.docker
class TestUnquotedGlobDetection:
    """Tests for detection of shell-expanded (unquoted) wildcard patterns."""

    def test_three_positional_args_detected(self, run_mgit, temp_dir):
        """3+ positional args (shell glob expansion) exits 2 with a quote hint."""
        result = run_mgit(["sync", "a/b/c", "d/e/f", "g/h/i"])
        output = result.stdout + result.stderr
        assert result.returncode == 2, f"Expected exit 2, got {result.returncode}"
        assert "quote" in output.lower(), f"Expected quoting hint: {output}"

    def test_two_positional_args_not_tripped(self, run_mgit, temp_dir):
        """A legitimate pattern + path call must not trip glob detection."""
        result = run_mgit(["sync", "no-such-org/*/*", str(temp_dir / "dest")])
        output = result.stdout + result.stderr
        assert "expanded an unquoted" not in output

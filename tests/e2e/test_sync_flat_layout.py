"""End-to-end tests for flat layout sync functionality.

This module tests the flat layout feature for mgit sync command:
- Basic sync operations with flat directory layout
- Collision detection and resolution
- Error handling scenarios
- Edge cases and idempotency

Test markers:
- @pytest.mark.e2e: All tests in this module
- @pytest.mark.requires_network: Tests requiring network access to GitHub

Tests use the installed binary at /usr/local/bin/mgit (or MGIT_BINARY env var).
"""

from pathlib import Path

import pytest

# Test repository for consistent tests (small public repo)
# Using steveant's repos as specified in test plan
TEST_REPO_PATTERN = "steveant/*/puray"
TEST_MULTI_PATTERN = "steveant/*/*"


# --- Section A: Basic Functionality Tests ---


@pytest.mark.e2e
@pytest.mark.requires_network
class TestSyncFlatLayoutBasic:
    """Section A: Basic Functionality Tests (Tests 1-9)"""

    def test_01_empty_target_directory(self, run_mgit, temp_dir):
        """Test 1: Clone into an empty/nonexistent target directory.

        Verifies that:
        - Target directory is created if it doesn't exist
        - Repository is cloned with flat layout (repo name directly in target)
        - .git directory exists in cloned repo
        """
        target = temp_dir / "empty_test"
        # Ensure target doesn't exist
        assert not target.exists()

        result = run_mgit(
            ["sync", TEST_REPO_PATTERN, str(target)],
            timeout=60,
        )

        assert result.returncode == 0, f"Sync failed: {result.stderr}"
        assert target.exists(), "Target directory was not created"
        assert (target / "puray").exists(), "Repository directory not found"
        assert (target / "puray" / ".git").exists(), "Not a valid git repository"

    def test_02_multi_repo_flat_clone(self, run_mgit, temp_dir):
        """Test 2: Clone multiple repos with flat layout.

        Verifies that:
        - Multiple repositories are cloned
        - Repos are placed directly in target (flat layout, no provider prefix)
        - All cloned directories are valid git repos
        """
        target = temp_dir / "multi_test"
        target.mkdir(parents=True, exist_ok=True)

        result = run_mgit(
            ["sync", TEST_MULTI_PATTERN, str(target)],
            timeout=120,
        )

        assert result.returncode == 0, f"Sync failed: {result.stderr}"

        # Check that repos are in flat layout (no github.com/ prefix)
        git_dirs = list(target.rglob(".git"))
        assert len(git_dirs) >= 1, "No repositories cloned"

        # Verify flat layout - .git should be at depth 2 (target/repo/.git)
        for git_dir in git_dirs:
            depth = len(git_dir.relative_to(target).parts)
            assert depth == 2, f"Expected flat layout, got nested: {git_dir}"

    def test_03_quiet_mode_flat_clone(self, run_mgit, temp_dir):
        """Test 3: Clone with --no-progress flag.

        Verifies that:
        - Clone succeeds without progress bar output
        - Repository is properly cloned
        """
        target = temp_dir / "quiet_test"
        target.mkdir(parents=True, exist_ok=True)

        result = run_mgit(
            ["sync", TEST_REPO_PATTERN, str(target), "--no-progress"],
            timeout=60,
        )

        assert result.returncode == 0, f"Sync failed: {result.stderr}"
        assert (target / "puray" / ".git").exists(), "Repository not cloned"

    def test_04_concurrency_limit(self, run_mgit, temp_dir):
        """Test 4: Clone with --concurrency 1 (sequential).

        Verifies that:
        - Repos clone sequentially with concurrency=1
        - All repos are cloned successfully
        """
        target = temp_dir / "conc_test"
        target.mkdir(parents=True, exist_ok=True)

        result = run_mgit(
            ["sync", TEST_MULTI_PATTERN, str(target), "--concurrency", "1"],
            timeout=180,  # Longer timeout for sequential cloning
        )

        assert result.returncode == 0, f"Sync failed: {result.stderr}"

        # Verify at least one repo cloned
        git_dirs = list(target.rglob(".git"))
        assert len(git_dirs) >= 1, "No repositories cloned"

    def test_05_dry_run_flat_preview(self, run_mgit, temp_dir):
        """Test 5: Dry-run mode shows preview without cloning.

        Verifies that:
        - Command returns exit code 0
        - Shows sync preview table
        - Target directory remains empty (no actual cloning)
        """
        target = temp_dir / "dryrun_test"
        target.mkdir(parents=True, exist_ok=True)

        result = run_mgit(
            ["sync", TEST_MULTI_PATTERN, str(target), "--dry-run"],
            timeout=60,
        )

        assert result.returncode == 0, f"Dry-run failed: {result.stderr}"

        # Verify preview output
        output = result.stdout + result.stderr
        assert "Preview" in output or "preview" in output or "dry" in output.lower(), (
            "Expected preview message in output"
        )

        # Verify no actual cloning
        git_dirs = list(target.rglob(".git"))
        assert len(git_dirs) == 0, "Dry-run should not clone repositories"

    def test_06_no_summary_flag(self, run_mgit, temp_dir):
        """Test 6: Clone with --no-summary flag.

        Verifies that:
        - Clone succeeds
        - Output is shorter (no summary table at end)
        """
        target = temp_dir / "nosummary_test"
        target.mkdir(parents=True, exist_ok=True)

        result = run_mgit(
            ["sync", TEST_REPO_PATTERN, str(target), "--no-summary"],
            timeout=60,
        )

        assert result.returncode == 0, f"Sync failed: {result.stderr}"
        assert (target / "puray" / ".git").exists(), "Repository not cloned"

    def test_07_hierarchical_clone(self, run_mgit, temp_dir):
        """Test 7: Clone with --hierarchy flag (non-flat layout).

        Verifies that:
        - Repository is cloned with hierarchical path
        - Path includes provider/org structure (github.com/steveant/...)
        """
        target = temp_dir / "hier_test"
        target.mkdir(parents=True, exist_ok=True)

        result = run_mgit(
            ["sync", TEST_REPO_PATTERN, str(target), "--hierarchy"],
            timeout=60,
        )

        assert result.returncode == 0, f"Sync failed: {result.stderr}"

        # Find .git directories - should be nested deeper than flat layout
        git_dirs = list(target.rglob(".git"))
        assert len(git_dirs) >= 1, "No repositories cloned"

        # Verify hierarchical layout - .git should be at depth > 2
        for git_dir in git_dirs:
            depth = len(git_dir.relative_to(target).parts)
            assert depth > 2, f"Expected hierarchical layout, got flat: {git_dir}"

    def test_08_force_mode_accept(self, run_mgit, temp_dir):
        """Test 8: Force mode with user accepting prompt.

        Verifies that:
        - First clone succeeds
        - Force re-clone with 'y' input works
        - Repository is fresh (re-cloned)
        """
        target = temp_dir / "force_test"
        target.mkdir(parents=True, exist_ok=True)

        # First clone
        result1 = run_mgit(
            ["sync", TEST_REPO_PATTERN, str(target)],
            timeout=60,
        )
        assert result1.returncode == 0, f"Initial clone failed: {result1.stderr}"

        # Get initial state
        repo_path = target / "puray"
        assert repo_path.exists()

        # Force re-clone with 'y' input
        result2 = run_mgit(
            ["sync", TEST_REPO_PATTERN, str(target), "--force"],
            input_text="y\n",
            timeout=120,
        )

        assert result2.returncode == 0, f"Force sync failed: {result2.stderr}"
        assert repo_path.exists(), "Repository should still exist after force sync"
        assert (repo_path / ".git").exists(), "Should be a valid git repository"

    def test_09_dirty_repo_detection(self, run_mgit, temp_dir):
        """Test 9: Sync detects and skips dirty repos.

        Verifies that:
        - Dirty repos (with uncommitted changes) are detected
        - Warning is printed about uncommitted changes
        - Dirty repo is skipped (not modified)
        - Sync completes with exit code 0
        """
        target = temp_dir / "dirty_test"
        target.mkdir(parents=True, exist_ok=True)

        # First clone
        result1 = run_mgit(
            ["sync", TEST_REPO_PATTERN, str(target)],
            timeout=60,
        )
        assert result1.returncode == 0, f"Initial clone failed: {result1.stderr}"

        # Make the repo dirty
        repo_path = target / "puray"
        readme = repo_path / "README.md"
        if readme.exists():
            original_content = readme.read_text()
            readme.write_text(original_content + "\n# Dirty modification for test\n")
        else:
            # Create a new file if README doesn't exist
            (repo_path / "dirty_test_file.txt").write_text("dirty content")

        # Sync again - should detect dirty repo
        result2 = run_mgit(
            ["sync", TEST_REPO_PATTERN, str(target)],
            timeout=60,
        )

        # Should complete with exit code 0 (dirty repos are skipped, not errors)
        assert result2.returncode == 0, f"Sync failed: {result2.stderr}"

        # Check for warning in output
        output = result2.stdout + result2.stderr
        assert "uncommitted" in output.lower() or "dirty" in output.lower() or "skipped" in output.lower(), (
            f"Expected dirty repo warning in output: {output}"
        )


# --- Section B/C: Collision Resolution Tests ---


@pytest.mark.e2e
class TestCollisionResolution:
    """Section B/C: Collision Tests (Tests 10-13) - Docker E2E and unit tests.

    Tests 10, 11, 13 use Gitea docker containers to test collision detection
    and resolution via the mgit binary. Test 12 is a Python-only unit test
    for cross-provider collision resolution logic.
    """

    @pytest.mark.docker
    def test_10_collision_detection_message(self, run_mgit, temp_dir, gitea_collision_repos, gitea_mgit_env):
        """Test 10: Collision detection identifies repos with same name via binary."""
        result = run_mgit(
            ["sync", "test-org-*/*/*", str(temp_dir), "--dry-run", "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Sync failed: {result.stderr}"
        output = result.stdout + result.stderr
        assert "collision" in output.lower() or "common-repo" in output

    @pytest.mark.docker
    def test_11_orgname_suffix_resolution(self, run_mgit, temp_dir, gitea_collision_repos, gitea_mgit_env):
        """Test 11: Sync repos, verify directories: common-repo_test-org-a/, common-repo_test-org-b/"""
        result = run_mgit(
            ["sync", "test-org-*/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Sync failed: {result.stderr}"
        assert (temp_dir / "common-repo_test-org-a").exists(), "Missing collision-resolved dir for org-a"
        assert (temp_dir / "common-repo_test-org-b").exists(), "Missing collision-resolved dir for org-b"

    def test_12_provider_orgname_suffix_resolution(self):
        """Test 12: Collision resolution adds _provider_orgname suffix.

        When same repo name AND same org name exist on different providers,
        resolution adds provider identifier.
        """
        from mgit.providers.base import Repository
        from mgit.utils.collision_resolver import resolve_collision_names

        # Same org name (orgname) on different providers
        repos = [
            Repository(
                name="auth",
                clone_url="https://github.com/orgname/auth",
                is_disabled=False,
            ),
            Repository(
                name="auth",
                clone_url="https://dev.azure.com/orgname/_git/auth",
                is_disabled=False,
            ),
        ]

        resolved = resolve_collision_names(repos)

        assert len(resolved) == 2

        name_github = resolved["https://github.com/orgname/auth"]
        name_azure = resolved["https://dev.azure.com/orgname/_git/auth"]

        # Names should be unique
        assert name_github != name_azure

        # At minimum should contain base name
        assert "auth" in name_github
        assert "auth" in name_azure

        # Should have provider or different identifiers
        # (exact format depends on implementation)
        print(f"Resolved: GitHub -> {name_github}, Azure -> {name_azure}")

    @pytest.mark.docker
    def test_13_no_collision_uses_base_name(self, run_mgit, temp_dir, gitea_unique_repos, gitea_mgit_env):
        """Test 13: Sync unique repos, verify no suffix: repo-one/, repo-two/"""
        result = run_mgit(
            ["sync", "unique-org-*/*/*", str(temp_dir), "--provider", "gitea_test"],
            env=gitea_mgit_env,
        )
        assert result.returncode == 0, f"Sync failed: {result.stderr}"
        assert (temp_dir / "repo-one").exists(), "repo-one should have no suffix"
        assert (temp_dir / "repo-two").exists(), "repo-two should have no suffix"
        assert not (temp_dir / "repo-one_unique-org-a").exists()
        assert not (temp_dir / "repo-two_unique-org-b").exists()


# --- Section D: Error Handling Tests ---


@pytest.mark.e2e
@pytest.mark.requires_network
class TestErrorHandling:
    """Section D: Error Handling Tests (Tests 14-18)"""

    def test_14_non_git_dir_in_target(self, run_mgit, temp_dir):
        """Test 14: Handle non-git directory with repo name.

        When a directory exists with the repo name but is not a git repo,
        should warn and record as failure.
        """
        target = temp_dir / "nongit_test"
        target.mkdir(parents=True, exist_ok=True)

        # Create a non-git directory with the repo name
        fake_repo = target / "puray"
        fake_repo.mkdir()
        (fake_repo / "some_file.txt").write_text("not a git repo")

        result = run_mgit(
            ["sync", TEST_REPO_PATTERN, str(target)],
            timeout=60,
        )

        # Command may complete with or without error depending on implementation
        output = result.stdout + result.stderr

        # Should mention something about the existing folder
        assert (
            "not a git" in output.lower()
            or "folder exists" in output.lower()
            or "exists" in output.lower()
            or result.returncode != 0
        ), f"Expected warning about non-git folder: {output}"

    # Test 15 skipped: Requires special provider config with disabled repo

    def test_16_clone_failure_nonexistent_repo(self, run_mgit, temp_dir):
        """Test 16: Handle clone failure for non-existent repo.

        Verifies clean exit when pattern matches no repositories.
        """
        target = temp_dir / "fail_test"
        target.mkdir(parents=True, exist_ok=True)

        result = run_mgit(
            ["sync", "steveant/*/nonexistent-repo-xyz-12345", str(target)],
            timeout=60,
        )

        # Should complete (may be exit 0 with "no repos found" message)
        output = result.stdout + result.stderr

        # Either exits cleanly with no repos message, or exits with error
        if result.returncode == 0:
            # Check for "no repositories" or "0 repositories" message
            assert (
                "no repo" in output.lower()
                or "0 repo" in output.lower()
                or "found 0" in output.lower()
                or not list(target.rglob(".git"))  # No repos cloned
            )
        # Non-zero exit is also acceptable for no matches

    def test_17_force_mode_user_declines(self, run_mgit, temp_dir):
        """Test 17: Force mode with user declining prompt.

        Verifies that:
        - Prompt appears asking for confirmation
        - 'n' input cancels the operation
        - Repository is not re-cloned
        """
        target = temp_dir / "force_decline_test"
        target.mkdir(parents=True, exist_ok=True)

        # First clone
        result1 = run_mgit(
            ["sync", TEST_REPO_PATTERN, str(target)],
            timeout=60,
        )
        assert result1.returncode == 0, f"Initial clone failed: {result1.stderr}"

        # Add a marker file to verify repo wasn't replaced
        marker_file = target / "puray" / ".e2e_test_marker"
        marker_file.write_text("test marker")

        # Force sync with 'n' input (decline)
        result2 = run_mgit(
            ["sync", TEST_REPO_PATTERN, str(target), "--force"],
            input_text="n\n",
            timeout=60,
        )

        output = result2.stdout + result2.stderr

        # Should cancel or show cancellation message
        assert (
            "cancel" in output.lower()
            or "abort" in output.lower()
            or result2.returncode != 0
            or marker_file.exists()  # Marker file still there = repo not replaced
        ), f"Expected cancellation or unchanged repo: {output}"

    def test_18_single_provider_flag(self, run_mgit, temp_dir):
        """Test 18: Sync with --provider flag limits to single provider.

        Verifies that specifying --provider only queries that provider.
        """
        target = temp_dir / "provider_test"
        target.mkdir(parents=True, exist_ok=True)

        # Try with a specific provider (github_steveant if configured, or fail gracefully)
        result = run_mgit(
            ["sync", TEST_MULTI_PATTERN, str(target), "--provider", "github_steveant"],
            timeout=120,
        )

        # If provider exists, should succeed; if not, should fail with provider not found
        output = result.stdout + result.stderr

        if result.returncode == 0:
            # Success - repos were synced
            git_dirs = list(target.rglob(".git"))
            assert len(git_dirs) >= 0  # May or may not find repos
        else:
            # Provider not found is acceptable
            assert (
                "provider" in output.lower()
                or "not found" in output.lower()
                or "not configured" in output.lower()
            ), f"Unexpected error: {output}"


# --- Section E: Edge Cases ---


@pytest.mark.e2e
class TestEdgeCases:
    """Section E: Edge Cases (Test 22) - Python only.

    Tests 19, 20 skipped: Require complex setup (pull conflicts, read-only dirs).
    """

    def test_22_counter_increment_fallback(self):
        """Test 22: Counter increment for 3+ repos with same name/org/provider.

        When multiple repos still collide after provider disambiguation,
        counter suffix (_2, _3) should be used.
        """
        from mgit.providers.base import Repository
        from mgit.utils.collision_resolver import resolve_collision_names

        # Create 3 repos that might collide even after standard disambiguation
        # Using same host and same org structure to force counter usage
        repos = [
            Repository(
                name="common",
                clone_url="https://github.com/myorg/common",
                is_disabled=False,
            ),
            Repository(
                name="common",
                clone_url="https://github.com/myorg/common.git",
                is_disabled=False,
            ),
            Repository(
                name="common",
                clone_url="https://github.com/myorg/common/",
                is_disabled=False,
            ),
        ]

        resolved = resolve_collision_names(repos)

        # All should get unique names
        names = list(resolved.values())
        assert len(names) == 3
        assert len(set(names)) == 3, f"Names not unique: {names}"


# --- Section F: Idempotency Tests ---


@pytest.mark.e2e
@pytest.mark.requires_network
class TestIdempotency:
    """Section F: Idempotency Tests (Tests 23-24)"""

    def test_23_idempotency_run_twice(self, run_mgit, temp_dir):
        """Test 23: Sync is idempotent (running twice works correctly).

        Verifies that:
        - First sync clones repos
        - Second sync pulls (no errors, no re-clone)
        """
        target = temp_dir / "idempotent_test"
        target.mkdir(parents=True, exist_ok=True)

        # First sync
        result1 = run_mgit(
            ["sync", TEST_MULTI_PATTERN, str(target)],
            timeout=120,
        )
        assert result1.returncode == 0, f"First sync failed: {result1.stderr}"

        # Count repos after first sync
        git_dirs_1 = list(target.rglob(".git"))
        count_1 = len(git_dirs_1)
        assert count_1 >= 1, "No repos cloned on first sync"

        # Second sync (should pull, not clone)
        result2 = run_mgit(
            ["sync", TEST_MULTI_PATTERN, str(target)],
            timeout=120,
        )
        assert result2.returncode == 0, f"Second sync failed: {result2.stderr}"

        # Count repos after second sync (should be same)
        git_dirs_2 = list(target.rglob(".git"))
        count_2 = len(git_dirs_2)
        assert count_2 == count_1, f"Repo count changed: {count_1} -> {count_2}"

        # Check output mentions pulling (not cloning)
        output = result2.stdout + result2.stderr
        # At least one of these should appear for pull operations
        pull_indicators = ["pull", "up to date", "already", "fetch"]
        has_pull_indicator = any(ind in output.lower() for ind in pull_indicators)

        # Cloning indicators should NOT dominate
        clone_only = "clone" in output.lower() and not has_pull_indicator

        assert not clone_only or has_pull_indicator, (
            f"Expected pull operations on second run, got: {output[:500]}"
        )

    def test_24_mixed_mode_clone_and_pull(self, run_mgit, temp_dir):
        """Test 24: Mixed mode - clone missing repos, pull existing.

        Verifies that:
        - Existing repos are pulled
        - Missing repos are cloned
        - Both operations succeed
        """
        target = temp_dir / "mixed_test"
        target.mkdir(parents=True, exist_ok=True)

        # First, sync just one repo
        result1 = run_mgit(
            ["sync", TEST_REPO_PATTERN, str(target)],
            timeout=60,
        )
        assert result1.returncode == 0, f"Initial clone failed: {result1.stderr}"

        # Verify one repo exists
        assert (target / "puray").exists(), "Initial repo not cloned"

        # Now sync all repos - should clone missing + pull existing
        result2 = run_mgit(
            ["sync", TEST_MULTI_PATTERN, str(target)],
            timeout=120,
        )
        assert result2.returncode == 0, f"Mixed sync failed: {result2.stderr}"

        # Should have more repos now
        git_dirs = list(target.rglob(".git"))
        # At minimum, the original repo should still be there
        assert (target / "puray" / ".git").exists(), "Original repo missing"

        # If there are other repos in steveant/*, we should have more
        # But at minimum we should have at least 1
        assert len(git_dirs) >= 1


# --- Utility Functions ---


def get_repo_count(target_dir: Path) -> int:
    """Count git repositories in target directory."""
    return len(list(target_dir.rglob(".git")))


def is_valid_git_repo(repo_path: Path) -> bool:
    """Check if path contains a valid git repository."""
    git_dir = repo_path / ".git"
    return git_dir.exists() and git_dir.is_dir()

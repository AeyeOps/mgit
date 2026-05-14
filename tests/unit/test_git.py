"""Unit tests for git-related functionality."""

import subprocess
from unittest.mock import AsyncMock, patch

import pytest

from mgit.git.manager import GitManager, sanitize_url
from mgit.git.utils import find_case_collisions


def _init_repo(path):
    """Init a git repo with one committed file."""
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    (path / "keep.txt").write_text("keep\n")
    subprocess.run(
        ["git", "add", "keep.txt"], cwd=str(path), check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(path),
        check=True,
        capture_output=True,
    )


def _add_index_entry(path, rel_path, content):
    """Add a tracked path to the index via plumbing (no working-tree file).

    Lets us create case-colliding tracked paths on any filesystem, including
    case-insensitive ones where both files cannot coexist on disk.
    """
    blob = (
        subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=str(path),
            input=content.encode(),
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .strip()
    )
    subprocess.run(
        ["git", "update-index", "--add", "--cacheinfo", f"100644,{blob},{rel_path}"],
        cwd=str(path),
        check=True,
        capture_output=True,
    )


class TestFindCaseCollisions:
    """Test find_case_collisions tracked-path collision detection."""

    def test_detects_colliding_paths(self, tmp_path):
        _init_repo(tmp_path)
        _add_index_entry(tmp_path, "dir/STATE.sql", "upper\n")
        _add_index_entry(tmp_path, "dir/State.sql", "mixed\n")
        result = find_case_collisions(tmp_path)
        assert result == {"dir/STATE.sql", "dir/State.sql"}

    def test_no_collisions_returns_empty(self, tmp_path):
        _init_repo(tmp_path)
        _add_index_entry(tmp_path, "dir/alpha.sql", "a\n")
        _add_index_entry(tmp_path, "dir/beta.sql", "b\n")
        assert find_case_collisions(tmp_path) == set()

    def test_non_git_dir_returns_empty(self, tmp_path):
        assert find_case_collisions(tmp_path) == set()

    def test_only_colliding_group_returned(self, tmp_path):
        _init_repo(tmp_path)
        _add_index_entry(tmp_path, "README.MD", "x\n")
        _add_index_entry(tmp_path, "readme.md", "y\n")
        _add_index_entry(tmp_path, "unique.txt", "z\n")
        result = find_case_collisions(tmp_path)
        assert result == {"README.MD", "readme.md"}


class TestSanitizeUrl:
    """Test sanitize_url credential removal."""

    def test_removes_credentials_from_https(self):
        assert (
            sanitize_url("https://user:pass@github.com/org/repo")
            == "https://***@github.com/org/repo"
        )

    def test_removes_pat_from_url(self):
        assert (
            sanitize_url("https://mytoken@dev.azure.com/org/_git/repo")
            == "https://***@dev.azure.com/org/_git/repo"
        )

    def test_preserves_url_without_credentials(self):
        assert (
            sanitize_url("https://github.com/org/repo") == "https://github.com/org/repo"
        )

    def test_handles_multiple_urls_in_text(self):
        text = "clone https://tok1@host.com/a and https://tok2@host.com/b"
        result = sanitize_url(text)
        assert "tok1" not in result
        assert "tok2" not in result
        assert "***@" in result

    def test_empty_string(self):
        assert sanitize_url("") == ""

    def test_no_url_in_text(self):
        assert sanitize_url("just some plain text") == "just some plain text"


class TestIsRepoEmpty:
    """Test GitManager.is_repo_empty with real temp git repos."""

    @pytest.fixture
    def git_manager(self):
        return GitManager()

    @pytest.mark.asyncio
    async def test_empty_repo_returns_true(self, tmp_path, git_manager):
        """A git init with no commits is empty."""
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        assert await git_manager.is_repo_empty(tmp_path) is True

    @pytest.mark.asyncio
    async def test_repo_with_commit_returns_false(self, tmp_path, git_manager):
        """A repo with at least one commit is not empty."""
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        (tmp_path / "file.txt").write_text("content")
        subprocess.run(
            ["git", "add", "."], cwd=str(tmp_path), check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )
        assert await git_manager.is_repo_empty(tmp_path) is False

    @pytest.mark.asyncio
    async def test_non_git_dir_returns_true(self, tmp_path, git_manager):
        """A directory without .git returns True (treated as empty for safety)."""
        assert await git_manager.is_repo_empty(tmp_path) is True


class TestRunSubprocessTimeout:
    """Test timeout handling in _run_subprocess."""

    @pytest.fixture
    def git_manager(self):
        return GitManager()

    @pytest.mark.asyncio
    async def test_timeout_raises_called_process_error(self, tmp_path, git_manager):
        """TimeoutExpired should be converted to CalledProcessError with code 124."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["git"], timeout=1),
        ):
            with pytest.raises(subprocess.CalledProcessError) as exc_info:
                await git_manager._run_subprocess(
                    ["git", "status"],
                    cwd=tmp_path,
                    timeout=1,
                    max_retries=0,
                )
            assert exc_info.value.returncode == 124
            assert "timed out" in exc_info.value.stderr


class TestRunSubprocessRetry:
    """Test retry logic in _run_subprocess."""

    @pytest.fixture
    def git_manager(self):
        return GitManager()

    @pytest.mark.asyncio
    async def test_transient_failure_retries_then_succeeds(self, tmp_path, git_manager):
        """Transient error (Connection reset) retries and succeeds."""
        success_result = subprocess.CompletedProcess(
            args=["git", "pull"],
            returncode=0,
            stdout="ok",
            stderr="",
        )
        transient_error = subprocess.CalledProcessError(
            128,
            ["git", "pull"],
            output="",
            stderr="fatal: Connection reset by peer",
        )

        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise transient_error
            return success_result

        with (
            patch("subprocess.run", side_effect=mock_run),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await git_manager._run_subprocess(
                ["git", "pull"],
                cwd=tmp_path,
                max_retries=3,
                initial_delay=0.01,
                backoff=1.0,
            )
        assert result.returncode == 0
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_permanent_failure_no_retry(self, tmp_path, git_manager):
        """Permanent error (not found) should not retry."""
        permanent_error = subprocess.CalledProcessError(
            128,
            ["git", "pull"],
            output="",
            stderr="fatal: repository 'https://example.com/repo' not found",
        )

        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise permanent_error

        with (
            patch("subprocess.run", side_effect=mock_run),
            pytest.raises(subprocess.CalledProcessError),
        ):
            await git_manager._run_subprocess(
                ["git", "pull"],
                cwd=tmp_path,
                max_retries=3,
                initial_delay=0.01,
                backoff=1.0,
            )
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_non_transient_failure_no_retry(self, tmp_path, git_manager):
        """Non-transient error (no commits) should not retry."""
        error = subprocess.CalledProcessError(
            128,
            ["git", "pull"],
            output="",
            stderr="fatal: your current branch 'main' does not have any commits yet",
        )

        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise error

        with (
            patch("subprocess.run", side_effect=mock_run),
            pytest.raises(subprocess.CalledProcessError),
        ):
            await git_manager._run_subprocess(
                ["git", "pull"],
                cwd=tmp_path,
                max_retries=3,
                initial_delay=0.01,
                backoff=1.0,
            )
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_exhausted(self, tmp_path, git_manager):
        """All retries fail with transient error — should raise."""
        transient_error = subprocess.CalledProcessError(
            128,
            ["git", "pull"],
            output="",
            stderr="fatal: Could not resolve host: github.com",
        )

        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise transient_error

        with (
            patch("subprocess.run", side_effect=mock_run),
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(subprocess.CalledProcessError),
        ):
            await git_manager._run_subprocess(
                ["git", "pull"],
                cwd=tmp_path,
                max_retries=2,
                initial_delay=0.01,
                backoff=1.0,
            )
        assert call_count == 3  # initial + 2 retries


class TestRunSubprocessLogLevel:
    """Test log_level parameter controls logging behavior."""

    @pytest.fixture
    def git_manager(self):
        return GitManager()

    @pytest.mark.asyncio
    async def test_debug_log_level_for_expected_failures(
        self, tmp_path, git_manager, caplog
    ):
        """is_repo_empty uses DEBUG log level, not ERROR."""
        import logging

        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)

        with caplog.at_level(logging.DEBUG, logger="mgit.git.manager"):
            result = await git_manager.is_repo_empty(tmp_path)

        assert result is True
        error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_records) == 0, f"Expected no ERROR logs, got: {error_records}"


class TestGitFetchResetUpstream:
    """Test git_fetch, get_upstream_ref, git_reset_hard against real repos."""

    @pytest.fixture
    def git_manager(self):
        return GitManager()

    @staticmethod
    def _make_origin_and_clone(tmp_path):
        """Create an origin repo with one commit and a clone tracking it."""
        origin = tmp_path / "origin"
        origin.mkdir()
        subprocess.run(
            ["git", "init", "-b", "main", str(origin)],
            check=True,
            capture_output=True,
        )
        (origin / "file.txt").write_text("v1\n")
        subprocess.run(
            ["git", "add", "."], cwd=str(origin), check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "v1"],
            cwd=str(origin),
            check=True,
            capture_output=True,
        )
        clone = tmp_path / "clone"
        subprocess.run(
            ["git", "clone", str(origin), str(clone)],
            check=True,
            capture_output=True,
        )
        return origin, clone

    @pytest.mark.asyncio
    async def test_get_upstream_ref_returns_tracking_branch(
        self, tmp_path, git_manager
    ):
        """A cloned repo's current branch tracks origin/<branch>."""
        _, clone = self._make_origin_and_clone(tmp_path)
        assert await git_manager.get_upstream_ref(clone) == "origin/main"

    @pytest.mark.asyncio
    async def test_get_upstream_ref_none_without_upstream(self, tmp_path, git_manager):
        """A standalone repo with no remote tracking returns None."""
        repo = tmp_path / "solo"
        subprocess.run(
            ["git", "init", "-b", "main", str(repo)], check=True, capture_output=True
        )
        (repo / "f.txt").write_text("x\n")
        subprocess.run(
            ["git", "add", "."], cwd=str(repo), check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "c"],
            cwd=str(repo),
            check=True,
            capture_output=True,
        )
        assert await git_manager.get_upstream_ref(repo) is None

    @pytest.mark.asyncio
    async def test_git_fetch_updates_remote_tracking(self, tmp_path, git_manager):
        """git_fetch advances the remote-tracking ref without touching HEAD."""
        origin, clone = self._make_origin_and_clone(tmp_path)
        (origin / "file.txt").write_text("v2\n")
        subprocess.run(
            ["git", "commit", "-am", "v2"],
            cwd=str(origin),
            check=True,
            capture_output=True,
        )
        await git_manager.git_fetch(clone)
        count = subprocess.run(
            ["git", "rev-list", "--count", "origin/main"],
            cwd=str(clone),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert count == "2", "origin/main should have the fetched second commit"

    @pytest.mark.asyncio
    async def test_git_reset_hard_moves_to_ref_and_discards_changes(
        self, tmp_path, git_manager
    ):
        """git_reset_hard moves the branch to the ref and discards local changes."""
        origin, clone = self._make_origin_and_clone(tmp_path)
        (origin / "file.txt").write_text("v2\n")
        subprocess.run(
            ["git", "commit", "-am", "v2"],
            cwd=str(origin),
            check=True,
            capture_output=True,
        )
        await git_manager.git_fetch(clone)
        (clone / "file.txt").write_text("local junk\n")
        await git_manager.git_reset_hard(clone, "origin/main")
        assert (clone / "file.txt").read_text() == "v2\n"
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(clone),
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert status == "", "working tree should be clean after hard reset"

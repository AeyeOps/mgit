"""Unit tests for git-related functionality."""

import subprocess
from unittest.mock import AsyncMock, patch

import pytest

from mgit.git.manager import GitManager, sanitize_url


class TestSanitizeUrl:
    """Test sanitize_url credential removal."""

    def test_removes_credentials_from_https(self):
        assert sanitize_url("https://user:pass@github.com/org/repo") == "https://***@github.com/org/repo"

    def test_removes_pat_from_url(self):
        assert sanitize_url("https://mytoken@dev.azure.com/org/_git/repo") == "https://***@dev.azure.com/org/_git/repo"

    def test_preserves_url_without_credentials(self):
        assert sanitize_url("https://github.com/org/repo") == "https://github.com/org/repo"

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
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=str(tmp_path), check=True, capture_output=True,
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
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["git"], timeout=1)):
            with pytest.raises(subprocess.CalledProcessError) as exc_info:
                await git_manager._run_subprocess(
                    ["git", "status"], cwd=tmp_path, timeout=1, max_retries=0,
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
            args=["git", "pull"], returncode=0, stdout="ok", stderr="",
        )
        transient_error = subprocess.CalledProcessError(
            128, ["git", "pull"], output="", stderr="fatal: Connection reset by peer",
        )

        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise transient_error
            return success_result

        with patch("subprocess.run", side_effect=mock_run), patch("asyncio.sleep", new_callable=AsyncMock):
            result = await git_manager._run_subprocess(
                ["git", "pull"], cwd=tmp_path, max_retries=3,
                initial_delay=0.01, backoff=1.0,
            )
        assert result.returncode == 0
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_permanent_failure_no_retry(self, tmp_path, git_manager):
        """Permanent error (not found) should not retry."""
        permanent_error = subprocess.CalledProcessError(
            128, ["git", "pull"], output="",
            stderr="fatal: repository 'https://example.com/repo' not found",
        )

        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise permanent_error

        with patch("subprocess.run", side_effect=mock_run), pytest.raises(subprocess.CalledProcessError):
            await git_manager._run_subprocess(
                ["git", "pull"], cwd=tmp_path, max_retries=3,
                initial_delay=0.01, backoff=1.0,
            )
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_non_transient_failure_no_retry(self, tmp_path, git_manager):
        """Non-transient error (no commits) should not retry."""
        error = subprocess.CalledProcessError(
            128, ["git", "pull"], output="",
            stderr="fatal: your current branch 'main' does not have any commits yet",
        )

        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise error

        with patch("subprocess.run", side_effect=mock_run), pytest.raises(subprocess.CalledProcessError):
            await git_manager._run_subprocess(
                ["git", "pull"], cwd=tmp_path, max_retries=3,
                initial_delay=0.01, backoff=1.0,
            )
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_exhausted(self, tmp_path, git_manager):
        """All retries fail with transient error — should raise."""
        transient_error = subprocess.CalledProcessError(
            128, ["git", "pull"], output="",
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
                ["git", "pull"], cwd=tmp_path, max_retries=2,
                initial_delay=0.01, backoff=1.0,
            )
        assert call_count == 3  # initial + 2 retries


class TestRunSubprocessLogLevel:
    """Test log_level parameter controls logging behavior."""

    @pytest.fixture
    def git_manager(self):
        return GitManager()

    @pytest.mark.asyncio
    async def test_debug_log_level_for_expected_failures(self, tmp_path, git_manager, caplog):
        """is_repo_empty uses DEBUG log level, not ERROR."""
        import logging

        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)

        with caplog.at_level(logging.DEBUG, logger="mgit.git.manager"):
            result = await git_manager.is_repo_empty(tmp_path)

        assert result is True
        error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_records) == 0, f"Expected no ERROR logs, got: {error_records}"

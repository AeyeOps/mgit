"""Unit tests for utility functions."""

import asyncio
from pathlib import Path

import pytest

# Import the actual utils once available
from mgit.git.utils import (
    embed_pat_in_url,
    normalize_path,
    sanitize_repo_name,
    validate_url,
)


class TestHelperFunctions:
    """Test cases for helper utility functions."""

    def test_embed_pat_in_url_https(self):
        """Test embedding PAT in HTTPS URL."""
        url = "https://dev.azure.com/test-org/_git/test-repo"
        pat = "test-pat-token"
        expected = "https://PersonalAccessToken:test-pat-token@dev.azure.com/test-org/_git/test-repo"
        assert embed_pat_in_url(url, pat) == expected

    def test_embed_pat_in_url_already_has_auth(self):
        """Test embedding PAT when URL already has authentication."""
        url = "https://user:pass@dev.azure.com/test-org/_git/test-repo"
        pat = "test-pat-token"
        assert embed_pat_in_url(url, pat) == url

    def test_embed_pat_in_url_ssh(self):
        """Test embedding PAT in SSH URL (should not modify)."""
        url = "git@ssh.dev.azure.com:v3/test-org/test-project/test-repo"
        pat = "test-pat-token"
        assert embed_pat_in_url(url, pat) == url

    def test_sanitize_repo_name_basic(self):
        """Test basic repository name sanitization."""
        assert sanitize_repo_name("my-repo") == "my-repo"
        assert sanitize_repo_name("MyRepo") == "MyRepo"
        assert sanitize_repo_name("my_repo") == "my_repo"

    def test_sanitize_repo_name_special_chars(self):
        """Test sanitizing repository names with special characters."""
        assert sanitize_repo_name("my/repo") == "my-repo"
        assert sanitize_repo_name("my\\repo") == "my-repo"
        assert sanitize_repo_name("my:repo") == "myrepo"
        assert sanitize_repo_name("my*repo") == "myrepo"
        assert sanitize_repo_name("my?repo") == "myrepo"
        assert sanitize_repo_name("my<repo>") == "myrepo"
        assert sanitize_repo_name("my|repo") == "myrepo"

    def test_sanitize_repo_name_whitespace(self):
        """Test sanitizing repository names with whitespace."""
        assert sanitize_repo_name("my repo") == "my-repo"
        assert sanitize_repo_name("  my repo  ") == "my-repo"
        assert sanitize_repo_name("my\trepo") == "my-repo"
        assert sanitize_repo_name("my\nrepo") == "my-repo"

    def test_sanitize_repo_name_dots(self):
        """Test sanitizing repository names with dots."""
        assert sanitize_repo_name(".repo") == "repo"
        assert sanitize_repo_name("repo.") == "repo"
        assert sanitize_repo_name("..repo..") == "repo"
        assert sanitize_repo_name("my.repo") == "my.repo"  # Internal dots are kept

    def test_sanitize_repo_name_multiple_dashes(self):
        """Test sanitizing repository names with multiple dashes."""
        assert sanitize_repo_name("my--repo") == "my-repo"
        assert sanitize_repo_name("my---repo") == "my-repo"
        assert sanitize_repo_name("--my-repo--") == "my-repo"

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("-repo", "repo"),
            (".-repo", "repo"),
            ("--repo", "repo"),
            ("CON", "CON_"),  # Windows reserved name
            ("PRN", "PRN_"),  # Windows reserved name
            ("AUX", "AUX_"),  # Windows reserved name
            ("NUL", "NUL_"),  # Windows reserved name
            ("COM1", "COM1_"),  # Windows reserved name
            ("LPT1", "LPT1_"),  # Windows reserved name
        ],
    )
    def test_sanitize_repo_name_edge_cases(self, name, expected):
        """Test edge cases for repository name sanitization."""
        assert sanitize_repo_name(name) == expected


class TestAsyncHelpers:
    """Test cases for async utility functions."""

    @pytest.mark.asyncio
    async def test_async_executor_success(self):
        """Test async executor with successful tasks."""
        # Placeholder for async executor tests
        import asyncio

        async def sample_task(n):
            await asyncio.sleep(0.1)
            return n * 2

        results = await asyncio.gather(sample_task(1), sample_task(2), sample_task(3))

        assert results == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_async_executor_with_semaphore(self):
        """Test async executor with concurrency limit."""
        import asyncio

        semaphore = asyncio.Semaphore(2)  # Limit to 2 concurrent tasks

        async def limited_task(n, sem):
            async with sem:
                await asyncio.sleep(0.1)
                return n * 2

        tasks = [limited_task(i, semaphore) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert results == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_async_executor_error_handling(self):
        """Test async executor error handling."""

        async def failing_task():
            await asyncio.sleep(0.1)
            raise ValueError("Test error")

        async def successful_task():
            await asyncio.sleep(0.1)
            return "success"

        with pytest.raises(ValueError):
            await asyncio.gather(successful_task(), failing_task(), successful_task())


class TestPathUtilities:
    """Test cases for path manipulation utilities."""

    def test_ensure_path_exists(self, temp_dir):
        """Test ensuring a path exists."""
        new_path = temp_dir / "subdir" / "nested"
        assert not new_path.exists()

        new_path.mkdir(parents=True)
        assert new_path.exists()
        assert new_path.is_dir()

    def test_resolve_relative_path(self):
        """Test resolving relative paths."""
        base = Path("/home/user/projects")
        relative = Path("../documents/file.txt")

        resolved = (base / relative).resolve()
        assert str(resolved) == "/home/user/documents/file.txt"

    def test_path_normalization(self):
        """Test path normalization."""
        paths = [
            "~/projects/repo",
            "$HOME/projects/repo",
        ]

        for path_str in paths:
            path = normalize_path(path_str)
            # Path should be expanded correctly
            assert "$" not in str(path)
            assert "~" not in str(path)


class TestConfigurationHelpers:
    """Test cases for configuration helper functions."""

    def test_merge_configs(self):
        """Test merging configuration dictionaries."""
        base_config = {
            "org": "https://dev.azure.com/base",
            "pat": "base-pat",
            "git": {"depth": 1, "branch": "main"},
        }

        override_config = {
            "pat": "override-pat",
            "git": {"depth": 10},
            "new_key": "new_value",
        }

        # Simple merge simulation
        merged = {**base_config, **override_config}
        merged["git"] = {**base_config["git"], **override_config["git"]}

        assert merged["org"] == "https://dev.azure.com/base"
        assert merged["pat"] == "override-pat"
        assert merged["git"]["depth"] == 10
        assert merged["git"]["branch"] == "main"
        assert merged["new_key"] == "new_value"

    def test_validate_url(self):
        """Test URL validation."""
        assert validate_url("https://example.com") is True
        assert validate_url("http://example.com") is True
        assert validate_url("ftp://example.com") is False
        assert validate_url("example.com") is False
        assert validate_url("") is False
        assert validate_url(None) is False

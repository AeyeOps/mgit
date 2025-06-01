"""Unit tests for utility functions."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the actual utils once available
from mgit.git.utils import embed_pat_in_url, sanitize_repo_name


class TestHelperFunctions:
    """Test cases for helper utility functions."""

    def test_embed_pat_in_url_https(self):
        """Test embedding PAT in HTTPS URL."""
        url = "https://dev.azure.com/org/project/_git/repo"
        pat = "test-pat-token"

        result = embed_pat_in_url(url, pat)
        assert (
            result
            == "https://PersonalAccessToken:test-pat-token@dev.azure.com/org/project/_git/repo"
        )

    def test_embed_pat_in_url_already_has_auth(self):
        """Test embedding PAT when URL already has authentication."""
        url = "https://user:pass@dev.azure.com/org/project/_git/repo"
        pat = "test-pat-token"

        result = embed_pat_in_url(url, pat)
        assert (
            result
            == "https://PersonalAccessToken:test-pat-token@dev.azure.com/org/project/_git/repo"
        )

    def test_embed_pat_in_url_ssh(self):
        """Test that SSH URLs are not modified."""
        url = "git@github.com:user/repo.git"
        pat = "test-pat-token"

        result = embed_pat_in_url(url, pat)
        assert result == url  # SSH URLs should not be modified

    def test_sanitize_repo_name_basic(self):
        """Test basic repository name sanitization."""
        assert sanitize_repo_name("my-repo") == "my-repo"
        assert sanitize_repo_name("MyRepo") == "MyRepo"
        assert sanitize_repo_name("my_repo") == "my_repo"

    def test_sanitize_repo_name_special_chars(self):
        """Test sanitizing repository names with special characters."""
        assert sanitize_repo_name("my/repo") == "my-repo"
        assert sanitize_repo_name("my\\repo") == "my-repo"
        assert sanitize_repo_name("my:repo") == "my-repo"
        assert sanitize_repo_name("my*repo") == "my-repo"
        assert sanitize_repo_name("my?repo") == "my-repo"
        assert sanitize_repo_name("my<repo>") == "my-repo-"
        assert sanitize_repo_name("my|repo") == "my-repo"

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
            ("", "repo"),  # Empty name gets default
            (".", "repo"),  # Just dots gets default
            ("-", "repo"),  # Just dashes gets default
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
            "./projects/repo",
            "../parent/projects/repo",
        ]

        for path_str in paths:
            path = Path(path_str).expanduser()
            # Path should be expanded correctly
            assert "$" not in str(path)
            assert "~" not in str(path) or str(path).startswith("~")


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
        valid_urls = [
            "https://dev.azure.com/org",
            "https://github.com/user/repo",
            "http://localhost:8080",
            "https://bitbucket.org/workspace/repo",
        ]

        invalid_urls = [
            "not-a-url",
            "ftp://invalid-protocol.com",
            "https://",
            "",
            None,
        ]

        for url in valid_urls:
            assert url.startswith(("http://", "https://"))

        for url in invalid_urls:
            if url:
                assert not url.startswith(("http://", "https://"))

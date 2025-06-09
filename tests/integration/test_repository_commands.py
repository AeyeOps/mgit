"""Integration tests for mgit CLI repository commands."""

import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mgit.__main__ import app
from mgit.providers.base import Repository


@pytest.mark.integration
class TestCloneAllCommand:
    """Test cases for the clone-all command."""

    def test_clone_all_success(
        self, cli_runner, temp_dir, mock_azure_repos, monkeypatch
    ):
        """Test cloning all repositories successfully."""
        monkeypatch.chdir(temp_dir)
        dest_dir = temp_dir / "repos"

        # Mock authentication and repository fetching
        with patch("mgit.__main__.ProviderManager") as mock_manager:
            manager_instance = mock_manager.return_value
            manager_instance.test_connection.return_value = True
            manager_instance.get_authenticated_clone_url.side_effect = (
                lambda repo: repo.clone_url
            )

            async def mock_list_repos(*args, **kwargs):
                for repo in mock_azure_repos:
                    yield repo

            manager_instance.list_repositories = mock_list_repos

            # Mock git clone operations
            with patch("mgit.__main__.GitManager") as mock_git_manager:
                git_instance = mock_git_manager.return_value
                git_instance.git_clone = AsyncMock()

                result = cli_runner.invoke(
                    app, ["clone-all", "test-project", str(dest_dir)]
                )

                assert result.exit_code == 0
                assert "Processing Repositories" in result.stdout

    def test_clone_all_with_concurrency(
        self, cli_runner, temp_dir, mock_azure_repos, monkeypatch
    ):
        """Test cloning with custom concurrency limit."""
        monkeypatch.chdir(temp_dir)
        dest_dir = temp_dir / "repos"

        with patch("mgit.__main__.ProviderManager") as mock_manager:
            manager_instance = mock_manager.return_value
            manager_instance.test_connection.return_value = True
            manager_instance.get_authenticated_clone_url.side_effect = (
                lambda repo: repo.clone_url
            )

            async def mock_list_repos(*args, **kwargs):
                for repo in mock_azure_repos:
                    yield repo

            manager_instance.list_repositories = mock_list_repos

            with patch("asyncio.Semaphore") as mock_semaphore:
                with patch("mgit.__main__.GitManager") as mock_git_manager:
                    git_instance = mock_git_manager.return_value
                    git_instance.git_clone = AsyncMock()
                    result = cli_runner.invoke(
                        app, ["clone-all", "test-project", str(dest_dir), "-c", "3"]
                    )

                    assert result.exit_code == 0
                    mock_semaphore.assert_called_with(3)

    def test_clone_all_skip_existing(
        self, cli_runner, temp_dir, mock_azure_repos, monkeypatch
    ):
        """Test skipping existing repositories."""
        monkeypatch.chdir(temp_dir)
        dest_dir = temp_dir / "repos"
        dest_dir.mkdir()

        # Create an existing repo
        existing_repo = dest_dir / "https-dev.azure.com-test-org-_git-repo-1"
        existing_repo.mkdir()
        (existing_repo / ".git").mkdir()

        with patch("mgit.__main__.ProviderManager") as mock_manager:
            manager_instance = mock_manager.return_value
            manager_instance.test_connection.return_value = True
            manager_instance.get_authenticated_clone_url.side_effect = (
                lambda repo: repo.clone_url
            )

            async def mock_list_repos(*args, **kwargs):
                for repo in mock_azure_repos:
                    yield repo

            manager_instance.list_repositories = mock_list_repos

            with patch("mgit.__main__.GitManager") as mock_git_manager:
                git_instance = mock_git_manager.return_value
                git_instance.git_clone = AsyncMock()
                result = cli_runner.invoke(
                    app, ["clone-all", "test-project", str(dest_dir), "-um", "skip"]
                )

                assert result.exit_code == 0
                assert "Skipped (exists)" in result.stdout


@pytest.mark.integration
class TestPullAllCommand:
    """Test cases for the pull-all command."""

    @pytest.fixture
    def pull_workspace(self, tmp_path):
        """Create a temporary workspace with git repos for pulling."""
        workspace = tmp_path / "pull_workspace"
        workspace.mkdir()

        # Create repos with the sanitized names that match what the code expects
        for i in range(3):
            repo_dir = workspace / f"http-a.com-repo-{i}"  # Match sanitized URL
            repo_dir.mkdir()
            subprocess.run(["git", "init"], cwd=repo_dir, check=True)
            (repo_dir / "README.md").write_text(f"repo-{i}")
            subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_dir, check=True)

        return workspace

    def test_pull_all_success(self, cli_runner, pull_workspace, monkeypatch):
        """Test pulling all repositories successfully."""
        monkeypatch.chdir(pull_workspace)

        with patch("mgit.__main__.ProviderManager") as mock_manager:
            manager_instance = mock_manager.return_value
            manager_instance.test_connection.return_value = True
            manager_instance.provider_name = "mock"
            manager_instance.provider_type = "azuredevops"

            # Create a proper async generator for list_repositories
            async def mock_list_repos(*args, **kwargs):
                for i in range(3):
                    yield Repository(
                        name=f"repo-{i}",
                        clone_url=f"http://a.com/repo-{i}",
                        is_disabled=False,
                        ssh_url="",
                        is_private=False,
                        default_branch="main",
                        size=0,
                        provider="mock",
                        metadata={},
                    )

            manager_instance.list_repositories = mock_list_repos
            manager_instance.get_authenticated_clone_url = MagicMock(
                side_effect=lambda repo: repo.clone_url
            )

            with patch("mgit.__main__.GitManager") as mock_git_manager:
                git_instance = mock_git_manager.return_value
                git_instance.GIT_EXECUTABLE = (
                    "git"  # Set this to avoid MagicMock in join
                )
                git_instance.git_pull = AsyncMock()

                result = cli_runner.invoke(
                    app,
                    ["pull-all", "test-project", str(pull_workspace), "-um", "pull"],
                )

                assert result.exit_code == 0
                assert "Processing Repositories" in result.stdout
                assert git_instance.git_pull.call_count == 3

    def test_pull_all_with_errors(self, cli_runner, pull_workspace, monkeypatch):
        """Test pull-all handling repository errors."""
        monkeypatch.chdir(pull_workspace)

        with patch("mgit.__main__.ProviderManager") as mock_manager:
            manager_instance = mock_manager.return_value
            manager_instance.test_connection.return_value = True
            manager_instance.provider_name = "mock"
            manager_instance.provider_type = "azuredevops"

            # Create a proper async generator for list_repositories
            async def mock_list_repos(*args, **kwargs):
                for i in range(2):
                    yield Repository(
                        name=f"repo-{i}",
                        clone_url=f"http://a.com/repo-{i}",
                        is_disabled=False,
                        ssh_url="",
                        is_private=False,
                        default_branch="main",
                        size=0,
                        provider="mock",
                        metadata={},
                    )

            manager_instance.list_repositories = mock_list_repos
            manager_instance.get_authenticated_clone_url = MagicMock(
                side_effect=lambda repo: repo.clone_url
            )

            with patch("mgit.__main__.GitManager") as mock_git_manager:
                git_instance = mock_git_manager.return_value
                git_instance.GIT_EXECUTABLE = (
                    "git"  # Set this to avoid MagicMock in join
                )
                git_instance.git_pull = AsyncMock(
                    side_effect=[None, subprocess.CalledProcessError(1, "git")]
                )

                result = cli_runner.invoke(
                    app,
                    ["pull-all", "test-project", str(pull_workspace), "-um", "pull"],
                )

                assert result.exit_code == 0
                assert "Pull Failed" in result.stdout

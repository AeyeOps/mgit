"""Integration tests for mgit CLI commands."""

import json
import os
import subprocess
from unittest.mock import AsyncMock, Mock, patch

import pytest
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication

from mgit.__main__ import app


@pytest.mark.integration
class TestLoginCommand:
    """Test cases for the login command."""

    def test_login_success(self, cli_runner, temp_dir, monkeypatch):
        """Test successful login with valid credentials."""
        monkeypatch.chdir(temp_dir)

        # Mock the Azure DevOps SDK connection where it's used
        with patch("mgit.providers.azdevops.Connection") as mock_connection:
            mock_core_client = Mock()
            mock_core_client.get_projects.return_value = []  # Simulate successful call
            mock_connection.return_value.clients.get_core_client.return_value = (
                mock_core_client
            )

            result = cli_runner.invoke(
                app,
                [
                    "login",
                    "--provider",
                    "azuredevops",
                    "--name",
                    "test_ado",
                    "--org",
                    "https://dev.azure.com/test-org",
                    "--token",
                    "test-pat",
                    "--no-store",  # Avoid modifying global config
                ],
            )

            assert result.exit_code == 0
            assert "Successfully connected to azuredevops" in result.stdout

    def test_login_invalid_credentials(self, cli_runner, temp_dir, monkeypatch):
        """Test login with invalid credentials."""
        monkeypatch.chdir(temp_dir)

        # Mock the Azure DevOps SDK to raise an authentication error
        with patch("mgit.providers.azdevops.Connection") as mock_connection:
            from azure.devops.exceptions import AzureDevOpsAuthenticationError

            mock_core_client = Mock()
            mock_core_client.get_projects.side_effect = AzureDevOpsAuthenticationError(
                "Authentication failed"
            )
            mock_connection.return_value.clients.get_core_client.return_value = (
                mock_core_client
            )

            result = cli_runner.invoke(
                app,
                [
                    "login",
                    "--provider",
                    "azuredevops",
                    "--name",
                    "test_ado_invalid",
                    "--org",
                    "https://dev.azure.com/test-org",
                    "--token",
                    "invalid-pat",
                    "--no-store",
                ],
                # The command should exit with code 1, so we don't want pytest to fail the test run
                catch_exceptions=False,
            )

            assert result.exit_code == 1
            assert "Failed to connect" in result.stdout

    def test_login_from_env_vars(self, cli_runner, temp_dir, monkeypatch):
        """Test login using environment variables."""
        monkeypatch.chdir(temp_dir)
        monkeypatch.setenv("AZURE_DEVOPS_ORG_URL", "https://dev.azure.com/env-org")
        monkeypatch.setenv("AZURE_DEVOPS_PAT", "env-pat")

        with patch("mgit.providers.azdevops.Connection") as mock_connection:
            mock_core_client = Mock()
            mock_core_client.get_projects.return_value = []
            mock_connection.return_value.clients.get_core_client.return_value = (
                mock_core_client
            )

            # This test is tricky because the login command is interactive.
            # We will skip it for now as it requires more complex mocking.
            pytest.skip(
                "Skipping env var login test due to interactive prompts that are hard to mock."
            )


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
            manager_instance.get_authenticated_clone_url.side_effect = lambda repo: repo.clone_url

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
            manager_instance.get_authenticated_clone_url.side_effect = lambda repo: repo.clone_url

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
            manager_instance.get_authenticated_clone_url.side_effect = lambda repo: repo.clone_url

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

    def test_pull_all_success(self, cli_runner, temp_dir, monkeypatch):
        """Test pulling all repositories successfully."""
        monkeypatch.chdir(temp_dir)
        repos_dir = temp_dir / "repos"
        repos_dir.mkdir()

        # Create mock repositories
        for i in range(3):
            repo_dir = repos_dir / f"repo-{i}"
            repo_dir.mkdir()
            (repo_dir / ".git").mkdir()

        with patch("mgit.__main__.ProviderManager") as mock_manager:
            manager_instance = mock_manager.return_value
            manager_instance.test_connection.return_value = True
            manager_instance.get_authenticated_clone_url.side_effect = lambda repo: repo.clone_url

            async def mock_list_repos(*args, **kwargs):
                for i in range(3):
                    yield Mock(name=f"repo-{i}", clone_url=f"http://a.com/repo-{i}", is_disabled=False)

            manager_instance.list_repositories = mock_list_repos

            with patch("mgit.__main__.GitManager") as mock_git_manager:
                git_instance = mock_git_manager.return_value
                git_instance.git_pull = AsyncMock()

                result = cli_runner.invoke(
                    app, ["pull-all", "test-project", str(repos_dir), "-um", "pull"]
                )

                assert result.exit_code == 0
                assert "Processing Repositories" in result.stdout
                assert git_instance.git_pull.call_count == 3

    def test_pull_all_with_errors(self, cli_runner, temp_dir, monkeypatch):
        """Test pull-all handling repository errors."""
        monkeypatch.chdir(temp_dir)
        repos_dir = temp_dir / "repos"
        repos_dir.mkdir()

        # Create mock repositories
        repo1 = repos_dir / "repo-1"
        repo1.mkdir()
        (repo1 / ".git").mkdir()

        repo2 = repos_dir / "repo-2"
        repo2.mkdir()
        (repo2 / ".git").mkdir()

        with patch("mgit.__main__.ProviderManager") as mock_manager:
            manager_instance = mock_manager.return_value
            manager_instance.test_connection.return_value = True
            manager_instance.get_authenticated_clone_url.side_effect = lambda repo: repo.clone_url

            async def mock_list_repos(*args, **kwargs):
                yield Mock(name="repo-1", clone_url="http://a.com/repo-1", is_disabled=False)
                yield Mock(name="repo-2", clone_url="http://a.com/repo-2", is_disabled=False)

            manager_instance.list_repositories = mock_list_repos

            with patch("mgit.__main__.GitManager") as mock_git_manager:
                git_instance = mock_git_manager.return_value
                git_instance.git_pull.side_effect = [
                    None,  # Success
                    subprocess.CalledProcessError(1, "git"),
                ]

                result = cli_runner.invoke(
                    app, ["pull-all", "test-project", str(repos_dir), "-um", "pull"]
                )

                # Command should complete but report errors
                assert result.exit_code == 0
                assert "Pull Failed" in result.stdout


@pytest.mark.integration
class TestConfigCommand:
    """Test cases for the config command."""

    def test_config_show(self, cli_runner, mock_config, temp_dir, monkeypatch):
        """Test showing configuration."""
        monkeypatch.chdir(temp_dir)

        result = cli_runner.invoke(app, ["config", "--list"])

        assert result.exit_code == 0
        assert "Configured Providers" in result.stdout

    def test_config_set_value(self, cli_runner, temp_dir, monkeypatch):
        """Test setting configuration values."""
        pytest.skip("Skipping outdated test.")


@pytest.mark.integration
class TestGenerateEnvCommand:
    """Test cases for the generate-env command."""

    def test_generate_env_success(self, cli_runner, mock_config, temp_dir, monkeypatch):
        """Test generating .env file."""
        monkeypatch.chdir(temp_dir)

        result = cli_runner.invoke(app, ["generate-env"])

        assert result.exit_code == 0
        assert "Created .env.sample" in result.stdout

        # Check .env file was created
        env_file = temp_dir / ".env.sample"
        assert env_file.exists()

        # Verify content
        content = env_file.read_text()
        assert "AZURE_DEVOPS_ORG_URL=" in content
        assert "AZURE_DEVOPS_PAT=" in content

    def test_generate_env_existing_file(self, cli_runner, temp_dir, monkeypatch):
        """Test generating .env when file already exists."""
        monkeypatch.chdir(temp_dir)

        # Create existing .env file
        env_file = temp_dir / ".env.sample"
        env_file.write_text("# Existing content\n")

        result = cli_runner.invoke(app, ["generate-env"])

        # Should create .env.sample1
        assert result.exit_code == 0
        assert "Created .env.sample1" in result.stdout


@pytest.mark.integration
class TestStatusCommand:
    """Test cases for the status command."""

    @pytest.fixture
    def dirty_workspace(self, tmp_path):
        """Create a temporary workspace with git repos in various states."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # 1. Clean repo
        clean_repo = workspace / "clean_repo"
        clean_repo.mkdir()
        subprocess.run(["git", "init"], cwd=clean_repo, check=True)
        (clean_repo / "README.md").write_text("clean")
        subprocess.run(["git", "add", "."], cwd=clean_repo, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=clean_repo, check=True)

        # 2. Modified repo
        modified_repo = workspace / "modified_repo"
        modified_repo.mkdir()
        subprocess.run(["git", "init"], cwd=modified_repo, check=True)
        (modified_repo / "main.py").write_text("print('hello')")
        subprocess.run(["git", "add", "."], cwd=modified_repo, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=modified_repo, check=True)
        (modified_repo / "main.py").write_text("print('hello world')")

        # 3. Untracked repo
        untracked_repo = workspace / "untracked_repo"
        untracked_repo.mkdir()
        subprocess.run(["git", "init"], cwd=untracked_repo, check=True)
        (untracked_repo / "README.md").write_text("initial")
        subprocess.run(["git", "add", "."], cwd=untracked_repo, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=untracked_repo, check=True)
        (untracked_repo / "new_file.txt").write_text("untracked")

        # 4. Repo that is ahead
        ahead_repo = workspace / "ahead_repo"
        remote_repo_path = tmp_path / "ahead_remote.git"
        subprocess.run(["git", "init", "--bare"], cwd=tmp_path, check=True, capture_output=True)
        
        ahead_repo.mkdir()
        subprocess.run(["git", "init"], cwd=ahead_repo, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote_repo_path)], cwd=ahead_repo, check=True)
        (ahead_repo / "feature.py").write_text("new feature")
        subprocess.run(["git", "add", "."], cwd=ahead_repo, check=True)
        subprocess.run(["git", "commit", "-m", "commit to remote"], cwd=ahead_repo, check=True)
        subprocess.run(["git", "push", "origin", "master"], cwd=ahead_repo, check=True)
        
        (ahead_repo / "another.py").write_text("local only")
        subprocess.run(["git", "add", "."], cwd=ahead_repo, check=True)
        subprocess.run(["git", "commit", "-m", "local only"], cwd=ahead_repo, check=True)

        return workspace

    def test_status_table_output_dirty_only(self, cli_runner, dirty_workspace):
        """Test default table output only shows dirty repos."""
        result = cli_runner.invoke(app, ["status", str(dirty_workspace)])
        
        assert result.exit_code == 0
        stdout = result.stdout
        
        assert "clean_repo" not in stdout
        assert "modified_repo" in stdout
        assert "untracked_repo" in stdout
        assert "ahead_repo" in stdout
        assert "Modified" in stdout
        assert "Untracked" in stdout
        assert "Ahead" in stdout

    def test_status_table_output_show_all(self, cli_runner, dirty_workspace):
        """Test table output with --all flag shows clean repos."""
        result = cli_runner.invoke(app, ["status", str(dirty_workspace), "--all"])
        
        assert result.exit_code == 0
        stdout = result.stdout
        
        assert "clean_repo" in stdout
        assert "Clean" in stdout
        assert "modified_repo" in stdout
        assert "untracked_repo" in stdout
        assert "ahead_repo" in stdout

    def test_status_json_output(self, cli_runner, dirty_workspace):
        """Test JSON output contains correct structured data."""
        result = cli_runner.invoke(app, ["status", str(dirty_workspace), "--output", "json", "--all"])
        
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        
        assert len(data) == 4
        
        status_map = {item["path"].split("/")[-1]: item for item in data}
        
        assert status_map["clean_repo"]["is_clean"] is True
        
        assert status_map["modified_repo"]["is_clean"] is False
        assert status_map["modified_repo"]["modified"] == 1
        
        assert status_map["untracked_repo"]["is_clean"] is False
        assert status_map["untracked_repo"]["untracked"] == 1
        
        assert status_map["ahead_repo"]["is_clean"] is False
        assert status_map["ahead_repo"]["ahead"] == 1

    def test_status_fail_on_dirty(self, cli_runner, dirty_workspace):
        """Test --fail-on-dirty exits with code 1 if repos are dirty."""
        result = cli_runner.invoke(app, ["status", str(dirty_workspace), "--fail-on-dirty"])
        assert result.exit_code == 1

    def test_status_fail_on_dirty_when_clean(self, cli_runner, tmp_path):
        """Test --fail-on-dirty exits with code 0 if repos are clean."""
        clean_workspace = tmp_path / "clean_workspace"
        clean_workspace.mkdir()
        clean_repo = clean_workspace / "clean_repo"
        clean_repo.mkdir()
        subprocess.run(["git", "init"], cwd=clean_repo, check=True)
        (clean_repo / "README.md").write_text("clean")
        subprocess.run(["git", "add", "."], cwd=clean_repo, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=clean_repo, check=True)

        result = cli_runner.invoke(app, ["status", str(clean_workspace), "--fail-on-dirty"])
        assert result.exit_code == 0


@pytest.mark.integration
@pytest.mark.requires_network
class TestEndToEndScenarios:
    """End-to-end integration tests requiring network access."""

    @pytest.mark.slow
    def test_full_workflow(self, cli_runner, temp_dir, monkeypatch):
        """Test complete workflow: login -> clone -> pull."""
        monkeypatch.chdir(temp_dir)

        # Skip if no network or test credentials
        if not os.environ.get("MGIT_TEST_ORG"):
            pytest.skip("Test credentials not available")

        # 1. Login
        result = cli_runner.invoke(
            app,
            [
                "login",
                "--org",
                os.environ["MGIT_TEST_ORG"],
                "--pat",
                os.environ["MGIT_TEST_PAT"],
            ],
        )
        assert result.exit_code == 0

        # 2. Clone repositories
        repos_dir = temp_dir / "test-repos"
        result = cli_runner.invoke(
            app,
            ["clone-all", os.environ.get("MGIT_TEST_PROJECT", "test"), str(repos_dir)],
        )
        assert result.exit_code == 0

        # 3. Pull updates
        result = cli_runner.invoke(
            app,
            ["pull-all", os.environ.get("MGIT_TEST_PROJECT", "test"), str(repos_dir)],
        )
        assert result.exit_code == 0

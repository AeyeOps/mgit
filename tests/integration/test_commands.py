"""Integration tests for mgit CLI commands."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from mgit.__main__ import app


@pytest.mark.integration
class TestLoginCommand:
    """Test cases for the login command."""

    def test_login_success(self, cli_runner, temp_dir, monkeypatch):
        """Test successful login with valid credentials."""
        monkeypatch.chdir(temp_dir)
        
        # Mock the API response for authentication
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"id": "test-user"}
            
            result = cli_runner.invoke(
                app,
                ["login", "--org", "https://dev.azure.com/test-org", "--pat", "test-pat"]
            )
            
            assert result.exit_code == 0
            assert "Successfully authenticated" in result.stdout
            
            # Check that config was saved
            config_file = temp_dir / ".mgit" / "config.json"
            assert config_file.exists()

    def test_login_invalid_credentials(self, cli_runner, temp_dir, monkeypatch):
        """Test login with invalid credentials."""
        monkeypatch.chdir(temp_dir)
        
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 401
            mock_get.return_value.text = "Unauthorized"
            
            result = cli_runner.invoke(
                app,
                ["login", "--org", "https://dev.azure.com/test-org", "--pat", "invalid-pat"]
            )
            
            assert result.exit_code == 1
            assert "Authentication failed" in result.stdout

    def test_login_from_env_vars(self, cli_runner, temp_dir, monkeypatch):
        """Test login using environment variables."""
        monkeypatch.chdir(temp_dir)
        monkeypatch.setenv("AZURE_DEVOPS_ORG", "https://dev.azure.com/env-org")
        monkeypatch.setenv("AZURE_DEVOPS_PAT", "env-pat")
        
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"id": "test-user"}
            
            result = cli_runner.invoke(app, ["login"])
            
            assert result.exit_code == 0
            assert "Successfully authenticated" in result.stdout


@pytest.mark.integration
class TestCloneAllCommand:
    """Test cases for the clone-all command."""

    def test_clone_all_success(self, cli_runner, temp_dir, mock_azure_repos, monkeypatch):
        """Test cloning all repositories successfully."""
        monkeypatch.chdir(temp_dir)
        dest_dir = temp_dir / "repos"
        
        # Mock authentication and repository fetching
        with patch("mgit.__main__.AzDevOpsManager") as mock_manager:
            manager_instance = Mock()
            manager_instance.authenticate.return_value = True
            manager_instance.get_repositories.return_value = mock_azure_repos
            mock_manager.return_value = manager_instance
            
            # Mock git clone operations
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                
                result = cli_runner.invoke(
                    app,
                    ["clone-all", "test-project", str(dest_dir)]
                )
                
                assert result.exit_code == 0
                assert "Cloning repositories" in result.stdout
                assert "Successfully cloned" in result.stdout

    def test_clone_all_with_concurrency(self, cli_runner, temp_dir, mock_azure_repos, monkeypatch):
        """Test cloning with custom concurrency limit."""
        monkeypatch.chdir(temp_dir)
        dest_dir = temp_dir / "repos"
        
        with patch("mgit.__main__.AzDevOpsManager") as mock_manager:
            manager_instance = Mock()
            manager_instance.authenticate.return_value = True
            manager_instance.get_repositories.return_value = mock_azure_repos
            mock_manager.return_value = manager_instance
            
            with patch("asyncio.Semaphore") as mock_semaphore:
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0
                    
                    result = cli_runner.invoke(
                        app,
                        ["clone-all", "test-project", str(dest_dir), "-c", "3"]
                    )
                    
                    assert result.exit_code == 0
                    mock_semaphore.assert_called_with(3)

    def test_clone_all_skip_existing(self, cli_runner, temp_dir, mock_azure_repos, monkeypatch):
        """Test skipping existing repositories."""
        monkeypatch.chdir(temp_dir)
        dest_dir = temp_dir / "repos"
        dest_dir.mkdir()
        
        # Create an existing repo
        existing_repo = dest_dir / "test-repo-1"
        existing_repo.mkdir()
        (existing_repo / ".git").mkdir()
        
        with patch("mgit.__main__.AzDevOpsManager") as mock_manager:
            manager_instance = Mock()
            manager_instance.authenticate.return_value = True
            manager_instance.get_repositories.return_value = mock_azure_repos
            mock_manager.return_value = manager_instance
            
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                
                result = cli_runner.invoke(
                    app,
                    ["clone-all", "test-project", str(dest_dir), "-u", "skip"]
                )
                
                assert result.exit_code == 0
                assert "Skipping existing repository" in result.stdout


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
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Already up to date.\n"
            
            result = cli_runner.invoke(
                app,
                ["pull-all", "test-project", str(repos_dir)]
            )
            
            assert result.exit_code == 0
            assert "Pulling updates" in result.stdout
            assert mock_run.call_count >= 3

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
        
        with patch("subprocess.run") as mock_run:
            # First repo succeeds, second fails
            mock_run.side_effect = [
                Mock(returncode=0, stdout="Updated\n", stderr=""),
                Mock(returncode=1, stdout="", stderr="Error: merge conflict\n"),
            ]
            
            result = cli_runner.invoke(
                app,
                ["pull-all", "test-project", str(repos_dir)]
            )
            
            # Command should complete but report errors
            assert result.exit_code == 0
            assert "Error pulling" in result.stdout


@pytest.mark.integration
class TestConfigCommand:
    """Test cases for the config command."""

    def test_config_show(self, cli_runner, mock_config, temp_dir, monkeypatch):
        """Test showing configuration."""
        monkeypatch.chdir(temp_dir)
        
        result = cli_runner.invoke(app, ["config", "--show"])
        
        assert result.exit_code == 0
        assert "Configuration" in result.stdout

    def test_config_set_value(self, cli_runner, temp_dir, monkeypatch):
        """Test setting configuration values."""
        monkeypatch.chdir(temp_dir)
        config_dir = temp_dir / ".mgit"
        config_dir.mkdir()
        
        result = cli_runner.invoke(
            app,
            ["config", "--set", "default_project=new-project"]
        )
        
        assert result.exit_code == 0
        assert "Configuration updated" in result.stdout
        
        # Verify config was written
        config_file = config_dir / "config.json"
        if config_file.exists():
            config_data = json.loads(config_file.read_text())
            assert config_data.get("default_project") == "new-project"


@pytest.mark.integration
class TestGenerateEnvCommand:
    """Test cases for the generate-env command."""

    def test_generate_env_success(self, cli_runner, mock_config, temp_dir, monkeypatch):
        """Test generating .env file."""
        monkeypatch.chdir(temp_dir)
        
        result = cli_runner.invoke(app, ["generate-env"])
        
        assert result.exit_code == 0
        assert "Generated .env file" in result.stdout
        
        # Check .env file was created
        env_file = temp_dir / ".env"
        assert env_file.exists()
        
        # Verify content
        content = env_file.read_text()
        assert "AZURE_DEVOPS_ORG=" in content
        assert "AZURE_DEVOPS_PAT=" in content

    def test_generate_env_existing_file(self, cli_runner, temp_dir, monkeypatch):
        """Test generating .env when file already exists."""
        monkeypatch.chdir(temp_dir)
        
        # Create existing .env file
        env_file = temp_dir / ".env"
        env_file.write_text("# Existing content\n")
        
        result = cli_runner.invoke(app, ["generate-env"])
        
        # Should warn about existing file
        assert result.exit_code == 0
        assert "already exists" in result.stdout or "Generated .env file" in result.stdout


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
                "--org", os.environ["MGIT_TEST_ORG"],
                "--pat", os.environ["MGIT_TEST_PAT"]
            ]
        )
        assert result.exit_code == 0
        
        # 2. Clone repositories
        repos_dir = temp_dir / "test-repos"
        result = cli_runner.invoke(
            app,
            ["clone-all", os.environ.get("MGIT_TEST_PROJECT", "test"), str(repos_dir)]
        )
        assert result.exit_code == 0
        
        # 3. Pull updates
        result = cli_runner.invoke(
            app,
            ["pull-all", os.environ.get("MGIT_TEST_PROJECT", "test"), str(repos_dir)]
        )
        assert result.exit_code == 0
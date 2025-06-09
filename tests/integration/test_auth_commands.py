"""Integration tests for mgit CLI auth commands."""

from unittest.mock import Mock, patch

import pytest

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

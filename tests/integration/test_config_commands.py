"""Integration tests for mgit CLI config commands."""

import os

import pytest

from mgit.__main__ import app


@pytest.mark.integration
class TestConfigCommand:
    """Test cases for the config command."""

    def test_config_show(
        self, cli_runner, config_file, temp_dir, temp_home_dir, monkeypatch
    ):
        """Test showing configuration."""
        monkeypatch.chdir(temp_dir)
        # The config_file fixture creates the file in the correct location
        # But we need to ensure mgit uses our test home directory
        result = cli_runner.invoke(app, ["config", "--list"])

        assert result.exit_code == 0
        assert "Configured Providers" in result.stdout
        assert "azure" in result.stdout

    def test_config_set_value(self, cli_runner, temp_dir, monkeypatch):
        """Test setting configuration values."""
        pytest.skip("Skipping outdated test.")


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

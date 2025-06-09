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
class TestGenerateEnvCommand:
    """Test cases for the generate-env command."""

    def test_generate_env_success(
        self, cli_runner, config_file, temp_dir, temp_home_dir, monkeypatch
    ):
        """Test generating .env file."""
        monkeypatch.chdir(temp_dir)
        # The config_file fixture creates the file in the correct location
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

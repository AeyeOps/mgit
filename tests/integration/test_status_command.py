"""Integration tests for mgit CLI status command."""

import json
import subprocess

import pytest

from mgit.__main__ import app


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
        subprocess.run(
            ["git", "commit", "-m", "initial commit"], cwd=clean_repo, check=True
        )

        # 2. Modified repo
        modified_repo = workspace / "modified_repo"
        modified_repo.mkdir()
        subprocess.run(["git", "init"], cwd=modified_repo, check=True)
        (modified_repo / "main.py").write_text("print('hello')")
        subprocess.run(["git", "add", "."], cwd=modified_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "initial commit"], cwd=modified_repo, check=True
        )
        (modified_repo / "main.py").write_text("print('hello world')")

        # 3. Untracked repo
        untracked_repo = workspace / "untracked_repo"
        untracked_repo.mkdir()
        subprocess.run(["git", "init"], cwd=untracked_repo, check=True)
        (untracked_repo / "README.md").write_text("initial")
        subprocess.run(["git", "add", "."], cwd=untracked_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "initial commit"], cwd=untracked_repo, check=True
        )
        (untracked_repo / "new_file.txt").write_text("untracked")

        # 4. Repo that is ahead
        ahead_repo = workspace / "ahead_repo"
        remote_repo_path = tmp_path / "ahead_remote"
        remote_repo_path.mkdir()
        subprocess.run(
            ["git", "init", "--bare"],
            cwd=remote_repo_path,
            check=True,
            capture_output=True,
        )

        ahead_repo.mkdir()
        subprocess.run(["git", "init"], cwd=ahead_repo, check=True)
        subprocess.run(
            ["git", "remote", "add", "origin", str(remote_repo_path)],
            cwd=ahead_repo,
            check=True,
        )
        (ahead_repo / "feature.py").write_text("new feature")
        subprocess.run(["git", "add", "."], cwd=ahead_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "commit to remote"], cwd=ahead_repo, check=True
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "main"], cwd=ahead_repo, check=True
        )

        (ahead_repo / "another.py").write_text("local only")
        subprocess.run(["git", "add", "."], cwd=ahead_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "local only"], cwd=ahead_repo, check=True
        )

        return workspace

    def test_status_table_output_dirty_only(self, cli_runner, dirty_workspace):
        """Test default table output only shows dirty repos."""
        result = cli_runner.invoke(app, ["status", str(dirty_workspace)])

        assert result.exit_code == 0
        stdout = result.stdout

        assert "clean_repo" not in stdout
        assert "Modified" in stdout
        assert "Untracked" in stdout
        assert "Ahead" in stdout

    def test_status_table_output_show_all(self, cli_runner, dirty_workspace):
        """Test table output with --all flag shows clean repos."""
        result = cli_runner.invoke(app, ["status", str(dirty_workspace), "--all"])

        assert result.exit_code == 0
        stdout = result.stdout

        assert "Clean" in stdout
        assert "Modified" in stdout
        assert "Untracked" in stdout
        assert "Ahead" in stdout

    def test_status_json_output(self, cli_runner, dirty_workspace):
        """Test JSON output contains correct structured data."""
        result = cli_runner.invoke(
            app, ["status", str(dirty_workspace), "--output", "json", "--all"]
        )

        assert result.exit_code == 0

        # The progress bar is now sent to stderr, so we can directly parse the JSON from stdout
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
        result = cli_runner.invoke(
            app, ["status", str(dirty_workspace), "--fail-on-dirty"]
        )
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
        subprocess.run(
            ["git", "commit", "-m", "initial commit"], cwd=clean_repo, check=True
        )

        result = cli_runner.invoke(
            app, ["status", str(clean_workspace), "--fail-on-dirty"]
        )
        assert result.exit_code == 0

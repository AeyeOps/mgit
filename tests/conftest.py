"""
Shared pytest fixtures and configuration for mgit tests.

This module contains fixtures that are available to all tests in the test suite.
"""

import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import AsyncMock, MagicMock

import pytest
from typer.testing import CliRunner

# --- Pytest Configuration ---


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Set asyncio event loop scope
    config.option.asyncio_default_fixture_loop_scope = "function"


# --- Directory and File Fixtures ---


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for testing.

    Yields:
        Path: Path to the temporary directory.
    """
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_home_dir(temp_dir: Path, monkeypatch) -> Path:
    """
    Create a temporary home directory and set HOME environment variable.

    Args:
        temp_dir: The temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        Path: Path to the temporary home directory.
    """
    home_dir = temp_dir / "home"
    home_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))  # For Windows
    return home_dir


@pytest.fixture
def config_dir(temp_home_dir: Path) -> Path:
    """
    Create a temporary .mgit configuration directory.

    Args:
        temp_home_dir: The temporary home directory fixture.

    Returns:
        Path: Path to the .mgit directory.
    """
    mgit_dir = temp_home_dir / ".mgit"
    mgit_dir.mkdir(exist_ok=True)
    return mgit_dir


# --- Git Repository Fixtures ---


@pytest.fixture
def mock_git_repo(temp_dir: Path) -> Dict[str, Any]:
    """
    Create a mock git repository structure.

    Args:
        temp_dir: The temporary directory fixture.

    Returns:
        Dict containing repository information.
    """
    repo_path = temp_dir / "test_repo"
    repo_path.mkdir()

    # Create .git directory
    git_dir = repo_path / ".git"
    git_dir.mkdir()

    # Create some mock files
    (repo_path / "README.md").write_text("# Test Repository")
    (repo_path / "setup.py").write_text("# Setup file")

    # Create mock git config
    config_file = git_dir / "config"
    config_file.write_text(
        """[core]
    repositoryformatversion = 0
    filemode = true
[remote "origin"]
    url = https://dev.azure.com/test-org/_git/test-repo
    fetch = +refs/heads/*:refs/remotes/origin/*
"""
    )

    return {
        "path": repo_path,
        "git_dir": git_dir,
        "url": "https://dev.azure.com/test-org/_git/test-repo",
        "name": "test-repo",
    }


@pytest.fixture
def multiple_git_repos(temp_dir: Path) -> List[Dict[str, Any]]:
    """
    Create multiple mock git repositories.

    Args:
        temp_dir: The temporary directory fixture.

    Returns:
        List of dictionaries containing repository information.
    """
    repos = []
    for i in range(3):
        repo_path = temp_dir / f"repo_{i}"
        repo_path.mkdir()

        git_dir = repo_path / ".git"
        git_dir.mkdir()

        (repo_path / "README.md").write_text(f"# Repository {i}")

        repos.append(
            {
                "path": repo_path,
                "git_dir": git_dir,
                "url": f"https://dev.azure.com/test-org/_git/repo-{i}",
                "name": f"repo-{i}",
            }
        )

    return repos


# --- Azure DevOps API Mock Fixtures ---


@pytest.fixture
def mock_azure_client():
    """
    Create a mock Azure DevOps client.

    Returns:
        MagicMock: Mocked Azure DevOps client.
    """
    client = MagicMock()

    # Mock Git client
    git_client = MagicMock()
    client.get_git_client.return_value = git_client

    # Mock Core client
    core_client = MagicMock()
    client.get_core_client.return_value = core_client

    return client


@pytest.fixture
def mock_repositories():
    """
    Create mock repository objects.

    Returns:
        List of mock repository objects.
    """
    repos = []
    for i in range(3):
        repo = MagicMock()
        repo.id = f"repo-id-{i}"
        repo.name = f"repo-{i}"
        repo.remote_url = f"https://dev.azure.com/test-org/_git/repo-{i}"
        repo.default_branch = "refs/heads/main"
        repo.size = 1024 * (i + 1)
        repo.is_disabled = False
        repos.append(repo)

    return repos


@pytest.fixture
def mock_projects():
    """
    Create mock project objects.

    Returns:
        List of mock project objects.
    """
    projects = []
    for i in range(2):
        project = MagicMock()
        project.id = f"project-id-{i}"
        project.name = f"project-{i}"
        project.description = f"Test Project {i}"
        project.state = "wellFormed"
        projects.append(project)

    return projects


# --- CLI Testing Fixtures ---


@pytest.fixture
def cli_runner() -> CliRunner:
    """
    Create a Typer CLI test runner.

    Returns:
        CliRunner: Typer test runner instance.
    """
    return CliRunner()


@pytest.fixture
def isolated_cli_runner(temp_home_dir: Path) -> CliRunner:
    """
    Create an isolated CLI runner with temporary home directory.

    Args:
        temp_home_dir: The temporary home directory fixture.

    Returns:
        CliRunner: Isolated Typer test runner instance.
    """
    runner = CliRunner()
    # The temp_home_dir fixture already sets HOME env var
    return runner


# --- Configuration Fixtures ---


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """
    Create a sample configuration dictionary.

    Returns:
        Dict: Sample configuration data.
    """
    return {
        "azure_devops": {
            "organization": "https://dev.azure.com/test-org",
            "pat": "test-pat-token",
            "default_project": "test-project",
        },
        "git": {"default_branch": "main", "fetch_depth": 1},
        "concurrency": {"max_workers": 5, "timeout": 300},
    }


@pytest.fixture
def config_file(config_dir: Path, sample_config: Dict[str, Any]) -> Path:
    """
    Create a configuration file with sample data.

    Args:
        config_dir: The configuration directory fixture.
        sample_config: The sample configuration fixture.

    Returns:
        Path: Path to the configuration file.
    """
    config_path = config_dir / "config.json"
    config_path.write_text(json.dumps(sample_config, indent=2))
    return config_path


# --- Environment Variable Fixtures ---


@pytest.fixture
def clean_env(monkeypatch):
    """
    Clean environment variables that might affect tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    env_vars = [
        "AZURE_DEVOPS_EXT_PAT",
        "AZURE_DEVOPS_ORG",
        "AZURE_DEVOPS_PROJECT",
        "MGIT_CONFIG_PATH",
        "MGIT_CONCURRENCY",
    ]

    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def mock_env_vars(monkeypatch, clean_env):
    """
    Set up mock environment variables.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        clean_env: Clean environment fixture.
    """
    monkeypatch.setenv("AZURE_DEVOPS_EXT_PAT", "env-test-pat")
    monkeypatch.setenv("AZURE_DEVOPS_ORG", "https://dev.azure.com/env-test-org")
    monkeypatch.setenv("AZURE_DEVOPS_PROJECT", "env-test-project")


# --- Async Fixtures ---


@pytest.fixture
def event_loop():
    """
    Create an event loop for async tests.

    Yields:
        asyncio.AbstractEventLoop: The event loop.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_mock_subprocess():
    """
    Create a mock for asyncio.create_subprocess_exec.

    Returns:
        AsyncMock: Mocked subprocess.
    """
    process = AsyncMock()
    process.communicate = AsyncMock(return_value=(b"Success", b""))
    process.returncode = 0
    process.wait = AsyncMock(return_value=0)

    return process


# --- Utility Fixtures ---


@pytest.fixture
def capture_logs():
    """
    Fixture to capture log messages during tests.

    Yields:
        List: List to collect log records.
    """
    import logging

    logs = []

    class TestHandler(logging.Handler):
        def emit(self, record):
            logs.append(record)

    handler = TestHandler()
    logger = logging.getLogger("mgit")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    yield logs

    logger.removeHandler(handler)


@pytest.fixture
def mock_sleep(monkeypatch):
    """
    Mock time.sleep to speed up tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr("time.sleep", lambda x: None)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())


# --- Test Data Fixtures ---


@pytest.fixture
def test_urls():
    """
    Provide test URLs for various providers.

    Returns:
        Dict: Dictionary of test URLs by provider.
    """
    return {
        "azure": [
            "https://dev.azure.com/test-org/_git/repo1",
            "https://test-org@dev.azure.com/test-org/_git/repo2",
            "https://test-pat@dev.azure.com/test-org/_git/repo3",
        ],
        "github": [
            "https://github.com/test-org/repo1.git",
            "git@github.com:test-org/repo2.git",
            "https://token@github.com/test-org/repo3.git",
        ],
        "bitbucket": [
            "https://bitbucket.org/test-org/repo1.git",
            "git@bitbucket.org:test-org/repo2.git",
            "https://x-token-auth:token@bitbucket.org/test-org/repo3.git",
        ],
    }


# --- Performance Testing Fixtures ---


@pytest.fixture
def benchmark_timer():
    """
    Simple timer for basic performance testing.

    Yields:
        Dict: Dictionary to store timing results.
    """
    import time

    timings = {}

    class Timer:
        def __init__(self, name):
            self.name = name
            self.start_time = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, *args):
            elapsed = time.time() - self.start_time
            timings[self.name] = elapsed

    Timer.timings = timings
    yield Timer


# --- Marker Fixtures ---


@pytest.fixture(autouse=True)
def skip_slow_tests(request):
    """
    Automatically skip slow tests unless explicitly requested.

    Args:
        request: Pytest request fixture.
    """
    if request.node.get_closest_marker("slow"):
        if not request.config.getoption("--run-slow", default=False):
            pytest.skip("Skipping slow test (use --run-slow to run)")


def pytest_addoption(parser):
    """
    Add custom command line options.

    Args:
        parser: Pytest argument parser.
    """
    parser.addoption(
        "--run-slow", action="store_true", default=False, help="Run slow tests"
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests",
    )

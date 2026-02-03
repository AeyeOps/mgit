"""Gitea Docker fixtures for E2E collision resolution tests."""

import json as json_mod
import os
import subprocess
import time
import urllib.request
from base64 import b64encode
from pathlib import Path

import pytest

# --- Configuration Constants ---

GITEA_PORT = int(os.environ.get("GITEA_TEST_PORT", "3000"))
GITEA_URL = f"http://localhost:{GITEA_PORT}"
GITEA_ADMIN_USER = "admin"
GITEA_ADMIN_PASS = "admin123"
GITEA_ADMIN_EMAIL = "admin@test.local"


# --- API Helper Functions (stdlib only) ---


def _gitea_api(method: str, path: str, headers: dict, data: dict | None = None) -> dict:
    """Make a Gitea API request using urllib (stdlib)."""
    url = f"{GITEA_URL}/api/v1{path}"
    body = json_mod.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json_mod.loads(resp.read())


def create_gitea_token(username: str, password: str) -> str:
    """POST /api/v1/users/{username}/tokens with basic auth."""
    auth = b64encode(f"{username}:{password}".encode()).decode()
    result = _gitea_api(
        "POST",
        f"/users/{username}/tokens",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
        data={"name": f"test-token-{os.getpid()}"},
    )
    return result["sha1"]


def create_gitea_org(token: str, org_name: str) -> dict:
    """POST /api/v1/orgs"""
    return _gitea_api(
        "POST",
        "/orgs",
        headers={"Authorization": f"token {token}", "Content-Type": "application/json"},
        data={"username": org_name},
    )


def create_gitea_repo(token: str, org: str, repo_name: str) -> dict:
    """POST /api/v1/orgs/{org}/repos with auto_init=true."""
    return _gitea_api(
        "POST",
        f"/orgs/{org}/repos",
        headers={"Authorization": f"token {token}", "Content-Type": "application/json"},
        data={"name": repo_name, "auto_init": True},
    )


# --- Pytest Fixtures ---


@pytest.fixture(scope="session")
def gitea_container():
    """Start Gitea via docker-compose, wait for health, yield, cleanup."""
    compose_file = Path(__file__).parent / "docker-compose.gitea.yml"
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        check=True,
    )
    try:
        # Poll until Gitea is healthy
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"{GITEA_URL}/api/v1/version") as resp:
                    if resp.status == 200:
                        break
            except Exception:
                pass
            time.sleep(2)
        else:
            raise RuntimeError("Gitea failed to become healthy within 60s")
        yield
    finally:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down", "-v"],
            check=False,  # Don't fail cleanup if container already gone
        )


@pytest.fixture(scope="session")
def gitea_admin_token(gitea_container) -> str:
    """Create admin via CLI, return API token."""
    subprocess.run(
        [
            "docker", "exec", "gitea", "gitea", "admin", "user", "create",
            "--admin", "--username", GITEA_ADMIN_USER,
            "--password", GITEA_ADMIN_PASS,
            "--email", GITEA_ADMIN_EMAIL,
            "--must-change-password=false",
        ],
        check=True,
    )
    return create_gitea_token(GITEA_ADMIN_USER, GITEA_ADMIN_PASS)


@pytest.fixture
def gitea_mgit_env(gitea_admin_token, tmp_path) -> dict[str, str]:
    """Create isolated mgit config with Gitea provider, return env dict."""
    home = tmp_path / "home"
    home.mkdir()
    config_dir = home / ".config" / "mgit"
    config_dir.mkdir(parents=True)

    config_yaml = f"""\
providers:
  gitea_test:
    url: {GITEA_URL}/api/v1
    token: {gitea_admin_token}
    type: github
"""
    (config_dir / "config.yaml").write_text(config_yaml)

    return {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}


@pytest.fixture
def gitea_collision_repos(gitea_admin_token):
    """Create two orgs with same-named repos for collision testing."""
    create_gitea_org(gitea_admin_token, "test-org-a")
    create_gitea_org(gitea_admin_token, "test-org-b")
    create_gitea_repo(gitea_admin_token, "test-org-a", "common-repo")
    create_gitea_repo(gitea_admin_token, "test-org-b", "common-repo")
    yield


@pytest.fixture
def gitea_unique_repos(gitea_admin_token):
    """Create orgs with uniquely-named repos (no collision)."""
    create_gitea_org(gitea_admin_token, "unique-org-a")
    create_gitea_org(gitea_admin_token, "unique-org-b")
    create_gitea_repo(gitea_admin_token, "unique-org-a", "repo-one")
    create_gitea_repo(gitea_admin_token, "unique-org-b", "repo-two")
    yield

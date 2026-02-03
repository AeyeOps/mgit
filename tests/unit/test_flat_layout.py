"""Unit tests for flat layout feature in sync command."""

import pytest
from pathlib import Path

from mgit.git.utils import build_repo_path, extract_repo_name
from mgit.providers.base import Repository
from mgit.utils.collision_resolver import (
    detect_repo_name_collisions,
    resolve_collision_names,
    _simplify_host,
)


class TestBuildRepoPath:
    """Tests for build_repo_path function with flat parameter."""

    def test_hierarchical_mode_github(self):
        """Test hierarchical mode returns full path for GitHub URLs."""
        url = "https://github.com/myorg/my-repo"
        path = build_repo_path(url, flat=False)
        assert path == Path("github.com/myorg/repos/my-repo")

    def test_flat_mode_github(self):
        """Test flat mode returns just repo name for GitHub URLs."""
        url = "https://github.com/myorg/my-repo"
        path = build_repo_path(url, flat=True)
        assert path == Path("my-repo")

    def test_hierarchical_mode_azure_devops(self):
        """Test hierarchical mode returns full path for Azure DevOps URLs."""
        url = "https://dev.azure.com/myorg/myproject/_git/myrepo"
        path = build_repo_path(url, flat=False)
        assert path == Path("dev.azure.com/myorg/myproject/myrepo")

    def test_flat_mode_azure_devops(self):
        """Test flat mode returns just repo name for Azure DevOps URLs."""
        url = "https://dev.azure.com/myorg/myproject/_git/myrepo"
        path = build_repo_path(url, flat=True)
        assert path == Path("myrepo")

    def test_hierarchical_mode_bitbucket(self):
        """Test hierarchical mode returns full path for BitBucket URLs."""
        url = "https://bitbucket.org/myworkspace/my-repo"
        path = build_repo_path(url, flat=False)
        assert path == Path("bitbucket.org/myworkspace/repos/my-repo")

    def test_flat_mode_bitbucket(self):
        """Test flat mode returns just repo name for BitBucket URLs."""
        url = "https://bitbucket.org/myworkspace/my-repo"
        path = build_repo_path(url, flat=True)
        assert path == Path("my-repo")

    def test_default_is_hierarchical(self):
        """Test default behavior is hierarchical mode."""
        url = "https://github.com/myorg/my-repo"
        path = build_repo_path(url)  # No flat parameter
        assert len(path.parts) == 4  # host/org/project/repo

    def test_flat_mode_sanitizes_special_chars(self):
        """Test that special chars are sanitized in flat mode."""
        url = "https://github.com/myorg/my<repo>name"
        path = build_repo_path(url, flat=True)
        # < and > should be removed
        assert "<" not in str(path)
        assert ">" not in str(path)
        assert str(path) == "myreponame"


class TestExtractRepoName:
    """Tests for extract_repo_name convenience function."""

    def test_extracts_github_repo_name(self):
        """Test extracting repo name from GitHub URL."""
        url = "https://github.com/myorg/my-repo"
        name = extract_repo_name(url)
        assert name == "my-repo"

    def test_extracts_azure_devops_repo_name(self):
        """Test extracting repo name from Azure DevOps URL."""
        url = "https://dev.azure.com/myorg/myproject/_git/my-repo"
        name = extract_repo_name(url)
        assert name == "my-repo"

    def test_handles_git_suffix(self):
        """Test that .git suffix is removed from repo name."""
        url = "https://github.com/myorg/my-repo.git"
        name = extract_repo_name(url)
        assert name == "my-repo"


class TestCollisionDetection:
    """Tests for collision detection functions."""

    def test_no_collisions(self):
        """Test detection with no collisions."""
        repos = [
            Repository(name="repo-a", clone_url="https://github.com/org1/repo-a", is_disabled=False),
            Repository(name="repo-b", clone_url="https://github.com/org1/repo-b", is_disabled=False),
            Repository(name="repo-c", clone_url="https://github.com/org2/repo-c", is_disabled=False),
        ]
        groups = detect_repo_name_collisions(repos)
        # Each repo should be in its own group
        assert all(len(repos) == 1 for repos in groups.values())

    def test_detects_same_name_collision(self):
        """Test detection of repos with same name from different orgs."""
        repos = [
            Repository(name="auth", clone_url="https://github.com/org-a/auth", is_disabled=False),
            Repository(name="auth", clone_url="https://github.com/org-b/auth", is_disabled=False),
        ]
        groups = detect_repo_name_collisions(repos)
        assert "auth" in groups
        assert len(groups["auth"]) == 2

    def test_detects_multiple_collisions(self):
        """Test detection of multiple collision groups."""
        repos = [
            Repository(name="auth", clone_url="https://github.com/org-a/auth", is_disabled=False),
            Repository(name="auth", clone_url="https://github.com/org-b/auth", is_disabled=False),
            Repository(name="api", clone_url="https://github.com/org-a/api", is_disabled=False),
            Repository(name="api", clone_url="https://github.com/org-b/api", is_disabled=False),
            Repository(name="unique", clone_url="https://github.com/org-a/unique", is_disabled=False),
        ]
        groups = detect_repo_name_collisions(repos)
        assert len(groups["auth"]) == 2
        assert len(groups["api"]) == 2
        assert len(groups["unique"]) == 1


class TestCollisionResolution:
    """Tests for collision resolution functions."""

    def test_unique_names_unchanged(self):
        """Test that unique repo names are not modified."""
        repos = [
            Repository(name="repo-a", clone_url="https://github.com/org1/repo-a", is_disabled=False),
            Repository(name="repo-b", clone_url="https://github.com/org1/repo-b", is_disabled=False),
        ]
        resolved = resolve_collision_names(repos)
        assert resolved["https://github.com/org1/repo-a"] == "repo-a"
        assert resolved["https://github.com/org1/repo-b"] == "repo-b"

    def test_colliding_names_get_org_suffix(self):
        """Test that colliding repos get org name as suffix."""
        repos = [
            Repository(name="auth", clone_url="https://github.com/org-a/auth", is_disabled=False),
            Repository(name="auth", clone_url="https://github.com/org-b/auth", is_disabled=False),
        ]
        resolved = resolve_collision_names(repos)
        assert resolved["https://github.com/org-a/auth"] == "auth_org-a"
        assert resolved["https://github.com/org-b/auth"] == "auth_org-b"

    def test_empty_repos_list(self):
        """Test resolution with empty list."""
        resolved = resolve_collision_names([])
        assert resolved == {}

    def test_single_repo(self):
        """Test resolution with single repo."""
        repos = [
            Repository(name="single", clone_url="https://github.com/org/single", is_disabled=False),
        ]
        resolved = resolve_collision_names(repos)
        assert resolved["https://github.com/org/single"] == "single"

    def test_cross_provider_collision(self):
        """Test resolution of collisions across providers."""
        repos = [
            Repository(name="auth", clone_url="https://github.com/myorg/auth", is_disabled=False),
            Repository(name="auth", clone_url="https://dev.azure.com/myorg/proj/_git/auth", is_disabled=False),
        ]
        resolved = resolve_collision_names(repos)
        # Both have 'myorg' so should get provider prefix
        github_name = resolved["https://github.com/myorg/auth"]
        azure_name = resolved["https://dev.azure.com/myorg/proj/_git/auth"]
        # Names should be different
        assert github_name != azure_name
        # Both should contain 'auth'
        assert "auth" in github_name
        assert "auth" in azure_name


class TestSimplifyHost:
    """Tests for host simplification function."""

    def test_github(self):
        """Test GitHub host simplification."""
        assert _simplify_host("github.com") == "github"
        assert _simplify_host("GITHUB.COM") == "github"

    def test_azure_devops(self):
        """Test Azure DevOps host simplification."""
        assert _simplify_host("dev.azure.com") == "azure"
        assert _simplify_host("myorg.visualstudio.com") == "azure"

    def test_bitbucket(self):
        """Test BitBucket host simplification."""
        assert _simplify_host("bitbucket.org") == "bitbucket"

    def test_gitlab(self):
        """Test GitLab host simplification."""
        assert _simplify_host("gitlab.com") == "gitlab"
        assert _simplify_host("gitlab.example.com") == "gitlab"

    def test_unknown_host(self):
        """Test unknown host returns first segment."""
        assert _simplify_host("custom.git.example.com") == "custom"


@pytest.mark.unit
class TestIntegration:
    """Integration tests for flat layout with collision resolution."""

    def test_full_workflow(self):
        """Test complete workflow from repos to resolved names."""
        repos = [
            Repository(name="auth-service", clone_url="https://github.com/org-a/auth-service", is_disabled=False),
            Repository(name="auth-service", clone_url="https://github.com/org-b/auth-service", is_disabled=False),
            Repository(name="api-gateway", clone_url="https://github.com/org-a/api-gateway", is_disabled=False),
            Repository(name="web-app", clone_url="https://dev.azure.com/org-a/proj/_git/web-app", is_disabled=False),
        ]

        # Detect collisions
        groups = detect_repo_name_collisions(repos)
        collisions = {name: rs for name, rs in groups.items() if len(rs) > 1}
        assert len(collisions) == 1  # Only auth-service collides

        # Resolve names
        resolved = resolve_collision_names(repos)

        # Verify all repos have resolved names
        assert len(resolved) == 4

        # Verify collision resolution
        assert resolved["https://github.com/org-a/auth-service"] == "auth-service_org-a"
        assert resolved["https://github.com/org-b/auth-service"] == "auth-service_org-b"

        # Verify non-colliding repos keep original names
        assert resolved["https://github.com/org-a/api-gateway"] == "api-gateway"
        assert resolved["https://dev.azure.com/org-a/proj/_git/web-app"] == "web-app"

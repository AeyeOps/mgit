"""Regression tests for GitHub-backed repository listing."""

from collections.abc import AsyncIterator

import pytest

from mgit.commands import listing
from mgit.providers.base import Repository


class _FakeGitHubProvider:
    PROVIDER_NAME = "github"

    async def authenticate(self) -> bool:
        return True

    async def list_organizations(self):
        # Simulate the reported failure mode: organization discovery sees only
        # one owner even though the token can read repositories from another.
        return []

    async def list_repositories(
        self, organization: str, project: str | None = None, filters=None
    ) -> AsyncIterator[Repository]:
        if False:
            yield

    async def list_accessible_repositories(
        self, filters=None
    ) -> AsyncIterator[Repository]:
        yield Repository(
            name="visible-repo",
            clone_url="https://github.com/visible-org/visible-repo.git",
            organization="visible-org",
            provider="github",
        )
        yield Repository(
            name="hidden-repo",
            clone_url="https://github.com/hidden-org/hidden-repo.git",
            organization="hidden-org",
            provider="github",
        )

    def supports_projects(self) -> bool:
        return False

    async def cleanup(self) -> None:
        return None


class _FakeProviderManager:
    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def get_provider(self):
        return _FakeGitHubProvider()


@pytest.mark.asyncio
async def test_github_wildcard_list_uses_authenticated_repo_inventory(
    monkeypatch,
):
    """Wildcard GitHub listing must include all repos the token can access."""
    monkeypatch.setattr(listing, "ProviderManager", _FakeProviderManager)

    results = await listing._process_single_provider("github_mm", "*/*/*")

    assert [result.full_path for result in results] == [
        "visible-org/visible-repo",
        "hidden-org/hidden-repo",
    ]

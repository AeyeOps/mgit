"""
Repository discovery integration for change detection.

Combines the provider system with change detection to enable tracking
changes across multiple repositories discovered through query patterns.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set, Any, Tuple
from dataclasses import dataclass

from mgit.providers.base import Repository
from mgit.commands.listing import list_repositories
from mgit.changesets.models import RepositoryChangeset
from mgit.config.yaml_manager import list_provider_names

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredRepositoryChange:
    """Represents changes in a repository discovered through provider queries."""

    repository: Repository
    local_path: Optional[Path]  # Local clone path if exists
    changeset: Optional[RepositoryChangeset]  # Change information if locally available
    provider_name: str
    discovery_query: str
    error: Optional[str] = None


@dataclass
class ChangeDiscoveryResult:
    """Result of change discovery across providers and repositories."""

    discovered_repositories: List[DiscoveredRepositoryChange]
    successful_providers: List[str]
    failed_providers: List[str]
    local_repositories_found: int
    remote_only_repositories: int
    total_repositories_with_changes: int
    query_pattern: str

    @property
    def success_rate(self) -> float:
        """Calculate provider success rate."""
        total_providers = len(self.successful_providers) + len(self.failed_providers)
        return (
            len(self.successful_providers) / total_providers
            if total_providers > 0
            else 0.0
        )


class ChangeDiscoveryEngine:
    """
    Engine for discovering repositories and their changes across providers.

    Combines repository discovery through provider APIs with local change detection
    to provide comprehensive view of repository states across multiple providers.
    """

    def __init__(self, local_scan_root: Optional[Path] = None, concurrency: int = 10):
        """
        Initialize change discovery engine.

        Args:
            local_scan_root: Root directory to scan for local repository clones
            concurrency: Number of concurrent operations for change detection
        """
        self.local_scan_root = local_scan_root
        self.concurrency = concurrency
        # Use delayed import to avoid circular dependency
        from mgit.processing import DiffProcessor

        self.diff_processor = DiffProcessor(concurrency=concurrency)

    async def discover_repository_changes(
        self,
        query_pattern: str,
        provider_name: Optional[str] = None,
        provider_url: Optional[str] = None,
        local_scan_only: bool = False,
        include_remote_only: bool = True,
        limit: Optional[int] = None,
    ) -> ChangeDiscoveryResult:
        """
        Discover repositories matching pattern and detect their changes.

        Args:
            query_pattern: Repository pattern to search for (e.g., "org/*/*")
            provider_name: Specific provider to query (None for all)
            provider_url: Provider URL for single provider discovery
            local_scan_only: Only check locally cloned repositories
            include_remote_only: Include repositories found remotely but not locally
            limit: Maximum number of repositories to process

        Returns:
            ChangeDiscoveryResult with discovered repositories and change information
        """
        try:
            logger.info(f"Starting change discovery for pattern: {query_pattern}")

            if local_scan_only:
                return await self._discover_local_only(query_pattern, limit)

            # Discover repositories through provider system
            discovered_repos = await self._discover_repositories_via_providers(
                query_pattern, provider_name, provider_url, limit
            )

            if not discovered_repos:
                logger.warning(
                    f"No repositories discovered for pattern: {query_pattern}"
                )
                return ChangeDiscoveryResult(
                    discovered_repositories=[],
                    successful_providers=[],
                    failed_providers=[],
                    local_repositories_found=0,
                    remote_only_repositories=0,
                    total_repositories_with_changes=0,
                    query_pattern=query_pattern,
                )

            # Map repositories to local paths and detect changes
            result_repos = await self._process_discovered_repositories(
                discovered_repos, include_remote_only, query_pattern
            )

            # Aggregate results
            successful_providers = list(
                set(r.provider_name for r in result_repos if r.error is None)
            )
            failed_providers = list(
                set(r.provider_name for r in result_repos if r.error is not None)
            )

            local_count = sum(1 for r in result_repos if r.local_path is not None)
            remote_only_count = sum(1 for r in result_repos if r.local_path is None)
            changes_count = sum(
                1
                for r in result_repos
                if r.changeset and r.changeset.has_uncommitted_changes
            )

            logger.info(
                f"Change discovery completed: {len(result_repos)} repositories, "
                f"{local_count} local, {remote_only_count} remote-only, "
                f"{changes_count} with changes"
            )

            return ChangeDiscoveryResult(
                discovered_repositories=result_repos,
                successful_providers=successful_providers,
                failed_providers=failed_providers,
                local_repositories_found=local_count,
                remote_only_repositories=remote_only_count,
                total_repositories_with_changes=changes_count,
                query_pattern=query_pattern,
            )

        except Exception as e:
            logger.error(f"Change discovery failed: {e}")
            return ChangeDiscoveryResult(
                discovered_repositories=[],
                successful_providers=[],
                failed_providers=[],
                local_repositories_found=0,
                remote_only_repositories=0,
                total_repositories_with_changes=0,
                query_pattern=query_pattern,
            )

    async def _discover_repositories_via_providers(
        self,
        query_pattern: str,
        provider_name: Optional[str],
        provider_url: Optional[str],
        limit: Optional[int],
    ) -> List[Tuple[Repository, str]]:
        """
        Discover repositories through provider system.

        Returns:
            List of (Repository, provider_name) tuples
        """
        discovered_repos = []

        if provider_name:
            # Single provider discovery
            try:
                logger.debug(
                    f"Querying provider '{provider_name}' for pattern: {query_pattern}"
                )

                repository_results = await list_repositories(
                    query=query_pattern,
                    provider_name=provider_name,
                    format_type="json",
                    limit=limit,
                )

                if repository_results:
                    for result in repository_results:
                        discovered_repos.append((result.repo, provider_name))

                    logger.debug(
                        f"Provider '{provider_name}' returned {len(repository_results)} repositories"
                    )

            except Exception as e:
                logger.error(f"Provider '{provider_name}' query failed: {e}")

        else:
            # Multi-provider discovery
            providers = list_provider_names()
            logger.debug(
                f"Querying {len(providers)} providers for pattern: {query_pattern}"
            )

            # Query providers concurrently
            tasks = []
            for prov_name in providers:
                task = self._query_single_provider(query_pattern, prov_name, limit)
                tasks.append(task)

            provider_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Aggregate results
            for i, result in enumerate(provider_results):
                prov_name = providers[i]

                if isinstance(result, Exception):
                    logger.debug(f"Provider '{prov_name}' failed: {result}")
                elif isinstance(result, list):
                    for repo in result:
                        discovered_repos.append((repo, prov_name))
                    logger.debug(
                        f"Provider '{prov_name}' returned {len(result)} repositories"
                    )

        logger.info(
            f"Discovered {len(discovered_repos)} repositories across all providers"
        )
        return discovered_repos

    async def _query_single_provider(
        self, query_pattern: str, provider_name: str, limit: Optional[int]
    ) -> List[Repository]:
        """Query a single provider for repositories."""
        try:
            repository_results = await list_repositories(
                query=query_pattern,
                provider_name=provider_name,
                format_type="json",
                limit=limit,
            )

            return [result.repo for result in (repository_results or [])]

        except Exception as e:
            logger.debug(f"Provider '{provider_name}' query failed: {e}")
            raise

    async def _process_discovered_repositories(
        self,
        discovered_repos: List[Tuple[Repository, str]],
        include_remote_only: bool,
        query_pattern: str,
    ) -> List[DiscoveredRepositoryChange]:
        """Process discovered repositories to detect local changes."""
        result_repos = []

        # Create tasks for concurrent processing
        semaphore = asyncio.Semaphore(self.concurrency)

        async def process_single_repo(
            repo_info: Tuple[Repository, str]
        ) -> DiscoveredRepositoryChange:
            async with semaphore:
                repository, provider_name = repo_info

                try:
                    # Check if repository exists locally
                    local_path = self._find_local_repository_path(repository)

                    changeset = None
                    if local_path and local_path.exists():
                        # Repository exists locally - detect changes
                        logger.debug(
                            f"Detecting changes in local repository: {local_path}"
                        )
                        changeset = (
                            await self.diff_processor._detect_repository_changes(
                                local_path
                            )
                        )
                    elif not include_remote_only:
                        # Skip remote-only repositories if not requested
                        return None

                    return DiscoveredRepositoryChange(
                        repository=repository,
                        local_path=local_path,
                        changeset=changeset,
                        provider_name=provider_name,
                        discovery_query=query_pattern,
                        error=None,
                    )

                except Exception as e:
                    logger.debug(f"Failed to process repository {repository.name}: {e}")
                    return DiscoveredRepositoryChange(
                        repository=repository,
                        local_path=None,
                        changeset=None,
                        provider_name=provider_name,
                        discovery_query=query_pattern,
                        error=str(e),
                    )

        # Process repositories concurrently
        tasks = [process_single_repo(repo_info) for repo_info in discovered_repos]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results and exceptions
        for result in results:
            if isinstance(result, Exception):
                logger.debug(f"Repository processing failed: {result}")
            elif result is not None:
                result_repos.append(result)

        return result_repos

    async def _discover_local_only(
        self, query_pattern: str, limit: Optional[int]
    ) -> ChangeDiscoveryResult:
        """Discover repositories by scanning local filesystem only."""
        if not self.local_scan_root:
            logger.error("Local scan requested but no local_scan_root configured")
            return ChangeDiscoveryResult(
                discovered_repositories=[],
                successful_providers=[],
                failed_providers=[],
                local_repositories_found=0,
                remote_only_repositories=0,
                total_repositories_with_changes=0,
                query_pattern=query_pattern,
            )

        try:
            from mgit.utils.directory_scanner import find_repositories_in_directory

            # Find local repositories
            local_repos = find_repositories_in_directory(
                self.local_scan_root, recursive=True
            )

            if limit and len(local_repos) > limit:
                local_repos = local_repos[:limit]

            # Process local repositories for changes
            changesets = await self.diff_processor.process_repositories(local_repos)

            # Convert to DiscoveredRepositoryChange format
            result_repos = []
            for i, local_path in enumerate(local_repos):
                changeset = changesets[i] if i < len(changesets) else None

                # Create minimal repository info for local-only mode
                dummy_repo = Repository(
                    name=local_path.name,
                    clone_url=f"file://{local_path}",
                    organization="local",
                    project="",
                )

                result_repos.append(
                    DiscoveredRepositoryChange(
                        repository=dummy_repo,
                        local_path=local_path,
                        changeset=changeset,
                        provider_name="local",
                        discovery_query=query_pattern,
                        error=None,
                    )
                )

            changes_count = sum(
                1
                for r in result_repos
                if r.changeset and r.changeset.has_uncommitted_changes
            )

            return ChangeDiscoveryResult(
                discovered_repositories=result_repos,
                successful_providers=["local"],
                failed_providers=[],
                local_repositories_found=len(result_repos),
                remote_only_repositories=0,
                total_repositories_with_changes=changes_count,
                query_pattern=query_pattern,
            )

        except Exception as e:
            logger.error(f"Local discovery failed: {e}")
            return ChangeDiscoveryResult(
                discovered_repositories=[],
                successful_providers=[],
                failed_providers=["local"],
                local_repositories_found=0,
                remote_only_repositories=0,
                total_repositories_with_changes=0,
                query_pattern=query_pattern,
            )

    def _find_local_repository_path(self, repository: Repository) -> Optional[Path]:
        """
        Find local path for a remote repository.

        Uses heuristics to find likely local clone locations based on
        repository organization, name, and common clone patterns.
        """
        if not self.local_scan_root:
            return None

        # Common clone path patterns to check
        potential_paths = [
            # Direct organization/repository structure
            self.local_scan_root / repository.organization / repository.name,
            # Flat repository name structure
            self.local_scan_root / repository.name,
            # Project-based structure (for Azure DevOps)
            self.local_scan_root
            / repository.organization
            / (repository.project or "default")
            / repository.name,
            # Provider-specific structures
            self.local_scan_root / "github" / repository.organization / repository.name,
            self.local_scan_root / "azure" / repository.organization / repository.name,
            self.local_scan_root
            / "bitbucket"
            / repository.organization
            / repository.name,
        ]

        # Check each potential path
        for path in potential_paths:
            if path.exists() and (path / ".git").exists():
                logger.debug(f"Found local repository at: {path}")
                return path

        return None


# Convenience functions for common use cases
async def discover_changes_by_pattern(
    pattern: str,
    local_root: Optional[Path] = None,
    provider: Optional[str] = None,
    limit: Optional[int] = None,
) -> ChangeDiscoveryResult:
    """
    Convenience function for discovering repository changes by pattern.

    Args:
        pattern: Repository search pattern (e.g., "myorg/*/*")
        local_root: Root directory to scan for local clones
        provider: Specific provider to query (None for all providers)
        limit: Maximum repositories to process

    Returns:
        ChangeDiscoveryResult with discovered changes
    """
    engine = ChangeDiscoveryEngine(local_scan_root=local_root)
    return await engine.discover_repository_changes(
        query_pattern=pattern, provider_name=provider, limit=limit
    )


async def discover_local_changes_only(
    local_root: Path, pattern: str = "*/*/*", limit: Optional[int] = None
) -> ChangeDiscoveryResult:
    """
    Convenience function for local-only change discovery.

    Args:
        local_root: Root directory to scan for repositories
        pattern: Pattern for filtering repository names
        limit: Maximum repositories to process

    Returns:
        ChangeDiscoveryResult with local repository changes
    """
    engine = ChangeDiscoveryEngine(local_scan_root=local_root)
    return await engine.discover_repository_changes(
        query_pattern=pattern, local_scan_only=True, limit=limit
    )

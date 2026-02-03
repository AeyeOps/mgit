"""Multi-provider repository resolution logic.

Extracted from __main__.py to consolidate the repository discovery logic
used by both clone_all and pull_all commands.
"""

import asyncio
import concurrent.futures
import logging
from dataclasses import dataclass
from urllib.parse import urlparse

from ..commands.listing import RepositoryResult, list_repositories
from ..config.yaml_manager import list_provider_names
from ..providers.base import Repository

logger = logging.getLogger(__name__)


@dataclass
class MultiProviderResult:
    """Result container for multi-provider repository resolution."""

    repositories: list[Repository]
    successful_providers: list[str]
    failed_providers: list[str]
    total_found: int
    duplicates_removed: int


class MultiProviderResolver:
    """Handles repository resolution across single or multiple providers."""

    def __init__(self, concurrency_limit: int = 5):
        """Initialize resolver with concurrency control.

        Args:
            concurrency_limit: Maximum concurrent provider queries
        """
        self.concurrency_limit = concurrency_limit
        self._semaphore = asyncio.Semaphore(concurrency_limit)

    def _detect_multi_provider_pattern(
        self, project: str, config: str | None = None, url: str | None = None
    ) -> bool:
        """Detect if this should use multi-provider resolution.

        Args:
            project: Query pattern
            config: Provider config name (if specified)
            url: Provider URL (if specified)

        Returns:
            True if should query multiple providers
        """
        return config is None and url is None and ("*" in project or "?" in project)

    def _has_pattern(self, project: str) -> bool:
        """Check if project contains wildcard patterns."""
        return "*" in project or "?" in project

    async def _query_single_provider(
        self, provider_name: str, project: str
    ) -> list[RepositoryResult]:
        """Query a single provider for repositories.

        Args:
            provider_name: Name of provider to query
            project: Query pattern

        Returns:
            List of repository results from this provider
        """
        try:
            logger.debug(f"Querying provider '{provider_name}' for pattern '{project}'")
            # Use asyncio.run to match the pattern from __main__.py since list_repositories is async
            results = await list_repositories(
                query=project,
                provider_name=provider_name,
                format_type="json",
                limit=None,
            )
            return results or []
        except Exception as e:
            logger.error(f"Provider '{provider_name}' listing failed: {e}")
            return []

    def _deduplicate_repositories(
        self, all_results: list[RepositoryResult]
    ) -> tuple[list[Repository], int]:
        """Deduplicate repositories by URL, then by org/name.

        Args:
            all_results: All repository results from all providers

        Returns:
            Tuple of (deduplicated repositories, duplicates_removed_count)
        """
        seen_urls = set()
        seen_org_names = set()
        deduplicated = []
        duplicates_removed = 0

        for result in all_results:
            repo = result.repo

            # Primary deduplication by clone URL
            if repo.clone_url in seen_urls:
                duplicates_removed += 1
                continue

            # Secondary deduplication by host/org/name combination
            # Include host to allow same org/name on different providers (hybrid setups)
            host = urlparse(repo.clone_url).hostname or "unknown"
            org_name_key = f"{host}/{result.org_name}/{repo.name}"
            if org_name_key in seen_org_names:
                duplicates_removed += 1
                continue

            # Add to deduplicated list
            seen_urls.add(repo.clone_url)
            seen_org_names.add(org_name_key)
            deduplicated.append(repo)

        return deduplicated, duplicates_removed

    async def resolve_repositories(
        self,
        project: str,
        provider_manager=None,
        config: str | None = None,
        url: str | None = None,
    ) -> MultiProviderResult:
        """Resolve repositories using appropriate strategy.

        Args:
            project: Query pattern
            provider_manager: Single provider manager (if available)
            config: Provider config name (if specified)
            url: Provider URL (if specified)

        Returns:
            MultiProviderResult with repositories and metadata
        """
        is_multi_provider = self._detect_multi_provider_pattern(project, config, url)
        has_pattern = self._has_pattern(project)

        if is_multi_provider:
            # Multi-provider mode: query all configured providers
            logger.debug(f"Using multi-provider discovery for pattern '{project}'")
            return await self._resolve_multi_provider(project)

        elif has_pattern:
            # Single provider with pattern: use list_repositories
            if provider_manager is None:
                raise ValueError(
                    "Provider manager required for single-provider pattern queries"
                )

            logger.debug(f"Using single-provider pattern query for '{project}'")
            return await self._resolve_single_provider_pattern(
                project, provider_manager.provider_name
            )
        else:
            # Direct single provider mode: use provider.list_repositories directly
            if provider_manager is None:
                raise ValueError("Provider manager required for direct queries")

            logger.debug(f"Using direct provider query for '{project}'")
            return await self._resolve_single_provider_direct(project, provider_manager)

    async def _resolve_multi_provider(self, project: str) -> MultiProviderResult:
        """Resolve repositories across all configured providers."""
        providers = list_provider_names()
        if not providers:
            logger.warning("No providers configured for multi-provider query")
            return MultiProviderResult(
                repositories=[],
                successful_providers=[],
                failed_providers=[],
                total_found=0,
                duplicates_removed=0,
            )

        # Use the same approach as the original code - call list_repositories with provider_name=None
        # This delegates to the list command's multi-provider logic
        try:
            logger.debug(f"Using multi-provider discovery for pattern '{project}'")
            results = await list_repositories(
                query=project,
                provider_name=None,  # This triggers multi-provider mode in list_repositories
                format_type="json",
                limit=None,
            )

            # Extract repositories from results and deduplicate
            all_repositories = results or []
            logger.debug(
                f"Multi-provider query returned {len(all_repositories)} raw results"
            )
            deduplicated_repos, duplicates_removed = self._deduplicate_repositories(
                all_repositories
            )
            logger.debug(
                f"After deduplication: {len(deduplicated_repos)} repos, {duplicates_removed} duplicates removed"
            )

            logger.info(
                f"Found {len(deduplicated_repos)} unique repositories "
                f"({len(all_repositories)} total, {duplicates_removed} duplicates removed) "
                f"across multiple providers using pattern '{project}'"
            )

            return MultiProviderResult(
                repositories=deduplicated_repos,  # Already extracted .repo in deduplication
                successful_providers=providers,  # Assume all providers were successful
                failed_providers=[],
                total_found=len(all_repositories),
                duplicates_removed=duplicates_removed,
            )
        except Exception as e:
            logger.error(f"Multi-provider query failed: {e}")
            return MultiProviderResult(
                repositories=[],
                successful_providers=[],
                failed_providers=providers,
                total_found=0,
                duplicates_removed=0,
            )

    async def _resolve_single_provider_pattern(
        self, project: str, provider_name: str
    ) -> MultiProviderResult:
        """Resolve repositories using single provider with pattern."""
        results = await self._query_single_provider(provider_name, project)
        repositories = [r.repo for r in results]

        logger.info(
            f"Found {len(repositories)} repositories in provider '{provider_name}' "
            f"using pattern '{project}'"
        )

        return MultiProviderResult(
            repositories=repositories,
            successful_providers=[provider_name],
            failed_providers=[],
            total_found=len(repositories),
            duplicates_removed=0,
        )

    async def _resolve_single_provider_direct(
        self, project: str, provider_manager
    ) -> MultiProviderResult:
        """Resolve repositories using direct provider query."""
        # Use the _ensure_repo_list pattern from original code
        repositories = self._ensure_repo_list(
            provider_manager.list_repositories(project)
        )

        logger.info(f"Found {len(repositories)} repositories in project '{project}'")

        return MultiProviderResult(
            repositories=repositories,
            successful_providers=[provider_manager.provider_name],
            failed_providers=[],
            total_found=len(repositories),
            duplicates_removed=0,
        )

    def _ensure_repo_list(self, repos):
        """Convert async iterable or other repo formats to list.

        This replicates the _ensure_repo_list function from __main__.py
        """
        try:
            if isinstance(repos, list):
                return repos
            # Async iterable
            if hasattr(repos, "__aiter__"):
                # Collect in separate function to avoid coroutine leakage
                def collect_sync():
                    async def collect_async(ait):
                        return [item async for item in ait]

                    return asyncio.run(collect_async(repos))

                try:
                    return collect_sync()
                except RuntimeError:
                    # Already in async context, run in separate thread
                    with concurrent.futures.ThreadPoolExecutor() as ex:
                        future_result = ex.submit(collect_sync)
                        return future_result.result()
            # Sync iterable fallback
            return list(repos)
        except Exception as e:
            logger.error(f"Failed to convert repository list: {e}")
            return []

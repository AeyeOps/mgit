"""Listing command implementation for mgit.

Provides repository discovery across providers using query patterns.
"""

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from ..config.yaml_manager import list_provider_names
from ..exceptions import MgitError
from ..providers.base import Repository
from ..providers.exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
)
from ..providers.exceptions import (
    ConnectionError as ProviderConnectionError,
)
from ..providers.manager import ProviderManager
from ..ui.progress import create_progress
from ..utils.query_parser import matches_pattern, parse_query, validate_query

logger = logging.getLogger(__name__)
console = Console()

# Errors that mean a provider produced NOTHING because it broke, not because it
# legitimately has no matching repositories. These must fail loud rather than
# present as "0 repositories".
FATAL_PROVIDER_ERRORS = (
    APIError,
    AuthenticationError,
    ConfigurationError,
    ProviderConnectionError,
    RateLimitError,
)


class RepositoryResult:
    """Container for repository search results."""

    def __init__(
        self, repo: Repository, org_name: str, project_name: str | None = None
    ):
        self.repo = repo
        self.org_name = org_name
        self.project_name = project_name

    @property
    def full_path(self) -> str:
        """Get full path string for display."""
        if self.project_name:
            return f"{self.org_name}/{self.project_name}/{self.repo.name}"
        else:
            return f"{self.org_name}/{self.repo.name}"


@dataclass
class ProviderOutcome:
    """Whether one provider's query succeeded, for honest reporting."""

    provider: str
    ok: bool
    error: str | None = None


@dataclass
class ListingResult:
    """Repository results plus the per-provider outcomes that produced them.

    A provider that errored contributes no results; its failure is recorded
    here instead of silently shrinking the result set.
    """

    results: list[RepositoryResult] = field(default_factory=list)
    provider_outcomes: list[ProviderOutcome] = field(default_factory=list)

    @property
    def successful_providers(self) -> list[str]:
        return [o.provider for o in self.provider_outcomes if o.ok]

    @property
    def failed_providers(self) -> list[str]:
        return [o.provider for o in self.provider_outcomes if not o.ok]


async def _process_single_provider(
    provider_name: str,
    query: str,
    limit: int | None = None,
    progress: Progress | None = None,
    provider_task_id: int | None = None,
) -> list[RepositoryResult]:
    """Process a single provider for repository discovery.

    Args:
        provider_name: Name of the provider to process
        query: Query pattern (org/project/repo)
        limit: Maximum number of results to return
        progress: Progress object for updates
        provider_task_id: Task ID for provider-level progress updates

    Returns:
        List of matching repository results from this provider
    """
    # Parse query pattern
    pattern = parse_query(query)

    # Get provider
    provider_manager = ProviderManager(provider_name=provider_name)
    provider = provider_manager.get_provider()
    if not provider:
        logger.warning(f"Could not initialize provider: {provider_name}")
        return []

    # Authenticate provider. A failure here propagates so the caller records
    # the outcome instead of silently reporting "0 repositories".
    if not await provider.authenticate():
        raise AuthenticationError(
            f"Failed to authenticate with provider: {provider_name}",
            provider=provider_name,
        )

    logger.debug(f"Using provider: {provider.PROVIDER_NAME}")

    results = []
    errors: list[Exception] = []
    seen_repositories: set[tuple[str | None, str | None, str]] = set()

    def add_result(
        repo: Repository, org_name: str, project_name: str | None = None
    ) -> bool:
        """Add a repository result if it has not already been discovered."""
        repo_key = (
            repo.clone_url,
            repo.metadata.get("full_name"),
            f"{org_name}/{repo.name}",
        )
        if repo_key in seen_repositories:
            return False

        seen_repositories.add(repo_key)
        repo.metadata["provider_config_name"] = provider_name
        results.append(RepositoryResult(repo, org_name, project_name))
        return True

    try:
        accessible_repo_lister = getattr(provider, "list_accessible_repositories", None)
        org_pattern_has_wildcards = (
            "*" in pattern.org_pattern or "?" in pattern.org_pattern
        )
        if (
            not provider.supports_projects()
            and org_pattern_has_wildcards
            and callable(accessible_repo_lister)
        ):
            async for repo in accessible_repo_lister(filters={"visibility": "all"}):
                org_name = repo.organization
                if not org_name:
                    full_name = repo.metadata.get("full_name")
                    if isinstance(full_name, str) and "/" in full_name:
                        org_name = full_name.split("/", 1)[0]

                if not org_name:
                    continue

                if matches_pattern(org_name, pattern.org_pattern) and matches_pattern(
                    repo.name, pattern.repo_pattern
                ):
                    add_result(repo, org_name)

                    if limit and len(results) >= limit:
                        break

            logger.debug(
                f"Provider {provider_name}: Found {len(results)} repositories from accessible inventory"
            )
            # Deliberately fall through to the org walk below: /user/repos and
            # the org-by-org listing each see repos the other can miss (e.g.
            # fine-grained tokens), so the union is required for coverage.
            # add_result dedups the overlap. Only a reached limit short-circuits.
            if limit and len(results) >= limit:
                if progress and provider_task_id is not None:
                    progress.update(
                        provider_task_id,
                        total=1,
                        completed=1,
                        description=(
                            f"  └─ {provider_name}: Found {len(results)} repositories"
                        ),
                    )
                return results

        # Step 1: List organizations
        organizations = await provider.list_organizations()

        # Filter organizations by pattern
        matching_orgs = []
        for org in organizations:
            if matches_pattern(org.name, pattern.org_pattern):
                matching_orgs.append(org)

        logger.debug(
            f"Provider {provider_name}: Found {len(matching_orgs)} matching organizations out of {len(organizations)}"
        )

        if not matching_orgs:
            if progress and provider_task_id is not None:
                progress.update(
                    provider_task_id,
                    description=f"  └─ {provider_name}: No matching organizations",
                    completed=True,
                )
            return results

        # Update progress with organization count
        if progress and provider_task_id is not None:
            progress.update(
                provider_task_id,
                total=len(matching_orgs),
                completed=0,
                description=f"  └─ {provider_name}: Processing {len(matching_orgs)} organizations",
            )

        # Step 2: For each organization, list projects/repositories
        for i, org in enumerate(matching_orgs):
            if limit and len(results) >= limit:
                break

            try:
                # Check if provider supports projects
                if provider.supports_projects():
                    # List projects first
                    projects = await provider.list_projects(org.name)
                    matching_projects = []

                    for project in projects:
                        if matches_pattern(project.name, pattern.project_pattern):
                            matching_projects.append(project)

                    # If no projects match, skip this org
                    if not matching_projects and pattern.has_project_filter:
                        continue

                    # List repositories for each matching project
                    if matching_projects:
                        for project in matching_projects:
                            project_name = project.name if project else None

                            async for repo in provider.list_repositories(
                                org.name, project_name
                            ):
                                if matches_pattern(repo.name, pattern.repo_pattern):
                                    add_result(repo, org.name, project_name)

                                    if limit and len(results) >= limit:
                                        break

                            if limit and len(results) >= limit:
                                break
                    else:
                        # Handle case with no projects (use None)
                        async for repo in provider.list_repositories(org.name, None):
                            if matches_pattern(repo.name, pattern.repo_pattern):
                                add_result(repo, org.name, None)

                                if limit and len(results) >= limit:
                                    break
                else:
                    # Provider doesn't support projects (GitHub, BitBucket)
                    async for repo in provider.list_repositories(org.name):
                        if matches_pattern(repo.name, pattern.repo_pattern):
                            add_result(repo, org.name)

                            if limit and len(results) >= limit:
                                break

            except Exception as e:
                # Per-org degradation is by design: a fine-grained token can 403
                # one org while others succeed, so keep going and union the rest.
                errors.append(e)
                logger.warning(
                    f"Failed to list repositories for {org.name} in {provider_name}: {e}"
                )
                continue

            # Update progress
            if progress and provider_task_id is not None:
                progress.update(provider_task_id, completed=i + 1)

    except Exception as e:
        errors.append(e)
        logger.warning(
            f"Error during repository listing for provider {provider_name}: {e}"
        )
    finally:
        # Clean up provider resources
        if hasattr(provider, "cleanup"):
            await provider.cleanup()

    # A provider that yielded nothing AND errored must fail loud, not present as
    # "0 repositories". Partial results still return (union design).
    if not results and errors:
        raise errors[0]

    logger.debug(f"Provider {provider_name}: Found {len(results)} repositories")
    return results


def provider_dedup_key(result: RepositoryResult) -> str:
    """Secondary dedup key: host/org/name.

    Host is included so the same org/name on different providers (hybrid setups)
    is preserved rather than collapsed onto a single entry.
    """
    host = urlparse(result.repo.clone_url).hostname or "unknown"
    return f"{host}/{result.org_name}/{result.repo.name}"


async def _gather_provider_results(
    matching_providers: list[str],
    remaining_query: str,
    limit: int | None,
    show_progress: bool,
    fail_fast: bool,
) -> tuple[list[RepositoryResult], list[ProviderOutcome]]:
    """Query providers concurrently and return their results plus outcomes.

    With ``fail_fast`` a fatal provider error propagates as an MgitError; without
    it the provider is recorded as a failed outcome and the rest continue.
    """
    all_results: list[RepositoryResult] = []
    outcomes: list[ProviderOutcome] = []
    sem = asyncio.Semaphore(min(4, len(matching_providers)))

    progress_cm = create_progress() if show_progress else contextlib.nullcontext()

    with progress_cm as progress:
        overall_task = None
        if progress is not None:
            overall_task = progress.add_task(
                f"Discovering across {len(matching_providers)} providers...",
                total=len(matching_providers),
                repos_found=0,
            )

        async def process_provider(
            provider_name_item: str,
        ) -> tuple[list[RepositoryResult], ProviderOutcome]:
            """Process one provider and return its results plus its outcome."""
            async with sem:
                provider_task = None
                if progress is not None:
                    provider_task = progress.add_task(
                        f"  └─ {provider_name_item}: Initializing...",
                        total=None,
                        repos_found=0,
                        visible=False,
                    )

                try:
                    results = await _process_single_provider(
                        provider_name=provider_name_item,
                        query=remaining_query,
                        limit=limit,
                        progress=progress,
                        provider_task_id=provider_task,
                    )
                    if progress is not None:
                        progress.update(
                            overall_task,
                            repos_found=len(all_results) + len(results),
                        )
                        progress.advance(overall_task, 1)
                    return results, ProviderOutcome(provider_name_item, True)

                except FATAL_PROVIDER_ERRORS as e:
                    if fail_fast:
                        raise
                    logger.warning(
                        f"Failed to process provider {provider_name_item}: {e}"
                    )
                    if progress is not None:
                        progress.update(
                            provider_task,
                            description=f"  └─ {provider_name_item}: Error - {str(e)[:50]}",
                            completed=True,
                        )
                        progress.advance(overall_task, 1)
                    return [], ProviderOutcome(provider_name_item, False, str(e))

                except Exception as e:
                    logger.warning(
                        f"Failed to process provider {provider_name_item}: {e}"
                    )
                    if progress is not None:
                        progress.update(
                            provider_task,
                            description=f"  └─ {provider_name_item}: Error - {str(e)[:50]}",
                            completed=True,
                        )
                        progress.advance(overall_task, 1)
                    return [], ProviderOutcome(provider_name_item, False, str(e))

        gathered = await asyncio.gather(
            *(process_provider(pname) for pname in matching_providers),
            return_exceptions=True,
        )

        for pname, result in zip(matching_providers, gathered, strict=True):
            if isinstance(result, FATAL_PROVIDER_ERRORS):
                # Only reachable when fail_fast re-raised inside the closure.
                raise MgitError(str(result))
            elif isinstance(result, tuple):
                items, outcome = result
                all_results.extend(items)
                outcomes.append(outcome)
            elif isinstance(result, Exception):
                # Progress-machinery calls outside the closure try (add_task /
                # semaphore) can still raise; record rather than crash.
                logger.warning(f"Provider processing failed: {result}")
                outcomes.append(ProviderOutcome(pname, False, str(result)))

        if progress is not None:
            progress.update(
                overall_task,
                completed=len(matching_providers),
                repos_found=len(all_results),
                description=f"Completed - processed {len(matching_providers)} providers",
            )

    return all_results, outcomes


async def list_repositories(
    query: str,
    provider_name: str | None = None,
    format_type: str = "table",
    limit: int | None = None,
) -> ListingResult:
    """List repositories matching query pattern.

    Args:
        query: Query pattern (provider/org/project/repo) or (org/project/repo)
        provider_name: Provider configuration name (uses default if None)
        format_type: Output format ('table' or 'json')
        limit: Maximum number of results to return

    Returns:
        ListingResult with matching repositories and per-provider outcomes

    Raises:
        MgitError: If query is invalid or provider operation fails
    """
    # Validate query
    error_msg = validate_query(query)
    if error_msg:
        raise MgitError(f"Invalid query: {error_msg}")

    # Multi-provider mode whenever no specific provider is requested. The multi
    # path also handles wildcard-free queries: a non-wildcard first segment maps
    # to provider_pattern "*" against the full query.
    query_segments = query.split("/")
    first_segment = query_segments[0] if query_segments else ""
    is_multi_provider_pattern = provider_name is None

    if is_multi_provider_pattern:
        query_segments = query.split("/")

        # Check if first segment has wildcards - if so, it's a provider pattern
        # Otherwise, use all providers with the full query
        if "*" in first_segment or "?" in first_segment:
            # First segment is a provider pattern (e.g., "*/*/*" or "github*/*/*")
            provider_pattern = query_segments[0] if query_segments else "*"
            # Extract the org/project/repo part for each provider
            remaining_query = (
                "/".join(query_segments[1:]) if len(query_segments) > 1 else "*/*"
            )
        else:
            # First segment is an org name, use all providers with full query
            provider_pattern = "*"  # Match all providers
            remaining_query = query  # Use the full original query

        # Get all provider names and filter by pattern
        all_provider_names = list_provider_names()
        matching_providers = []

        for provider_name_candidate in all_provider_names:
            if matches_pattern(
                provider_name_candidate, provider_pattern, case_sensitive=False
            ):
                matching_providers.append(provider_name_candidate)

        logger.debug(
            f"Provider pattern '{provider_pattern}' matches {len(matching_providers)} providers: {matching_providers}"
        )

        if not matching_providers:
            if format_type != "json":
                console.print(
                    f"[yellow]No providers match pattern '{provider_pattern}'[/yellow]"
                )
            return ListingResult()

        show_progress = format_type != "json"
        all_results, outcomes = await _gather_provider_results(
            matching_providers,
            remaining_query,
            limit,
            show_progress,
            fail_fast=False,
        )

        logger.debug(
            f"Found {len(all_results)} total repositories from {len(matching_providers)} providers"
        )

        # Deduplicate repositories by URL, then by org/name
        seen_urls = set()
        seen_org_names = set()
        deduplicated_results = []
        duplicates_removed = 0

        for result in all_results:
            repo = result.repo

            # Primary deduplication by clone URL
            if repo.clone_url in seen_urls:
                duplicates_removed += 1
                continue

            # Secondary deduplication by host/org/name combination.
            org_name_key = provider_dedup_key(result)
            if org_name_key in seen_org_names:
                duplicates_removed += 1
                continue

            # Add to deduplicated list
            seen_urls.add(repo.clone_url)
            seen_org_names.add(org_name_key)
            deduplicated_results.append(result)

        logger.info(
            f"Multi-provider query: Found {len(deduplicated_results)} unique repositories "
            f"({len(all_results)} total, {duplicates_removed} duplicates removed) "
            f"across {len(matching_providers)} providers"
        )

        return ListingResult(results=deduplicated_results, provider_outcomes=outcomes)
    # Single provider mode: query the one requested provider, fail-fast.
    else:
        matching_providers = [provider_name]
        remaining_query = query
        show_progress = format_type != "json"
        all_results, outcomes = await _gather_provider_results(
            matching_providers,
            remaining_query,
            limit,
            show_progress,
            fail_fast=True,
        )

        logger.debug(
            f"Found {len(all_results)} total repositories from {len(matching_providers)} providers"
        )

        # Single provider: nothing to deduplicate.
        return ListingResult(results=all_results, provider_outcomes=outcomes)


def format_results(results: list[RepositoryResult], format_type: str = "table") -> None:
    """Format and display repository results.

    Args:
        results: List of repository results to display
        format_type: Output format (table or json)
    """

    if not results:
        if format_type == "json":
            print("[]")  # Empty JSON array
        else:
            console.print("[yellow]No repositories found matching query.[/yellow]")
        return

    if format_type == "json":
        import json

        output = []
        for result in results:
            # Ensure all values are JSON serializable
            output.append(
                {
                    "organization": (
                        str(result.org_name) if result.org_name is not None else None
                    ),
                    "project": (
                        str(result.project_name)
                        if result.project_name is not None
                        else None
                    ),
                    "repository": (
                        str(result.repo.name) if result.repo.name is not None else None
                    ),
                    "clone_url": (
                        str(result.repo.clone_url)
                        if result.repo.clone_url is not None
                        else None
                    ),
                    "ssh_url": (
                        str(result.repo.ssh_url)
                        if result.repo.ssh_url is not None
                        else None
                    ),
                    "default_branch": (
                        str(result.repo.default_branch)
                        if result.repo.default_branch is not None
                        else None
                    ),
                    "is_private": (
                        bool(result.repo.is_private)
                        if result.repo.is_private is not None
                        else None
                    ),
                    "description": (
                        str(result.repo.description)
                        if result.repo.description is not None
                        else None
                    ),
                }
            )
        # Use print() instead of console.print() for JSON to avoid Rich formatting issues
        print(json.dumps(output, indent=2, ensure_ascii=False))

    else:  # table format
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Organization", style="green")
        table.add_column("Project", style="blue")
        table.add_column("Repository", style="yellow")
        table.add_column("Clone URL", style="dim")

        for result in results:
            table.add_row(
                result.org_name,
                result.project_name or "-",
                result.repo.name,
                result.repo.clone_url,
            )

        console.print(table)
        console.print(f"\n[dim]Found {len(results)} repositories[/dim]")

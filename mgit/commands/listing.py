"""Listing command implementation for mgit.

Provides repository discovery across providers using query patterns.
"""

import asyncio
import logging

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from ..config.yaml_manager import list_provider_names
from ..exceptions import MgitError
from ..providers.base import Repository
from ..providers.exceptions import ConfigurationError
from ..providers.manager import ProviderManager
from ..utils.query_parser import matches_pattern, parse_query, validate_query

logger = logging.getLogger(__name__)
console = Console()


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

    try:
        # Authenticate provider
        if not await provider.authenticate():
            logger.warning(f"Failed to authenticate with provider: {provider_name}")
            return []

        logger.debug(f"Using provider: {provider.PROVIDER_NAME}")
    except Exception as e:
        logger.warning(f"Failed to initialize provider {provider_name}: {e}")
        return []

    results = []

    try:
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
                                    results.append(
                                        RepositoryResult(repo, org.name, project_name)
                                    )

                                    if limit and len(results) >= limit:
                                        break

                            if limit and len(results) >= limit:
                                break
                    else:
                        # Handle case with no projects (use None)
                        async for repo in provider.list_repositories(org.name, None):
                            if matches_pattern(repo.name, pattern.repo_pattern):
                                results.append(RepositoryResult(repo, org.name, None))

                                if limit and len(results) >= limit:
                                    break
                else:
                    # Provider doesn't support projects (GitHub, BitBucket)
                    async for repo in provider.list_repositories(org.name):
                        if matches_pattern(repo.name, pattern.repo_pattern):
                            results.append(RepositoryResult(repo, org.name))

                            if limit and len(results) >= limit:
                                break

            except Exception as e:
                logger.warning(
                    f"Failed to list repositories for {org.name} in {provider_name}: {e}"
                )
                continue

            # Update progress
            if progress and provider_task_id is not None:
                progress.update(provider_task_id, completed=i + 1)

    except Exception as e:
        logger.warning(
            f"Error during repository listing for provider {provider_name}: {e}"
        )
    finally:
        # Clean up provider resources
        if hasattr(provider, "cleanup"):
            await provider.cleanup()

    logger.debug(f"Provider {provider_name}: Found {len(results)} repositories")
    return results


async def list_repositories(
    query: str,
    provider_name: str | None = None,
    format_type: str = "table",
    limit: int | None = None,
) -> list[RepositoryResult]:
    """List repositories matching query pattern.

    Args:
        query: Query pattern (provider/org/project/repo) or (org/project/repo)
        provider_name: Provider configuration name (uses default if None)
        format_type: Output format ('table' or 'json')
        limit: Maximum number of results to return

    Returns:
        List of matching repository results

    Raises:
        MgitError: If query is invalid or provider operation fails
    """
    # Validate query
    error_msg = validate_query(query)
    if error_msg:
        raise MgitError(f"Invalid query: {error_msg}")

    # Check if this is a multi-provider wildcard discovery
    # Multi-provider mode when no specific provider and first segment has wildcards
    query_segments = query.split("/")
    first_segment = query_segments[0] if query_segments else ""
    # Multi-provider mode when no specific provider OR when provider is specified with wildcards
    # However, if a specific provider is requested, always use single-provider mode
    is_multi_provider_pattern = provider_name is None and ("*" in query or "?" in query)

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
            return []

        # Process multiple providers concurrently
        all_results = []
        sem = asyncio.Semaphore(
            min(4, len(matching_providers))
        )  # Limit concurrent providers

        show_progress = format_type != "json"
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                MofNCompleteColumn(),
                TextColumn("• {task.fields[repos_found]} repos found"),
                console=console,
                transient=False,
            ) as progress:
                # Overall discovery task
                overall_task = progress.add_task(
                    f"Discovering across {len(matching_providers)} providers...",
                    total=len(matching_providers),
                    repos_found=0,
                )

                async def process_provider(
                    provider_name_item: str,
                ) -> list[RepositoryResult]:
                    """Process a single provider and return its results."""
                    async with sem:
                        # Add provider-specific task
                        provider_task = progress.add_task(
                            f"  └─ {provider_name_item}: Initializing...",
                            total=None,
                            repos_found=0,
                        )

                        try:
                            # Process this provider
                            provider_results = await _process_single_provider(
                                provider_name=provider_name_item,
                                query=remaining_query,
                                limit=limit,
                                progress=progress,
                                provider_task_id=provider_task,
                            )

                            # Update overall progress
                            progress.update(
                                overall_task,
                                repos_found=len(all_results) + len(provider_results),
                            )
                            progress.advance(overall_task, 1)

                            return provider_results

                        except Exception as e:
                            logger.warning(
                                f"Failed to process provider {provider_name_item}: {e}"
                            )
                            progress.update(
                                provider_task,
                                description=f"  └─ {provider_name_item}: Error - {str(e)[:50]}",
                                completed=True,
                            )
                            progress.advance(overall_task, 1)
                            return []

                # Process all providers concurrently
                provider_results = await asyncio.gather(
                    *(process_provider(pname) for pname in matching_providers),
                    return_exceptions=True,
                )

                # Collect all results
                for result in provider_results:
                    if isinstance(result, list):
                        all_results.extend(result)
                    elif isinstance(result, Exception):
                        logger.warning(f"Provider processing failed: {result}")

                # Final update
                progress.update(
                    overall_task,
                    completed=len(matching_providers),
                    repos_found=len(all_results),
                    description=f"Completed - processed {len(matching_providers)} providers",
                )
        else:
            # JSON mode: no progress output
            async def process_provider(
                provider_name_item: str,
            ) -> list[RepositoryResult]:
                async with sem:
                    try:
                        return await _process_single_provider(
                            provider_name=provider_name_item,
                            query=remaining_query,
                            limit=limit,
                            progress=None,
                            provider_task_id=None,
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to process provider {provider_name_item}: {e}"
                        )
                        return []

            provider_results = await asyncio.gather(
                *(process_provider(pname) for pname in matching_providers),
                return_exceptions=True,
            )
            for result in provider_results:
                if isinstance(result, list):
                    all_results.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Provider processing failed: {result}")

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

            # Secondary deduplication by org/name combination
            org_name_key = f"{result.org_name}/{repo.name}"
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

        return deduplicated_results
    # Single provider mode - use multi-provider logic with just one provider
    else:
        # When provider is specified, treat it as multi-provider with one provider
        if provider_name:
            matching_providers = [provider_name]
            remaining_query = query
        # Process the single provider using multi-provider logic
        all_results = []
        sem = asyncio.Semaphore(1)  # Only one provider, so limit is 1

        show_progress = format_type != "json"
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                MofNCompleteColumn(),
                TextColumn("• {task.fields[repos_found]} repos found"),
                console=console,
                transient=False,
            ) as progress:
                # Overall discovery task
                overall_task = progress.add_task(
                    "Discovering repositories...",
                    total=len(matching_providers),
                    repos_found=0,
                )

                async def process_provider(
                    provider_name_item: str,
                ) -> list[RepositoryResult]:
                    """Process the provider and return its results."""
                    async with sem:
                        # Add provider-specific task
                        provider_task = progress.add_task(
                            f"  └─ {provider_name_item}: Initializing...",
                            total=None,
                            repos_found=0,
                        )

                        try:
                            # Process this provider
                            provider_results = await _process_single_provider(
                                provider_name=provider_name_item,
                                query=remaining_query,
                                limit=limit,
                                progress=progress,
                                provider_task_id=provider_task,
                            )

                            # Update overall progress
                            progress.update(
                                overall_task,
                                repos_found=len(all_results) + len(provider_results),
                            )
                            progress.advance(overall_task, 1)

                            return provider_results

                        except ConfigurationError:
                            # Fail-fast: configuration errors should propagate
                            raise
                        except Exception as e:
                            logger.warning(
                                f"Failed to process provider {provider_name_item}: {e}"
                            )
                            progress.update(
                                provider_task,
                                description=f"  └─ {provider_name_item}: Error - {str(e)[:50]}",
                                completed=True,
                            )
                            progress.advance(overall_task, 1)
                            return []

                # Process the provider
                provider_results = await asyncio.gather(
                    *(process_provider(pname) for pname in matching_providers),
                    return_exceptions=True,
                )

                # Collect results - fail-fast on configuration errors
                for result in provider_results:
                    if isinstance(result, ConfigurationError):
                        raise MgitError(str(result))
                    elif isinstance(result, list):
                        all_results.extend(result)
                    elif isinstance(result, Exception):
                        logger.warning(f"Provider processing failed: {result}")

                # Final update
                progress.update(
                    overall_task,
                    completed=len(matching_providers),
                    repos_found=len(all_results),
                    description=f"Completed - processed {len(matching_providers)} providers",
                )
        else:
            # JSON mode: no progress output
            async def process_provider(
                provider_name_item: str,
            ) -> list[RepositoryResult]:
                async with sem:
                    try:
                        return await _process_single_provider(
                            provider_name=provider_name_item,
                            query=remaining_query,
                            limit=limit,
                            progress=None,
                            provider_task_id=None,
                        )
                    except ConfigurationError:
                        # Fail-fast: configuration errors should propagate
                        raise
                    except Exception as e:
                        logger.warning(
                            f"Failed to process provider {provider_name_item}: {e}"
                        )
                        return []

            provider_results = await asyncio.gather(
                *(process_provider(pname) for pname in matching_providers),
                return_exceptions=True,
            )
            # Collect results - fail-fast on configuration errors
            for result in provider_results:
                if isinstance(result, ConfigurationError):
                    raise MgitError(str(result))
                elif isinstance(result, list):
                    all_results.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Provider processing failed: {result}")

        logger.debug(
            f"Found {len(all_results)} total repositories from {len(matching_providers)} providers"
        )

        # For single provider, skip deduplication since there's only one provider
        return all_results


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

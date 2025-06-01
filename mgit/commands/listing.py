"""Listing command implementation for mgit.

Provides repository discovery across providers using query patterns.
"""

import logging
from typing import List, Optional

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

from ..exceptions import MgitError
from ..providers.base import Repository
from ..providers.manager_v2 import ProviderManager
from ..utils.query_parser import matches_pattern, parse_query, validate_query

logger = logging.getLogger(__name__)
console = Console()


class RepositoryResult:
    """Container for repository search results."""

    def __init__(
        self, repo: Repository, org_name: str, project_name: Optional[str] = None
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


async def list_repositories(
    query: str,
    provider_name: Optional[str] = None,
    format_type: str = "table",
    limit: Optional[int] = None,
) -> List[RepositoryResult]:
    """List repositories matching query pattern.

    Args:
        query: Query pattern (org/project/repo)
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

    # Parse query pattern
    pattern = parse_query(query)
    logger.debug(
        f"Parsed query '{query}' into: org={pattern.org_pattern}, project={pattern.project_pattern}, repo={pattern.repo_pattern}"
    )

    # Get provider
    provider_manager = ProviderManager(provider_name=provider_name)
    try:
        provider = provider_manager.get_provider()
        if not provider:
            raise MgitError(
                "No provider available. Use 'mgit config list' to see configured providers."
            )

        # Authenticate provider
        if not await provider.authenticate():
            raise MgitError("Failed to authenticate with provider")

        logger.debug(f"Using provider: {provider.PROVIDER_NAME}")

    except Exception as e:
        raise MgitError(f"Failed to initialize provider: {e}")

    results = []

    try:
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

            # Step 1: List organizations
            discovery_task = progress.add_task(
                "Discovering organizations...", total=None, repos_found=0
            )
            organizations = await provider.list_organizations()

            # Filter organizations by pattern
            matching_orgs = []
            for org in organizations:
                if matches_pattern(org.name, pattern.org_pattern):
                    matching_orgs.append(org)

            logger.debug(
                f"Found {len(matching_orgs)} matching organizations out of {len(organizations)}"
            )

            if not matching_orgs:
                progress.update(discovery_task, completed=True)
                console.print(
                    f"[yellow]No organizations match pattern '{pattern.org_pattern}'[/yellow]"
                )
                return results

            # Update overall progress with known organization count
            progress.update(
                discovery_task,
                total=len(matching_orgs),
                completed=0,
                description="Processing organizations",
            )

            # Step 2: For each organization, list projects/repositories
            for i, org in enumerate(matching_orgs):
                if limit and len(results) >= limit:
                    break

                # Update overall progress
                progress.update(
                    discovery_task,
                    completed=i,
                    repos_found=len(results),
                    description=f"Processing {org.name} ({i+1}/{len(matching_orgs)})",
                )

                # Add organization-specific task
                org_task = progress.add_task(
                    f"  └─ Scanning {org.name}", total=None, repos_found=len(results)
                )

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
                            progress.update(
                                org_task,
                                description=f"  └─ {org.name}: No matching projects",
                                completed=True,
                            )
                            continue

                        # Update with project count if we have projects to process
                        if matching_projects:
                            progress.update(
                                org_task,
                                total=len(matching_projects),
                                completed=0,
                                description=f"  └─ {org.name}: Processing projects",
                            )

                            # List repositories for each matching project
                            for j, project in enumerate(matching_projects):
                                project_name = project.name if project else None

                                # Add project-level task
                                project_task = progress.add_task(
                                    f"      └─ {project.name}",
                                    total=None,
                                    repos_found=0,
                                )
                                project_repos = 0

                                async for repo in provider.list_repositories(
                                    org.name, project_name
                                ):
                                    if matches_pattern(repo.name, pattern.repo_pattern):
                                        results.append(
                                            RepositoryResult(
                                                repo, org.name, project_name
                                            )
                                        )
                                        project_repos += 1

                                        # Update counters
                                        progress.update(
                                            project_task,
                                            repos_found=project_repos,
                                            description=f"      └─ {project.name}: {project_repos} repos",
                                        )
                                        progress.update(
                                            org_task, repos_found=len(results)
                                        )
                                        progress.update(
                                            discovery_task, repos_found=len(results)
                                        )

                                        if limit and len(results) >= limit:
                                            break

                                progress.update(project_task, completed=True)
                                progress.update(org_task, completed=j + 1)

                                if limit and len(results) >= limit:
                                    break
                        else:
                            # Handle case with no projects (use None)
                            async for repo in provider.list_repositories(
                                org.name, None
                            ):
                                if matches_pattern(repo.name, pattern.repo_pattern):
                                    results.append(
                                        RepositoryResult(repo, org.name, None)
                                    )

                                    # Update counters
                                    progress.update(org_task, repos_found=len(results))
                                    progress.update(
                                        discovery_task, repos_found=len(results)
                                    )

                                    if limit and len(results) >= limit:
                                        break

                            progress.update(org_task, completed=True)
                    else:
                        # Provider doesn't support projects (GitHub, BitBucket)
                        org_repos = 0
                        async for repo in provider.list_repositories(org.name):
                            if matches_pattern(repo.name, pattern.repo_pattern):
                                results.append(RepositoryResult(repo, org.name))
                                org_repos += 1

                                # Update counters
                                progress.update(
                                    org_task,
                                    repos_found=org_repos,
                                    description=f"  └─ {org.name}: {org_repos} repos",
                                )
                                progress.update(
                                    discovery_task, repos_found=len(results)
                                )

                                if limit and len(results) >= limit:
                                    break

                        progress.update(org_task, completed=True)

                except Exception as e:
                    logger.warning(f"Failed to list repositories for {org.name}: {e}")
                    progress.update(
                        org_task,
                        description=f"  └─ {org.name}: Error - {str(e)[:50]}",
                        completed=True,
                    )
                    continue

            # Final update
            progress.update(
                discovery_task,
                completed=len(matching_orgs),
                repos_found=len(results),
                description=f"Completed - processed {len(matching_orgs)} organizations",
            )

    except Exception as e:
        raise MgitError(f"Error during repository listing: {e}")
    finally:
        # Clean up provider resources if cleanup method exists
        if hasattr(provider, "cleanup"):
            await provider.cleanup()

    logger.debug(f"Found {len(results)} total repositories matching query")
    return results


def format_results(results: List[RepositoryResult], format_type: str = "table") -> None:
    """Format and display repository results.

    Args:
        results: List of repository results to display
        format_type: Output format ('table' or 'json')
    """
    if not results:
        console.print("[yellow]No repositories found matching query.[/yellow]")
        return

    if format_type == "json":
        import json

        output = []
        for result in results:
            output.append(
                {
                    "organization": result.org_name,
                    "project": result.project_name,
                    "repository": result.repo.name,
                    "clone_url": result.repo.clone_url,
                    "ssh_url": result.repo.ssh_url,
                    "default_branch": result.repo.default_branch,
                    "is_private": result.repo.is_private,
                    "description": result.repo.description,
                }
            )
        console.print(json.dumps(output, indent=2))

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

"""
Remote repository change detection command.

Provides functionality to discover repositories through provider queries
and detect their changes, combining remote discovery with local change detection.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import asdict

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from mgit.discovery.change_discovery import ChangeDiscoveryEngine, ChangeDiscoveryResult
from mgit.changesets.storage import ChangesetStorage
from mgit.commands.diff import _convert_to_repository_changeset

logger = logging.getLogger(__name__)
console = Console()


def execute_remote_diff_command(
    pattern: str,
    local_root: Optional[Path],
    provider: Optional[str],
    output: Optional[Path],
    save_changeset: bool,
    changeset_name: str,
    include_remote_only: bool,
    concurrency: int,
    limit: Optional[int],
    verbose: bool,
) -> None:
    """
    Execute remote repository change detection.

    Args:
        pattern: Repository search pattern (e.g., "myorg/*/*")
        local_root: Root directory to scan for local repository clones
        provider: Specific provider to query (None for all)
        output: Optional output file path for results
        save_changeset: Whether to save results to changeset storage
        changeset_name: Name of changeset collection for storage
        include_remote_only: Include repositories found remotely but not locally
        concurrency: Number of concurrent operations
        limit: Maximum repositories to process
        verbose: Enable verbose output
    """
    if verbose:
        logging.getLogger("mgit").setLevel(logging.DEBUG)
        console.print(
            f"[blue]Starting remote change discovery for pattern: {pattern}[/blue]"
        )

    try:
        # Initialize discovery engine
        engine = ChangeDiscoveryEngine(
            local_scan_root=local_root, concurrency=concurrency
        )

        # Perform discovery
        with Progress() as progress:
            task = progress.add_task("[green]Discovering repositories...", total=None)

            result = asyncio.run(
                engine.discover_repository_changes(
                    query_pattern=pattern,
                    provider_name=provider,
                    include_remote_only=include_remote_only,
                    limit=limit,
                )
            )

            progress.update(task, completed=100, total=100)

        # Display results summary
        _display_discovery_summary(result, verbose)

        # Save to changeset storage if requested
        if save_changeset:
            _save_discovery_to_changesets(result, changeset_name, verbose)

        # Output detailed results
        if output or not save_changeset:
            _output_discovery_results(result, output, verbose)

        if verbose:
            console.print(
                f"[green]Remote change discovery completed successfully[/green]"
            )

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error during remote change discovery: {e}[/red]")
        logger.error(f"Remote change discovery failed: {e}")
        raise typer.Exit(1)


def _display_discovery_summary(result: ChangeDiscoveryResult, verbose: bool) -> None:
    """Display summary of discovery results."""

    # Create summary table
    table = Table(title="Repository Discovery Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Details", style="dim")

    table.add_row(
        "Total Repositories",
        str(len(result.discovered_repositories)),
        "Found across all providers",
    )
    table.add_row(
        "Local Repositories",
        str(result.local_repositories_found),
        "With local clones available",
    )
    table.add_row(
        "Remote Only",
        str(result.remote_only_repositories),
        "Found remotely but not locally",
    )
    table.add_row(
        "With Changes",
        str(result.total_repositories_with_changes),
        "Have uncommitted changes",
    )

    if result.successful_providers:
        table.add_row(
            "Successful Providers",
            str(len(result.successful_providers)),
            ", ".join(result.successful_providers),
        )

    if result.failed_providers:
        table.add_row(
            "Failed Providers",
            str(len(result.failed_providers)),
            ", ".join(result.failed_providers),
        )

    table.add_row(
        "Success Rate", f"{result.success_rate:.1%}", "Provider query success rate"
    )

    console.print(table)

    if verbose and result.discovered_repositories:
        # Show detailed repository information
        console.print("\n[bold]Repository Details:[/bold]")

        for repo_change in result.discovered_repositories:
            status_emoji = "✅" if repo_change.local_path else "🌐"
            changes_info = ""

            if repo_change.changeset:
                if repo_change.changeset.has_uncommitted_changes:
                    changes_info = f" ([yellow]{len(repo_change.changeset.uncommitted_files)} changes[/yellow])"
                else:
                    changes_info = " ([green]clean[/green])"
            elif repo_change.local_path:
                changes_info = " ([red]error[/red])"

            console.print(
                f"  {status_emoji} {repo_change.repository.organization}/{repo_change.repository.name}{changes_info}"
            )

            if verbose and repo_change.error:
                console.print(f"    [red]Error: {repo_change.error}[/red]")


def _save_discovery_to_changesets(
    result: ChangeDiscoveryResult, changeset_name: str, verbose: bool
) -> None:
    """Save discovery results to changeset storage."""
    try:
        storage = ChangesetStorage()
        changesets_saved = 0

        with storage.atomic_update(changeset_name) as collection:
            # Add metadata about the discovery operation
            collection.metadata.update(
                {
                    "discovery_query": result.query_pattern,
                    "discovery_timestamp": collection.updated_at,
                    "total_discovered": len(result.discovered_repositories),
                    "local_repositories": result.local_repositories_found,
                    "remote_only_repositories": result.remote_only_repositories,
                    "successful_providers": result.successful_providers,
                    "failed_providers": result.failed_providers,
                }
            )

            # Save changesets for repositories with local changes
            for repo_change in result.discovered_repositories:
                if repo_change.changeset and not repo_change.error:
                    collection.add_repository(repo_change.changeset)
                    changesets_saved += 1

        if verbose:
            console.print(
                f"[green]Saved {changesets_saved} changesets to collection: {changeset_name}[/green]"
            )

    except Exception as e:
        logger.error(f"Failed to save discovery to changesets: {e}")
        if verbose:
            console.print(f"[red]Failed to save changesets: {e}[/red]")


def _output_discovery_results(
    result: ChangeDiscoveryResult, output: Optional[Path], verbose: bool
) -> None:
    """Output detailed discovery results in JSONL format."""
    import json

    output_stream = sys.stdout
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output_stream = output.open("w", encoding="utf-8")

    try:
        written_count = 0

        for repo_change in result.discovered_repositories:
            try:
                # Convert to serializable format
                result_data = {
                    "repository": {
                        "name": repo_change.repository.name,
                        "organization": repo_change.repository.organization,
                        "project": repo_change.repository.project,
                        "clone_url": repo_change.repository.clone_url,
                        "description": repo_change.repository.description,
                        "default_branch": repo_change.repository.default_branch,
                    },
                    "local_path": (
                        str(repo_change.local_path) if repo_change.local_path else None
                    ),
                    "provider_name": repo_change.provider_name,
                    "discovery_query": repo_change.discovery_query,
                    "has_local_clone": repo_change.local_path is not None,
                    "changeset": None,
                    "error": repo_change.error,
                }

                # Include changeset data if available
                if repo_change.changeset:
                    result_data["changeset"] = asdict(repo_change.changeset)

                # Write as JSONL
                json_line = json.dumps(
                    result_data, ensure_ascii=False, separators=(",", ":")
                )
                output_stream.write(json_line + "\n")
                output_stream.flush()

                written_count += 1

            except Exception as e:
                logger.error(
                    f"Error writing result for {repo_change.repository.name}: {e}"
                )

        if verbose:
            console.print(f"[blue]Wrote {written_count} discovery results[/blue]")

    finally:
        if output_stream != sys.stdout:
            output_stream.close()

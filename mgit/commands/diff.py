"""
Change detection command implementation.

Provides functionality to detect and report changes in Git repositories,
outputting structured data in JSONL format for pipeline processing.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, TextIO
from dataclasses import dataclass, asdict
from datetime import datetime

import typer
from rich.console import Console
from rich.progress import Progress, TaskID

from mgit.git.manager import GitManager
from mgit.git.utils import is_git_repository
from mgit.changesets.models import RepositoryChangeset, FileChange, CommitInfo
from mgit.changesets.storage import ChangesetStorage
from mgit.content.embedding import ContentEmbeddingEngine, EmbeddingConfig
from mgit.content.embedding import ContentStrategy
from mgit.processing import DiffProcessor, RepositoryChange
from mgit.discovery.change_discovery import ChangeDiscoveryEngine

logger = logging.getLogger(__name__)
console = Console()


def _find_repositories(path: Path, recursive: bool) -> List[Path]:
    """
    Find Git repositories in the given path.

    Args:
        path: Path to search
        recursive: Whether to search recursively

    Returns:
        List of repository paths
    """
    repositories = []

    # Check if the root path itself is a repository
    if is_git_repository(path):
        repositories.append(path)

    if recursive:
        # Recursively find all .git directories
        for git_dir in path.rglob(".git"):
            if git_dir.is_dir():
                parent_repo = git_dir.parent
                if parent_repo not in repositories:
                    repositories.append(parent_repo)
    else:
        # Only check immediate subdirectories
        for item in path.iterdir():
            if item.is_dir() and is_git_repository(item) and item not in repositories:
                repositories.append(item)

    return repositories


def execute_diff_command(
    path: Path,
    output: Optional[Path],
    recursive: bool,
    concurrency: int,
    verbose: bool,
    save_changeset: bool = False,
    changeset_name: str = "default",
    incremental: bool = False,
    embed_content: bool = False,
    content_strategy: str = "sample",
    content_memory_mb: int = 100,
    discover_pattern: Optional[str] = None,
    discover_provider: Optional[str] = None,
    merge_discovered: bool = False,
) -> None:
    """
    Execute diff command with optional repository discovery integration.

    Args:
        path: Path to repository or directory to scan
        output: Optional output file path
        recursive: Whether to scan recursively for repositories
        concurrency: Number of concurrent operations
        verbose: Whether to enable verbose output
        save_changeset: Whether to save changesets to persistent storage
        changeset_name: Name of changeset collection to use
        incremental: Whether to only report changes since last save
        embed_content: Whether to embed file content in the output
        content_strategy: Content embedding strategy
        content_memory_mb: Memory budget for content embedding
        discover_pattern: Optional pattern for discovering additional repositories
        discover_provider: Provider to use for discovery
        merge_discovered: Whether to merge discovered repos with local scan
    """
    if verbose:
        logging.getLogger("mgit").setLevel(logging.DEBUG)
        console.print(f"[blue]Starting change detection on: {path}[/blue]")
        if embed_content:
            console.print(
                f"[blue]Content embedding enabled with strategy: {content_strategy}[/blue]"
            )

    # Initialize changeset storage if needed
    storage = None
    previous_collection = None
    if save_changeset or incremental:
        storage = ChangesetStorage()
        if incremental:
            previous_collection = storage.load_changeset_collection(changeset_name)
            if verbose and previous_collection:
                console.print(
                    f"[blue]Loaded previous changeset with {previous_collection.repository_count} repositories[/blue]"
                )

    try:
        # Discover repositories
        repositories = _find_repositories(path, recursive)

        if not repositories:
            console.print(
                "[yellow]No repositories found in the specified path.[/yellow]"
            )
            return

        if verbose:
            console.print(
                f"[blue]Found {len(repositories)} repositories to analyze[/blue]"
            )

        # Optional repository discovery via providers
        discovered_repos = []
        if discover_pattern:
            if verbose:
                console.print(
                    f"[blue]Discovering repositories with pattern: {discover_pattern}[/blue]"
                )

            discovery_engine = ChangeDiscoveryEngine(local_scan_root=path.parent)

            discovery_result = asyncio.run(
                discovery_engine.discover_repository_changes(
                    query_pattern=discover_pattern,
                    provider_name=discover_provider,
                    include_remote_only=False,  # Only include locally available repos
                )
            )

            # Extract local paths from discovery results
            for repo_change in discovery_result.discovered_repositories:
                if repo_change.local_path and repo_change.local_path.exists():
                    discovered_repos.append(repo_change.local_path)

            if verbose and discovered_repos:
                console.print(
                    f"[blue]Discovered {len(discovered_repos)} additional repositories[/blue]"
                )

        # Merge discovered repositories with local scan if requested
        if merge_discovered and discovered_repos:
            # Avoid duplicates by converting to set of resolved paths
            all_repo_paths = set(repo.resolve() for repo in repositories)
            new_repo_paths = set(repo.resolve() for repo in discovered_repos)

            # Add new repositories not already in local scan
            additional_repos = new_repo_paths - all_repo_paths
            repositories.extend(Path(p) for p in additional_repos)

            if verbose and additional_repos:
                console.print(
                    f"[blue]Added {len(additional_repos)} discovered repositories to scan[/blue]"
                )

        # Process repositories with content embedding support
        content_strategy_enum = ContentStrategy(content_strategy.lower())
        processor = DiffProcessor(
            concurrency=concurrency,
            embed_content=embed_content,
            content_strategy=content_strategy_enum,
            content_memory_mb=content_memory_mb,
        )

        with Progress() as progress:
            task = progress.add_task(
                "[green]Detecting changes...", total=len(repositories)
            )

            # Run async processing
            changes = asyncio.run(
                processor.process_repositories(repositories, progress, task)
            )

        # Filter for incremental changes if requested
        if incremental and previous_collection:
            changes = _filter_incremental_changes(changes, previous_collection, verbose)
            if verbose:
                console.print(
                    f"[blue]Found {len(changes)} repositories with changes since last scan[/blue]"
                )

        # Save to changeset storage if requested
        if save_changeset and storage:
            _save_to_changeset_storage(changes, storage, changeset_name, verbose)

        # Output results
        output_stream = _get_output_stream(output)
        try:
            _write_changes_jsonl(changes, output_stream, verbose)
        finally:
            if output_stream != sys.stdout:
                output_stream.close()

        if verbose:
            console.print(
                f"[green]Change detection completed. Processed {len(changes)} repositories.[/green]"
            )

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error during change detection: {e}[/red]")
        logger.error(f"Change detection failed: {e}")
        raise typer.Exit(1)


def _get_output_stream(output: Optional[Path]) -> TextIO:
    """Get the appropriate output stream for results."""
    if output:
        # Ensure output directory exists
        output.parent.mkdir(parents=True, exist_ok=True)
        return output.open("w", encoding="utf-8")
    else:
        return sys.stdout


def _write_changes_jsonl(
    changes: List[RepositoryChange], stream: TextIO, verbose: bool
) -> None:
    """
    Write file-level change data to output stream in JSONL format.

    Args:
        changes: List of repository changes to write
        stream: Output stream to write to
        verbose: Whether to log verbose information
    """
    file_count = 0
    repo_count = 0
    error_count = 0

    def _map_change_type_to_operation(change_type: str) -> str:
        """Map git change types to pipeline operations."""
        mapping = {
            "added": "add",
            "modified": "modify",
            "deleted": "delete",
            "untracked": "add",
            "renamed": "modify",
            "copied": "add",
            "unknown": "modify",
        }
        return mapping.get(change_type, "modify")

    for change in changes:
        try:
            if change.error:
                if verbose:
                    console.print(
                        f"[yellow]Warning - {change.repository_name}: {change.error}[/yellow]"
                    )
                continue

            repo_name = change.repository_name

            # Output file-level changes
            for file_change in change.uncommitted_files:
                file_record = {
                    "repo": repo_name,
                    "op": _map_change_type_to_operation(file_change["change_type"]),
                    "path": file_change["filename"],
                }

                # Add embedded content if present
                if "embedded_content" in file_change:
                    embedded = file_change["embedded_content"]
                    if embedded.get("error"):
                        # Include error information
                        file_record["content_error"] = embedded["error"]
                    else:
                        # Include successful embedding data
                        file_record.update(
                            {
                                "content": embedded.get("content"),
                                "content_hash": embedded.get("content_hash"),
                                "size_bytes": embedded.get("size_bytes"),
                                "mime_type": embedded.get("mime_type"),
                                "charset": embedded.get("charset"),
                                "is_truncated": embedded.get("is_truncated"),
                                "line_count": embedded.get("line_count"),
                            }
                        )

                json_line = json.dumps(
                    file_record, ensure_ascii=False, separators=(",", ":")
                )
                stream.write(json_line + "\n")
                stream.flush()
                file_count += 1

            # Output changeset record if we have commit info
            if change.recent_commits or change.current_branch:
                changeset_data = {}
                if change.recent_commits:
                    changeset_data["commit"] = change.recent_commits[0].get("hash", "")
                if change.current_branch:
                    changeset_data["branch"] = change.current_branch

                if changeset_data:
                    changeset_record = {
                        "repo": repo_name,
                        "new_changeset": changeset_data,
                    }
                    json_line = json.dumps(
                        changeset_record, ensure_ascii=False, separators=(",", ":")
                    )
                    stream.write(json_line + "\n")
                    stream.flush()

            repo_count += 1

        except Exception as e:
            error_count += 1
            logger.error(f"Error writing change data for {change.repository_path}: {e}")

    if verbose:
        console.print(
            f"[blue]Wrote {file_count} file records from {repo_count} repositories, {error_count} errors[/blue]"
        )


def _convert_to_repository_changeset(change: RepositoryChange) -> "RepositoryChangeset":
    """Convert RepositoryChange to RepositoryChangeset for storage."""
    from mgit.changesets.models import RepositoryChangeset, FileChange, CommitInfo

    # Convert file changes
    file_changes = []
    for file_data in change.uncommitted_files:
        file_changes.append(
            FileChange(
                filename=file_data["filename"],
                change_type=file_data["change_type"],
                index_status=file_data["index_status"],
                worktree_status=file_data["worktree_status"],
            )
        )

    # Convert commit info
    commits = []
    for commit_data in change.recent_commits:
        commits.append(
            CommitInfo(
                hash=commit_data["hash"],
                author_name=commit_data["author_name"],
                author_email=commit_data["author_email"],
                date=commit_data["date"],
                message=commit_data["message"],
            )
        )

    return RepositoryChangeset(
        repository_path=change.repository_path,
        repository_name=change.repository_name,
        timestamp=change.timestamp,
        has_uncommitted_changes=change.has_uncommitted_changes,
        current_branch=change.current_branch,
        git_status=change.git_status,
        uncommitted_files=file_changes,
        recent_commits=commits,
        error=change.error,
    )


def _save_to_changeset_storage(
    changes: List[RepositoryChange],
    storage: ChangesetStorage,
    collection_name: str,
    verbose: bool,
) -> None:
    """Save repository changes to persistent storage."""
    try:
        with storage.atomic_update(collection_name) as collection:
            for change in changes:
                changeset = _convert_to_repository_changeset(change)
                collection.add_repository(changeset)

        if verbose:
            console.print(
                f"[green]Saved {len(changes)} changesets to collection: {collection_name}[/green]"
            )

    except Exception as e:
        logger.error(f"Failed to save changesets: {e}")
        if verbose:
            console.print(f"[red]Failed to save changesets: {e}[/red]")


def _filter_incremental_changes(
    current_changes: List[RepositoryChange], previous_collection, verbose: bool
) -> List[RepositoryChange]:
    """Filter changes to only include repositories with differences since last scan."""
    incremental_changes = []

    for change in current_changes:
        previous_changeset = previous_collection.get_repository(change.repository_path)

        if previous_changeset is None:
            # New repository - include it
            incremental_changes.append(change)
            if verbose:
                console.print(
                    f"[yellow]New repository: {change.repository_name}[/yellow]"
                )
            continue

        # Check if there are meaningful differences
        if _has_meaningful_changes(change, previous_changeset):
            incremental_changes.append(change)
            if verbose:
                console.print(
                    f"[yellow]Changed repository: {change.repository_name}[/yellow]"
                )

    return incremental_changes


def _has_meaningful_changes(current: RepositoryChange, previous) -> bool:
    """Check if current changeset has meaningful differences from previous."""

    # Different git status
    if current.git_status != previous.git_status:
        return True

    # Different uncommitted changes status
    if current.has_uncommitted_changes != previous.has_uncommitted_changes:
        return True

    # Different branch
    if current.current_branch != previous.current_branch:
        return True

    # Different number of uncommitted files
    if len(current.uncommitted_files) != len(previous.uncommitted_files):
        return True

    # Different recent commits (check latest commit hash)
    current_latest = (
        current.recent_commits[0]["hash"] if current.recent_commits else None
    )
    previous_latest = (
        previous.recent_commits[0].hash if previous.recent_commits else None
    )

    if current_latest != previous_latest:
        return True

    return False

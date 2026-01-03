"""Status command implementation for mgit.

Provides a high-performance status overview for multiple repositories.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..git.utils import is_git_repository
from ..utils.async_executor import AsyncExecutor

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class RepositoryStatus:
    """Holds the parsed status of a single Git repository."""

    path: Path
    is_clean: bool = True
    branch_name: str = ""
    remote_branch: str = ""
    ahead_by: int = 0
    behind_by: int = 0
    modified_files: int = 0
    untracked_files: int = 0
    staged_files: int = 0
    error: str | None = None


async def _get_single_repo_status(repo_path: Path, fetch: bool) -> RepositoryStatus:
    """Gets the status of a single repository."""
    try:
        if fetch:
            fetch_cmd = ["git", "fetch"]
            process = await asyncio.create_subprocess_exec(
                *fetch_cmd,
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            if process.returncode != 0:
                logger.warning(f"git fetch failed for {repo_path}")

        status_cmd = ["git", "status", "--porcelain=v1", "-b"]
        process = await asyncio.create_subprocess_exec(
            *status_cmd,
            cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            return RepositoryStatus(
                path=repo_path,
                is_clean=False,
                error=stderr.decode("utf-8", errors="ignore").strip(),
            )

        raw_output = stdout.decode("utf-8", errors="ignore")
        return _parse_status_output(repo_path, raw_output)
    except Exception as e:
        return RepositoryStatus(path=repo_path, is_clean=False, error=str(e))


def _parse_status_output(repo_path: Path, output: str) -> RepositoryStatus:
    """Parses the output of 'git status --porcelain=v1 -b'."""
    lines = output.strip().split("\n")
    status = RepositoryStatus(path=repo_path)

    if not lines or not lines[0].startswith("##"):
        status.is_clean = False
        status.error = "Could not parse branch information."
        return status

    # Parse branch line
    branch_line = lines.pop(0)
    branch_match = re.match(
        r"## (?P<branch>.*?)(?:\.\.\.(?P<remote>.*?))?(?: \[(?:ahead (?P<ahead>\d+))?,? ?(?:behind (?P<behind>\d+))?\])?$",
        branch_line,
    )
    if branch_match:
        status.branch_name = branch_match.group("branch")
        status.remote_branch = branch_match.group("remote") or ""
        status.ahead_by = int(branch_match.group("ahead") or 0)
        status.behind_by = int(branch_match.group("behind") or 0)

    # Parse file status lines
    for line in lines:
        if line.strip():
            status.is_clean = False
            if line.startswith("??"):
                status.untracked_files += 1
            else:
                # Check staged (index) status
                if line[0] != " ":
                    status.staged_files += 1
                # Check modified (worktree) status
                if line[1] != " ":
                    status.modified_files += 1

    if status.ahead_by > 0 or status.behind_by > 0:
        status.is_clean = False

    return status


async def get_repository_statuses(
    path: Path, concurrency: int, fetch: bool, json_mode: bool = False
) -> list[RepositoryStatus]:
    """Finds all git repos in a path and gets their status concurrently."""
    if not json_mode:
        logger.info(f"Getting statuses for repos in: {path}")
    repos_to_check = []
    # First, check if the root path itself is a repository
    if is_git_repository(path):
        repos_to_check.append(path)

    # Then, find all .git directories inside and get their parents
    for git_dir in path.rglob(".git"):
        if git_dir.is_dir():
            parent_repo = git_dir.parent
            if parent_repo not in repos_to_check:
                repos_to_check.append(parent_repo)

    if not repos_to_check:
        return []

    # For JSON mode, disable progress output to avoid mixing with JSON output
    import io

    from rich.console import Console

    if json_mode:
        # Create a null console that discards all output
        progress_console = Console(file=io.StringIO(), force_terminal=False)
    else:
        progress_console = console

    executor = AsyncExecutor(concurrency=concurrency, rich_console=progress_console)

    async def process_repo(repo_path: Path):
        return await _get_single_repo_status(repo_path, fetch)

    results, errors = await executor.run_batch(
        items=repos_to_check,
        process_func=process_repo,
        task_description="Checking repository statuses...",
    )

    # Process errors into status objects
    for repo_path, error in errors:
        results.append(
            RepositoryStatus(path=repo_path, is_clean=False, error=str(error))
        )

    # Filter out None results if any and sort by path
    final_results = sorted([r for r in results if r], key=lambda r: r.path)

    return final_results


def display_status_results(
    results: list[RepositoryStatus], output_format: str, show_clean: bool
):
    """Displays the status results in the specified format."""
    if output_format != "json":
        logger.info(f"Entering display_status_results with {len(results)} results.")
        logger.debug(
            f"Displaying {len(results)} status results in {output_format} format."
        )
    if not show_clean:
        results = [r for r in results if not r.is_clean]

    if not results:
        if output_format == "json":
            console.print("[]")
        else:
            console.print("[green]✓ All repositories are clean.[/green]")
        return

    if output_format == "json":
        json_output = [
            {
                "path": str(r.path),
                "is_clean": r.is_clean,
                "branch": r.branch_name,
                "remote_branch": r.remote_branch,
                "ahead": r.ahead_by,
                "behind": r.behind_by,
                "modified": r.modified_files,
                "untracked": r.untracked_files,
                "staged": r.staged_files,
                "error": r.error,
            }
            for r in results
        ]
        # Use print() instead of console.print() for JSON to avoid Rich formatting issues
        print(json.dumps(json_output, indent=2))
    else:
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Repository", style="cyan", max_width=50, overflow="fold")
        table.add_column("Branch", style="yellow")
        table.add_column("Status")

        for r in results:
            status_parts = []
            if r.error:
                status_parts.append(f"[red]Error: {r.error}[/red]")
            elif r.is_clean:
                status_parts.append("[green]Clean[/green]")
            else:
                if r.ahead_by:
                    status_parts.append(f"[bold blue]Ahead ({r.ahead_by})[/bold blue]")
                if r.behind_by:
                    status_parts.append(f"[bold red]Behind ({r.behind_by})[/bold red]")
                if r.modified_files:
                    status_parts.append(
                        f"[yellow]Modified ({r.modified_files})[/yellow]"
                    )
                if r.staged_files:
                    status_parts.append(f"[cyan]Staged ({r.staged_files})[/cyan]")
                if r.untracked_files:
                    status_parts.append(
                        f"[magenta]Untracked ({r.untracked_files})[/magenta]"
                    )

            status_str = ", ".join(status_parts)
            table.add_row(str(r.path), r.branch_name, status_str)

        console.print(table)

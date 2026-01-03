"""
Sync command implementation.

Provides a unified interface for repository synchronization that combines
the functionality of clone-all and pull-all into a single, intuitive command.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

from mgit.commands.bulk_operations import (
    BulkOperationProcessor,
    OperationType,
    check_force_mode_confirmation,
)
from mgit.config.yaml_manager import get_global_setting, list_provider_names
from mgit.exceptions import MgitError
from mgit.git import GitManager
from mgit.git.utils import build_repo_path, get_git_remote_url
from mgit.providers import detect_provider_by_url
from mgit.providers.manager import ProviderManager
from mgit.providers.base import Repository
from mgit.utils.async_executor import AsyncExecutor
from mgit.utils.directory_scanner import find_repositories_in_directory
from mgit.utils.pattern_matching import analyze_pattern
from mgit.utils.multi_provider_resolver import MultiProviderResolver

logger = logging.getLogger(__name__)
console = Console()

LOCAL_ACTION_PULL = "pull"
LOCAL_ACTION_PULLED = "pulled"
LOCAL_ACTION_SKIP_DIRTY = "skipped_dirty"
LOCAL_ACTION_SKIP_NO_REMOTE = "skipped_no_remote"
LOCAL_ACTION_FAILED = "failed"


@dataclass
class LocalRepoState:
    path: Path
    name: str
    remote_url: Optional[str]
    provider: str
    is_dirty: bool
    error: Optional[str] = None


@dataclass
class LocalRepoResult:
    state: LocalRepoState
    action: str
    error: Optional[str] = None


def _detect_local_provider(remote_url: Optional[str]) -> str:
    if not remote_url:
        return "unknown"
    try:
        return detect_provider_by_url(remote_url)
    except Exception:
        return "unknown"


async def _run_git_command(repo_path: Path, args: List[str]) -> Tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=str(repo_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return (
        process.returncode or 0,
        stdout.decode("utf-8", errors="ignore"),
        stderr.decode("utf-8", errors="ignore"),
    )


async def _inspect_local_repository(repo_path: Path) -> LocalRepoState:
    remote_url = get_git_remote_url(repo_path)
    provider = _detect_local_provider(remote_url)

    try:
        returncode, stdout, stderr = await _run_git_command(
            repo_path, ["status", "--porcelain"]
        )
        if returncode != 0:
            error_msg = stderr.strip() or stdout.strip() or "git status failed"
            return LocalRepoState(
                path=repo_path,
                name=repo_path.name,
                remote_url=remote_url,
                provider=provider,
                is_dirty=True,
                error=error_msg,
            )
        return LocalRepoState(
            path=repo_path,
            name=repo_path.name,
            remote_url=remote_url,
            provider=provider,
            is_dirty=bool(stdout.strip()),
        )
    except Exception as exc:
        return LocalRepoState(
            path=repo_path,
            name=repo_path.name,
            remote_url=remote_url,
            provider=provider,
            is_dirty=True,
            error=str(exc),
        )


def _determine_local_action(state: LocalRepoState, force: bool) -> str:
    if state.error:
        return LOCAL_ACTION_FAILED
    if not state.remote_url:
        return LOCAL_ACTION_SKIP_NO_REMOTE
    if state.is_dirty and not force:
        return LOCAL_ACTION_SKIP_DIRTY
    return LOCAL_ACTION_PULL


def _summarize_local_results(results: List[LocalRepoResult]) -> Dict[str, int]:
    counts = {
        "total": len(results),
        "pulled": 0,
        "skipped_dirty": 0,
        "skipped_no_remote": 0,
        "failed": 0,
    }
    for result in results:
        if result.action in {LOCAL_ACTION_PULL, LOCAL_ACTION_PULLED}:
            counts["pulled"] += 1
        elif result.action == LOCAL_ACTION_SKIP_DIRTY:
            counts["skipped_dirty"] += 1
        elif result.action == LOCAL_ACTION_SKIP_NO_REMOTE:
            counts["skipped_no_remote"] += 1
        else:
            counts["failed"] += 1
    return counts


def _format_repo_display(root_path: Path, repo_path: Path) -> str:
    try:
        return str(repo_path.relative_to(root_path))
    except ValueError:
        return str(repo_path)


def _render_local_plan(
    root_path: Path, results: List[LocalRepoResult], force: bool
) -> None:
    table = Table(title="Local Sync Plan")
    table.add_column("Repository", style="cyan", overflow="fold")
    table.add_column("Provider", style="magenta")
    table.add_column("Action", style="green")
    table.add_column("Notes", style="dim")

    for result in results:
        state = result.state
        action_label = "Pull"
        notes = ""
        if result.action == LOCAL_ACTION_SKIP_DIRTY:
            action_label = "Skip"
            notes = "Dirty"
        elif result.action == LOCAL_ACTION_SKIP_NO_REMOTE:
            action_label = "Skip"
            notes = "No remote"
        elif result.action == LOCAL_ACTION_FAILED:
            action_label = "Error"
            notes = result.error or state.error or "Unknown error"
        elif force:
            notes = "Force clean"

        table.add_row(
            _format_repo_display(root_path, state.path),
            state.provider,
            action_label,
            notes,
        )

    console.print(table)


def _render_local_summary(results: List[LocalRepoResult], dry_run: bool) -> None:
    counts = _summarize_local_results(results)
    table = Table(title="Local Sync Summary")
    table.add_column("Result", style="bold")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Total", str(counts["total"]))
    table.add_row("Pull" if dry_run else "Pulled", str(counts["pulled"]))
    table.add_row("Skipped (dirty)", str(counts["skipped_dirty"]))
    table.add_row("Skipped (no remote)", str(counts["skipped_no_remote"]))
    table.add_row("Failed", str(counts["failed"]))

    console.print(table)


def _render_local_failures(results: List[LocalRepoResult], root_path: Path) -> None:
    failures = [result for result in results if result.action == LOCAL_ACTION_FAILED]
    if not failures:
        return

    table = Table(title="Local Sync Failures")
    table.add_column("Repository", style="red", overflow="fold")
    table.add_column("Error", style="yellow", overflow="fold")

    for result in failures:
        error_msg = result.error or result.state.error or "Unknown error"
        table.add_row(
            _format_repo_display(root_path, result.state.path),
            error_msg,
        )

    console.print(table)

async def resolve_repositories_for_sync(
    pattern: str,
    provider_manager,
    explicit_provider: Optional[str] = None,
    explicit_url: Optional[str] = None
) -> tuple[List[Repository], bool]:
    """
    Resolve repositories for sync operation with clear logging.

    Returns:
        Tuple of (repositories, is_multi_provider_operation)
    """
    from mgit.utils.pattern_matching import analyze_pattern
    
    pattern_analysis = analyze_pattern(pattern, explicit_provider, explicit_url)

    # Validate pattern
    if pattern_analysis.validation_errors:
        for error in pattern_analysis.validation_errors:
            console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1)

    logger.debug(f"Resolving repositories for sync pattern: {pattern}")

    try:
        if pattern_analysis.is_multi_provider:
            # Multi-provider search
            available_providers = list_provider_names()
            console.print(f"[blue]Synchronizing across {len(available_providers)} providers:[/blue] {', '.join(available_providers)}")

            if not available_providers:
                console.print("[red]Error:[/red] No providers configured. Run 'mgit login' to add providers.")
                raise typer.Exit(code=1)

            resolver = MultiProviderResolver()
            result = await resolver.resolve_repositories(
                project=pattern_analysis.normalized_pattern,
                provider_manager=None,
                config=None,
                url=None,
            )
            repositories = result.repositories

            # Log detailed results
            console.print(
                f"[green]Found {len(repositories)} repositories[/green] "
                f"from {len(result.successful_providers)} providers"
            )

            if result.failed_providers:
                console.print(
                    f"[yellow]Warning:[/yellow] Failed to query {len(result.failed_providers)} providers: "
                    f"{', '.join(result.failed_providers)}"
                )

            if result.duplicates_removed > 0:
                console.print(f"[blue]Info:[/blue] Removed {result.duplicates_removed} duplicate repositories")

            return repositories, True

        elif pattern_analysis.is_pattern:
            # Single provider pattern search
            provider_name = provider_manager.provider_name if provider_manager else None
            console.print(f"[blue]Synchronizing from provider:[/blue] {provider_name}")

            resolver = MultiProviderResolver()
            result = await resolver.resolve_repositories(
                project=pattern_analysis.normalized_pattern,
                provider_manager=provider_manager,
                config=provider_name,
                url=explicit_url,
            )
            repositories = result.repositories

            console.print(f"[green]Found {len(repositories)} repositories[/green] in provider '{provider_name}'")

            return repositories, False

        else:
            # Non-pattern query: use provider manager directly
            repositories = provider_manager.list_repositories(pattern)
            if hasattr(repositories, '__len__'):
                repo_list = list(repositories)
            else:
                repo_list = [repositories] if repositories else []

            console.print(f"[green]Found {len(repo_list)} repositories[/green] for exact match")

            return repo_list, False

    except Exception as e:
        logger.error(f"Error resolving repositories: {e}")
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

async def analyze_repository_states(repositories: List[Repository], target_path: Path):
    """Analyze current state of repositories in target path."""
    from dataclasses import dataclass

    @dataclass
    class RepoAnalysis:
        clean_repos: List[str]
        dirty_repos: List[str]
        missing_repos: List[str]
        non_git_dirs: List[str]

    clean_repos = []
    dirty_repos = []
    missing_repos = []
    non_git_dirs = []

    for repo in repositories:
        repo_path = build_repo_path(repo.clone_url)
        local_path = target_path / repo_path

        if not local_path.exists():
            missing_repos.append(repo.name)
        elif not (local_path / ".git").exists():
            non_git_dirs.append(repo.name)
        else:
            # Check if repo has uncommitted changes
            try:
                result = await asyncio.subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=local_path,
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    dirty_repos.append(repo.name)
                else:
                    clean_repos.append(repo.name)
            except Exception:
                # If git status fails, consider it dirty for safety
                dirty_repos.append(repo.name)

    return RepoAnalysis(clean_repos, dirty_repos, missing_repos, non_git_dirs)

async def show_sync_preview(repositories: List[Repository], target_path: Path, force: bool, detailed: bool):
    """Show detailed preview of sync operations."""
    repo_analysis = await analyze_repository_states(repositories, target_path)

    # Create summary table
    table = Table(title="Sync Preview")
    table.add_column("Repository", style="cyan", no_wrap=True)
    table.add_column("Current State", style="yellow")
    table.add_column("Planned Action", style="green")
    table.add_column("Notes", style="dim")

    for repo in repositories:
        repo_path = build_repo_path(repo.clone_url)
        local_path = target_path / repo_path
        repo_name = f"{repo_path.parts[-3]}/{repo_path.parts[-1]}"  # org/repo

        if repo.name in repo_analysis.missing_repos:
            table.add_row(repo_name, "Missing", "🔄 Clone", "New repository")
        elif repo.name in repo_analysis.non_git_dirs:
            table.add_row(repo_name, "Non-Git", "⚠️ Skip", "Directory exists but not git repo")
        elif repo.name in repo_analysis.dirty_repos:
            if force:
                table.add_row(repo_name, "Dirty", "🗑️ Force Clone", "Will delete local changes")
            else:
                table.add_row(repo_name, "Dirty", "⏭️ Skip", "Has uncommitted changes")
        else:  # clean repo
            if force:
                table.add_row(repo_name, "Clean", "🗑️ Force Clone", "Will re-clone fresh")
            else:
                table.add_row(repo_name, "Clean", "⬇️ Pull", "Update to latest")

    console.print(table)

    # Summary counts
    if detailed:
        summary_table = Table(title="Operation Summary")
        summary_table.add_column("Action", style="bold")
        summary_table.add_column("Count", justify="right", style="green")

        clone_count = len(repo_analysis.missing_repos) + (len(repositories) if force else 0)
        pull_count = len(repo_analysis.clean_repos) if not force else 0
        skip_count = len(repo_analysis.dirty_repos) + len(repo_analysis.non_git_dirs)
        if force:
            skip_count = len(repo_analysis.non_git_dirs)  # Only non-git dirs skipped in force mode

        summary_table.add_row("Clone", str(clone_count))
        summary_table.add_row("Pull", str(pull_count))
        summary_table.add_row("Skip", str(skip_count))

        console.print(summary_table)


async def _sync_local_repository(
    state: LocalRepoState, force: bool
) -> LocalRepoResult:
    action = _determine_local_action(state, force)
    if action != LOCAL_ACTION_PULL:
        return LocalRepoResult(state=state, action=action, error=state.error)

    if force:
        returncode, stdout, stderr = await _run_git_command(
            state.path, ["reset", "--hard"]
        )
        if returncode != 0:
            error_msg = stderr.strip() or stdout.strip() or "git reset --hard failed"
            return LocalRepoResult(
                state=state, action=LOCAL_ACTION_FAILED, error=error_msg
            )
        returncode, stdout, stderr = await _run_git_command(
            state.path, ["clean", "-fd"]
        )
        if returncode != 0:
            error_msg = stderr.strip() or stdout.strip() or "git clean -fd failed"
            return LocalRepoResult(
                state=state, action=LOCAL_ACTION_FAILED, error=error_msg
            )

    returncode, stdout, stderr = await _run_git_command(state.path, ["pull"])
    if returncode != 0:
        error_msg = stderr.strip() or stdout.strip() or "git pull failed"
        return LocalRepoResult(state=state, action=LOCAL_ACTION_FAILED, error=error_msg)

    return LocalRepoResult(state=state, action=LOCAL_ACTION_PULLED)


async def sync_local_command(
    root: str = ".",
    force: bool = False,
    concurrency: Optional[int] = None,
    dry_run: bool = False,
    progress: bool = True,
    summary: bool = True,
) -> None:
    """
    Synchronize repositories in a local directory tree by running git pull.
    """
    default_concurrency = int(get_global_setting("default_concurrency") or 4)
    if concurrency is None:
        concurrency = default_concurrency

    root_path = Path(root).expanduser().resolve()
    if not root_path.exists() or not root_path.is_dir():
        console.print(
            f"[red]Error:[/red] Local path '{root_path}' does not exist or is not a directory."
        )
        raise typer.Exit(code=1)

    repo_paths = sorted(find_repositories_in_directory(root_path, recursive=True))
    if not repo_paths:
        console.print(
            f"[yellow]No git repositories found under {root_path}[/yellow]"
        )
        return

    console.print(f"[blue]Local sync scan:[/blue] {root_path}")

    executor = AsyncExecutor(concurrency=concurrency, rich_console=console)

    async def inspect_repo(repo_path: Path) -> LocalRepoState:
        return await _inspect_local_repository(repo_path)

    repo_states, errors = await executor.run_batch(
        items=repo_paths,
        process_func=inspect_repo,
        task_description="Scanning local repositories...",
        show_progress=False,
    )
    repo_states = [state for state in repo_states if state]

    for repo_path, error in errors:
        repo_states.append(
            LocalRepoState(
                path=repo_path,
                name=repo_path.name,
                remote_url=None,
                provider="unknown",
                is_dirty=True,
                error=str(error),
            )
        )

    planned_results = [
        LocalRepoResult(
            state=state,
            action=_determine_local_action(state, force),
            error=state.error,
        )
        for state in repo_states
    ]

    if dry_run:
        _render_local_plan(root_path, planned_results, force)
        _render_local_summary(planned_results, dry_run=True)
        return

    if force:
        force_targets = [
            result for result in planned_results if result.action == LOCAL_ACTION_PULL
        ]
        if force_targets:
            confirmed = Confirm.ask(
                "[red]WARNING:[/red] Force mode will reset and clean "
                f"{len(force_targets)} repositories before pulling. Continue?"
            )
            if not confirmed:
                console.print("Sync cancelled.")
                return

    async def process_repo(state: LocalRepoState) -> LocalRepoResult:
        return await _sync_local_repository(state, force)

    results, errors = await executor.run_batch(
        items=repo_states,
        process_func=process_repo,
        task_description="Pulling local repositories...",
        item_description=lambda state: _format_repo_display(root_path, state.path),
        show_progress=progress,
    )
    results = [result for result in results if result]

    for repo_path, error in errors:
        results.append(
            LocalRepoResult(
                state=LocalRepoState(
                    path=repo_path,
                    name=repo_path.name,
                    remote_url=None,
                    provider="unknown",
                    is_dirty=True,
                    error=str(error),
                ),
                action=LOCAL_ACTION_FAILED,
                error=str(error),
            )
        )

    if summary:
        _render_local_summary(results, dry_run=False)

    _render_local_failures(results, root_path)

    if any(result.action == LOCAL_ACTION_FAILED for result in results):
        raise typer.Exit(code=1)

async def sync_command(
    pattern: str = typer.Argument(..., help="Repository pattern (org/project/repo)"),
    path: str = typer.Argument(".", help="Local path to synchronize repositories into"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Specific provider (otherwise search all)"),
    force: bool = typer.Option(False, "--force", "-f", help="Delete and re-clone all repositories"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c", help="Number of concurrent operations"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    progress: bool = typer.Option(True, "--progress/--no-progress", help="Show progress bar"),
    summary: bool = typer.Option(True, "--summary/--no-summary", help="Show detailed summary"),
) -> None:
    """
    Synchronize repositories with remote providers.

    🚀 UNIFIED REPOSITORY SYNC - replaces clone-all and pull-all

    Intelligently handles your repository synchronization:
    - Clones repositories that don't exist locally
    - Pulls updates for repositories that already exist and are clean
    - Skips repositories with uncommitted changes (unless --force)
    - Handles conflicts and errors gracefully
    - Provides detailed progress and summary reporting

    PATTERN can be:
    - Exact: myorg/myproject/myrepo
    - Wildcards: myorg/*/myrepo, */myproject/*, myorg/*/*
    - Cross-provider: */*/* (searches ALL providers)

    When no --provider specified, patterns search ALL configured providers.

    Examples:
        # Daily workspace sync
        mgit sync "myorg/*/*" ./workspace

        # Preview changes first
        mgit sync "myorg/*/*" ./workspace --dry-run

        # Nuclear option - fresh everything
        mgit sync "myorg/*/*" ./workspace --force

        # Quiet sync for scripts
        mgit sync "myorg/*/*" ./workspace --no-progress --no-summary
    """
    # Load configuration
    default_concurrency = int(get_global_setting("default_concurrency") or 4)
    if concurrency is None:
        concurrency = default_concurrency

    # Initialize managers
    git_manager = GitManager()

    # Setup provider manager
    if provider:
        provider_manager = ProviderManager(provider_name=provider)
    else:
        provider_manager = ProviderManager()  # Will be used for non-pattern queries only

    # Setup target path
    target_path = Path(path).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[blue]Synchronizing to:[/blue] {target_path}")

    # Resolve repositories
    repositories, is_multi_provider = await resolve_repositories_for_sync(pattern, provider_manager, provider, None)

    if not repositories:
        console.print(f"[yellow]No repositories found for pattern '{pattern}'[/yellow]")
        return

    # Analyze repositories before operation
    if not dry_run:
        repo_analysis = await analyze_repository_states(repositories, target_path)

        if repo_analysis.dirty_repos and not force:
            console.print("\n[yellow]⚠️  Repositories with uncommitted changes:[/yellow]")
            for repo_name in repo_analysis.dirty_repos:
                console.print(f"  • {repo_name}")
            console.print("\n[blue]These will be skipped. Use --force to override (will lose changes)[/blue]")

    # Enhanced dry run with repository analysis
    if dry_run:
        await show_sync_preview(repositories, target_path, force, summary)
        return

    # Determine update mode based on force flag
    update_mode = "force" if force else "pull"

    # Handle force confirmation
    if force:
        force_confirmed = Confirm.ask(
            f"[red]WARNING:[/red] Force mode will DELETE and re-clone {len(repositories)} repositories. "
            f"All local changes will be lost. Continue?"
        )
        if not force_confirmed:
            console.print("Sync cancelled.")
            return

    confirmed_force_remove = force
    dirs_to_remove = []  # Will be calculated by processor if needed

    # Create processor - use appropriate provider manager
    if is_multi_provider:
        # For multi-provider operations, let the processor handle individual repo URLs
        processor_provider_manager = ProviderManager()
    else:
        processor_provider_manager = provider_manager

    processor = BulkOperationProcessor(
        git_manager=git_manager,
        provider_manager=processor_provider_manager,
        operation_type=OperationType.clone,  # Sync uses clone operation type but with pull update mode
    )

    console.print(f"\n[blue]Synchronizing {len(repositories)} repositories...[/blue]")

    # Run sync with progress tracking
    if progress:
        await run_sync_with_progress(
            repositories, target_path, processor, concurrency, update_mode,
            confirmed_force_remove, dirs_to_remove
        )
    else:
        await run_sync_quiet(
            repositories, target_path, processor, concurrency, update_mode,
            confirmed_force_remove, dirs_to_remove
        )

async def run_sync_with_progress(repositories, target_path, processor, concurrency, update_mode, confirmed_force_remove, dirs_to_remove):
    """Run sync operation with rich progress reporting."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:

        # Add main progress task
        sync_task = progress.add_task("Synchronizing repositories...", total=len(repositories))

        # Custom callback to update progress
        async def progress_callback(completed: int, total: int, current_repo: str):
            progress.update(
                sync_task,
                completed=completed,
                description=f"Syncing: {current_repo}"
            )

        # Run sync with progress callback
        failures = await processor.process_repositories(
            repositories=repositories,
            target_path=target_path,
            concurrency=concurrency,
            update_mode=update_mode,
            confirmed_force_remove=confirmed_force_remove,
            dirs_to_remove=dirs_to_remove,
        )

    # Show final results
    success_count = len(repositories) - len(failures)

    if failures:
        console.print(f"\n[yellow]Sync completed with issues:[/yellow]")
        console.print(f"  [green]✅ Successful:[/green] {success_count}")
        console.print(f"  [red]❌ Failed:[/red] {len(failures)}")

        # Group failures by type for better reporting
        failure_table = Table(title="Failed Operations")
        failure_table.add_column("Repository", style="red")
        failure_table.add_column("Error", style="yellow")

        for failure in failures:
            # Parse failure string to extract repo name and error
            parts = str(failure).split(":", 1)
            repo_name = parts[0] if len(parts) > 0 else "Unknown"
            error_msg = parts[1].strip() if len(parts) > 1 else str(failure)
            failure_table.add_row(repo_name, error_msg)

        console.print(failure_table)
        raise typer.Exit(code=1)
    else:
        console.print(f"\n[green]✅ Successfully synchronized {success_count} repositories![/green]")

async def run_sync_quiet(repositories, target_path, processor, concurrency, update_mode, confirmed_force_remove, dirs_to_remove):
    """Run sync operation without progress reporting."""
    failures = await processor.process_repositories(
        repositories=repositories,
        target_path=target_path,
        concurrency=concurrency,
        update_mode=update_mode,
        confirmed_force_remove=confirmed_force_remove,
        dirs_to_remove=dirs_to_remove,
    )

    success_count = len(repositories) - len(failures)

    if failures:
        logger.error(f"Sync completed with {len(failures)} failures out of {len(repositories)} repositories")
        for failure in failures:
            logger.error(f"Failed: {failure}")
        raise typer.Exit(code=1)
    else:
        logger.info(f"Successfully synchronized {success_count} repositories")

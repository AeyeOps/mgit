"""Bulk repository operations for mgit.

Provides common logic for clone and pull operations across multiple repositories.
"""

import asyncio
import io
import logging
import shutil
import subprocess
from enum import Enum
from pathlib import Path

from rich.console import Console
from rich.progress import Progress
from rich.prompt import Confirm

from ..git import GitManager, resolve_local_repo_path, sanitize_url
from ..git.utils import classify_dirty_repo, find_case_collisions, parse_porcelain_z
from ..providers.base import Repository
from ..providers.manager import ProviderManager

logger = logging.getLogger(__name__)
console = Console()


class UpdateMode(str, Enum):
    """Update mode for existing folders."""

    skip = "skip"
    pull = "pull"
    force = "force"


class OperationType(str, Enum):
    """Type of bulk operation."""

    clone = "clone"
    pull = "pull"


class BulkOperationProcessor:
    """Handles bulk repository operations with progress tracking."""

    def __init__(
        self,
        git_manager: GitManager,
        provider_manager: ProviderManager,
        operation_type: OperationType,
        flat_layout: bool = True,
    ):
        self.git_manager = git_manager
        self.provider_manager = provider_manager
        self.operation_type = operation_type
        self.flat_layout = flat_layout
        self.failures: list[tuple[str, str]] = []
        self.skipped: list[tuple[str, str]] = []
        # Repos whose dirtiness is purely a case-collision checkout artifact;
        # force-synced to origin instead of pulled. Tracked separately so the
        # summary can report them distinctly from ordinary pulls.
        self.case_collision_repos: set[str] = set()
        self.case_collision_synced: list[str] = []

    async def process_repositories(
        self,
        repositories: list[Repository],
        target_path: Path,
        concurrency: int = 4,
        update_mode: UpdateMode = UpdateMode.skip,
        confirmed_force_remove: bool = False,
        dirs_to_remove: list[tuple[str, str, Path]] | None = None,
        show_progress: bool = True,
        resolved_names: dict[str, str] | None = None,
        case_collision_repos: set[str] | None = None,
    ) -> list[tuple[str, str]]:
        """
        Process repositories asynchronously with progress tracking.

        Args:
            repositories: List of repositories to process
            target_path: Target directory for operations
            concurrency: Number of concurrent operations
            update_mode: How to handle existing directories
            confirmed_force_remove: Whether user confirmed force removal
            dirs_to_remove: List of directories marked for removal in force mode
            show_progress: Whether to show progress bar
            resolved_names: Pre-resolved directory names for flat layout (handles collisions)
            case_collision_repos: Names of repos whose dirtiness is purely a
                case-collision checkout artifact — force-synced to origin
                (fetch + reset) instead of pulled, in pull update mode.

        Returns:
            List of (repo_name, error_reason) tuples for failed operations
        """
        self.failures = []
        self.skipped = []
        self.case_collision_repos = case_collision_repos or set()
        self.case_collision_synced = []
        sem = asyncio.Semaphore(concurrency)
        repo_tasks = {}

        progress_console = console
        if not show_progress:
            progress_console = Console(file=io.StringIO(), force_terminal=False)

        with Progress(console=progress_console) as progress:
            overall_task_id = progress.add_task(
                "[green]Processing Repositories...",
                total=len(repositories),
            )

            async def process_one_repo(repo: Repository):
                repo_name = repo.name
                repo_url = repo.clone_url
                is_disabled = repo.is_disabled
                display_name = (
                    repo_name[:30] + "..." if len(repo_name) > 30 else repo_name
                )

                # Add a task for this specific repo
                repo_task_id = progress.add_task(
                    f"[grey50]Pending: {display_name}[/grey50]", total=1, visible=True
                )
                repo_tasks[repo_name] = repo_task_id

                async with sem:
                    # Check if repository is disabled
                    if is_disabled:
                        logger.info(f"Skipping disabled repository: {repo_name}")
                        self.skipped.append((repo_name, "repository is disabled"))
                        progress.update(
                            repo_task_id,
                            description=f"[yellow]Disabled: {display_name}[/yellow]",
                            completed=1,
                        )
                        progress.advance(overall_task_id, 1)
                        return

                    # Determine repository folder path
                    repo_path = resolve_local_repo_path(
                        repo_url, self.flat_layout, resolved_names
                    )
                    logger.debug(
                        f"Using path '{repo_path}' for repository '{repo_name}'"
                    )

                    repo_folder = target_path / repo_path
                    # Handle existing directory
                    if repo_folder.exists():
                        handled = await self._handle_existing_directory(
                            repo=repo,
                            repo_folder=repo_folder,
                            update_mode=update_mode,
                            progress=progress,
                            repo_task_id=repo_task_id,
                            overall_task_id=overall_task_id,
                            display_name=display_name,
                            confirmed_force_remove=confirmed_force_remove,
                            dirs_to_remove=dirs_to_remove or [],
                        )
                        if handled:
                            return

                    # Perform the primary operation (clone or pull)
                    await self._perform_operation(
                        repo=repo,
                        repo_folder=repo_folder,
                        target_path=target_path,
                        repo_path=repo_path,
                        progress=progress,
                        repo_task_id=repo_task_id,
                        display_name=display_name,
                    )

                    progress.advance(overall_task_id, 1)

            # Process all repositories concurrently
            await asyncio.gather(*(process_one_repo(repo) for repo in repositories))

        return self.failures

    async def _handle_existing_directory(
        self,
        repo: Repository,
        repo_folder: Path,
        update_mode: UpdateMode,
        progress: Progress,
        repo_task_id: int,
        overall_task_id: int,
        display_name: str,
        confirmed_force_remove: bool,
        dirs_to_remove: list[tuple[str, str, Path]],
    ) -> bool:
        """
        Handle existing directory based on update mode.

        Returns:
            True if the operation should be skipped, False to continue
        """
        repo_name = repo.name
        sanitized_name = repo_folder.name

        if update_mode == UpdateMode.skip:
            logger.info(f"Skipping existing repo folder: {sanitized_name}")
            progress.update(
                repo_task_id,
                description=f"[blue]Skipped (exists): {display_name}[/blue]",
                completed=1,
            )
            progress.advance(overall_task_id, 1)
            return True

        elif update_mode == UpdateMode.pull:
            progress.update(
                repo_task_id,
                description=f"[cyan]Pulling: {display_name}...",
                visible=True,
            )
            if (repo_folder / ".git").exists():
                if await self.git_manager.is_repo_empty(repo_folder):
                    logger.info(f"Skipping empty repo (no commits): {repo_name}")
                    self.skipped.append((repo_name, "empty repo (no commits)"))
                    progress.update(
                        repo_task_id,
                        description=f"[yellow]Skipped (empty): {display_name}[/yellow]",
                        completed=1,
                    )
                elif repo_name in self.case_collision_repos:
                    await self._force_sync_case_collision(
                        repo_folder, repo_name, progress, repo_task_id, display_name
                    )
                else:
                    try:
                        await self.git_manager.git_pull(repo_folder)
                        progress.update(
                            repo_task_id,
                            description=f"[green]Pulled (update): {display_name}[/green]",
                            completed=1,
                        )
                    except subprocess.CalledProcessError as e:
                        error_detail = sanitize_url(
                            (e.stderr or "").strip().split("\n")[0]
                        )
                        logger.warning(f"Pull failed for {repo_name}: {error_detail}")
                        self.failures.append(
                            (repo_name, f"pull failed: {error_detail}")
                        )
                        progress.update(
                            repo_task_id,
                            description=f"[red]Pull Failed (update): {display_name}[/red]",
                            completed=1,
                        )
            else:
                if not any(repo_folder.iterdir()):
                    logger.info(f"Removing empty non-git directory: {repo_folder}")
                    repo_folder.rmdir()
                    return False
                else:
                    msg = "dir exists, not a git repo"
                    logger.warning(f"{repo_name}: {msg}")
                    self.skipped.append((repo_name, msg))
                    progress.update(
                        repo_task_id,
                        description=f"[yellow]Skipped (not repo): {display_name}[/yellow]",
                        completed=1,
                    )
            progress.advance(overall_task_id, 1)
            return True

        elif update_mode == UpdateMode.force:
            # Check if removal was confirmed AND this dir was marked
            should_remove = confirmed_force_remove and any(
                rf == repo_folder for _, _, rf in dirs_to_remove
            )
            if should_remove:
                progress.update(
                    repo_task_id,
                    description=f"[magenta]Removing: {display_name}...",
                    visible=True,
                )
                logger.info(f"Removing existing folder: {sanitized_name}")
                try:
                    shutil.rmtree(repo_folder)
                    # Removal successful, continue to clone
                    return False
                except Exception as e:
                    self.failures.append(
                        (repo_name, f"Failed removing old folder: {e}")
                    )
                    progress.update(
                        repo_task_id,
                        description=f"[red]Remove Failed: {display_name}[/red]",
                        completed=1,
                    )
                    progress.advance(overall_task_id, 1)
                    return True
            else:
                logger.warning(
                    f"Skipping removal of existing folder (not confirmed): {sanitized_name}"
                )
                progress.update(
                    repo_task_id,
                    description=f"[blue]Skipped (force declined/not applicable): {display_name}[/blue]",
                    completed=1,
                )
                progress.advance(overall_task_id, 1)
                return True

        return False

    async def _is_pure_case_collision(self, repo_folder: Path) -> bool:
        """True if the repo is dirty solely because of case-colliding paths.

        Re-checked at sync time because the classification done during analysis
        can be stale: every changed path must also be a case-colliding tracked
        path, meaning there is no real local work that ``git reset --hard``
        would lose.
        """
        proc = await asyncio.create_subprocess_exec(
            "git",
            "status",
            "--porcelain",
            "-z",
            cwd=str(repo_folder),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return False
        dirty_paths = parse_porcelain_z(stdout.decode("utf-8", errors="ignore"))
        collisions = find_case_collisions(repo_folder)
        return classify_dirty_repo(dirty_paths, collisions) == "case_collision"

    async def _force_sync_case_collision(
        self,
        repo_folder: Path,
        repo_name: str,
        progress: Progress,
        repo_task_id: int,
        display_name: str,
    ) -> None:
        """Bring a case-collision repo current with origin via fetch + reset.

        A verified case-collision repo has no real local changes — every dirty
        path is a case-colliding tracked path the filesystem cannot represent.
        That makes ``git reset --hard`` safe: it only discards the unavoidable
        checkout artifact, which reappears on checkout anyway. The repo is
        re-verified first, so one that gained genuine edits since analysis is
        skipped rather than reset.
        """
        progress.update(
            repo_task_id,
            description=f"[cyan]Syncing (case-collision): {display_name}...",
            visible=True,
        )
        if not await self._is_pure_case_collision(repo_folder):
            msg = "case-colliding paths plus genuine local edits"
            logger.warning(f"Skipping force-sync for {repo_name}: {msg}")
            self.skipped.append((repo_name, msg))
            progress.update(
                repo_task_id,
                description=f"[yellow]Skipped (local edits): {display_name}[/yellow]",
                completed=1,
            )
            return
        try:
            await self.git_manager.git_fetch(repo_folder)
            upstream = await self.git_manager.get_upstream_ref(repo_folder)
            if upstream:
                await self.git_manager.git_reset_hard(repo_folder, upstream)
            else:
                # No upstream branch to reset to — fetch still advanced the
                # repo's history, the best that can be done without one.
                logger.info(f"{repo_name}: no upstream branch; fetched without reset")
            self.case_collision_synced.append(repo_name)
            progress.update(
                repo_task_id,
                description=f"[green]Synced (case-collision): {display_name}[/green]",
                completed=1,
            )
        except subprocess.CalledProcessError as e:
            error_detail = sanitize_url((e.stderr or "").strip().split("\n")[0])
            logger.warning(
                f"Case-collision sync failed for {repo_name}: {error_detail}"
            )
            self.failures.append(
                (repo_name, f"case-collision sync failed: {error_detail}")
            )
            progress.update(
                repo_task_id,
                description=f"[red]Sync Failed: {display_name}[/red]",
                completed=1,
            )

    async def _perform_operation(
        self,
        repo: Repository,
        repo_folder: Path,
        target_path: Path,
        repo_path: Path,
        progress: Progress,
        repo_task_id: int,
        display_name: str,
    ):
        """Perform the primary operation (clone or pull)."""
        repo_name = repo.name

        if self.operation_type == OperationType.clone:
            progress.update(
                repo_task_id,
                description=f"[cyan]Cloning: {display_name}...",
                visible=True,
            )
            # Get authenticated URL from provider manager
            pat_url = self.provider_manager.get_authenticated_clone_url(repo)
            try:
                # Ensure parent directories exist
                repo_folder.parent.mkdir(parents=True, exist_ok=True)
                await self.git_manager.git_clone(
                    pat_url, repo_folder.parent, repo_folder.name
                )
                progress.update(
                    repo_task_id,
                    description=f"[green]Cloned: {display_name}[/green]",
                    completed=1,
                )
            except subprocess.CalledProcessError as e:
                error_detail = sanitize_url((e.stderr or "").strip().split("\n")[0])
                logger.warning(f"Clone failed for {repo_name}: {error_detail}")
                self.failures.append((repo_name, f"clone failed: {error_detail}"))
                progress.update(
                    repo_task_id,
                    description=f"[red]Clone Failed: {display_name}[/red]",
                    completed=1,
                )

        elif self.operation_type == OperationType.pull:
            if repo_folder.exists() and (repo_folder / ".git").exists():
                if await self.git_manager.is_repo_empty(repo_folder):
                    logger.info(f"Skipping empty repo (no commits): {repo_name}")
                    self.skipped.append((repo_name, "empty repo (no commits)"))
                    progress.update(
                        repo_task_id,
                        description=f"[yellow]Skipped (empty): {display_name}[/yellow]",
                        completed=1,
                    )
                else:
                    progress.update(
                        repo_task_id,
                        description=f"[cyan]Pulling: {display_name}...",
                        visible=True,
                    )
                    try:
                        await self.git_manager.git_pull(repo_folder)
                        progress.update(
                            repo_task_id,
                            description=f"[green]Pulled: {display_name}[/green]",
                            completed=1,
                        )
                    except subprocess.CalledProcessError as e:
                        error_detail = sanitize_url(
                            (e.stderr or "").strip().split("\n")[0]
                        )
                        logger.warning(f"Pull failed for {repo_name}: {error_detail}")
                        self.failures.append(
                            (repo_name, f"pull failed: {error_detail}")
                        )
                        progress.update(
                            repo_task_id,
                            description=f"[red]Pull Failed: {display_name}[/red]",
                            completed=1,
                        )
            else:
                progress.update(
                    repo_task_id,
                    description=f"[yellow]Skipped (not found): {display_name}[/yellow]",
                    completed=1,
                )


def check_force_mode_confirmation(
    repositories: list[Repository],
    target_path: Path,
    update_mode: UpdateMode,
    flat_layout: bool = True,
    resolved_names: dict[str, str] | None = None,
) -> tuple[bool, list[tuple[str, str, Path]]]:
    """
    Check for existing directories in force mode and get user confirmation.

    Args:
        repositories: List of repositories to check
        target_path: Target directory for operations
        update_mode: Current update mode
        flat_layout: If True, use flat directory layout
        resolved_names: Pre-resolved names for collision handling in flat mode

    Returns:
        Tuple of (confirmed, dirs_to_remove)
    """
    dirs_to_remove = []
    confirmed_force_remove = False

    if update_mode == UpdateMode.force:
        logger.debug("Checking for existing directories to remove (force mode)...")
        for repo in repositories:
            repo_path = resolve_local_repo_path(
                repo.clone_url, flat_layout, resolved_names
            )
            repo_folder = target_path / repo_path
            if repo_folder.exists():
                dirs_to_remove.append((repo.name, str(repo_path), repo_folder))

        if dirs_to_remove:
            console.print(
                "[bold yellow]Force mode selected. The following existing directories will be REMOVED:[/bold yellow]"
            )
            for _, s_name, _ in dirs_to_remove:
                console.print(f" - {s_name}")
            if Confirm.ask(
                "Proceed with removing these directories and cloning fresh?",
                default=False,
            ):
                confirmed_force_remove = True
                logger.info("User confirmed removal of existing directories.")
            else:
                logger.warning(
                    "User declined removal. Force mode aborted for existing directories."
                )

    return confirmed_force_remove, dirs_to_remove

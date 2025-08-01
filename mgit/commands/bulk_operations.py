"""Bulk repository operations for mgit.

Provides common logic for clone and pull operations across multiple repositories.
"""

import asyncio
import logging
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console
from rich.progress import Progress
from rich.prompt import Confirm

from ..git import GitManager, build_repo_path
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
    ):
        self.git_manager = git_manager
        self.provider_manager = provider_manager
        self.operation_type = operation_type
        self.failures: List[Tuple[str, str]] = []

    async def process_repositories(
        self,
        repositories: List[Repository],
        target_path: Path,
        concurrency: int = 4,
        update_mode: UpdateMode = UpdateMode.skip,
        confirmed_force_remove: bool = False,
        dirs_to_remove: Optional[List[Tuple[str, str, Path]]] = None,
    ) -> List[Tuple[str, str]]:
        """
        Process repositories asynchronously with progress tracking.

        Args:
            repositories: List of repositories to process
            target_path: Target directory for operations
            concurrency: Number of concurrent operations
            update_mode: How to handle existing directories
            confirmed_force_remove: Whether user confirmed force removal
            dirs_to_remove: List of directories marked for removal in force mode

        Returns:
            List of (repo_name, error_reason) tuples for failed operations
        """
        self.failures = []
        sem = asyncio.Semaphore(concurrency)
        repo_tasks = {}

        with Progress() as progress:
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
                        self.failures.append((repo_name, "repository is disabled"))
                        progress.update(
                            repo_task_id,
                            description=f"[yellow]Disabled: {display_name}[/yellow]",
                            completed=1,
                        )
                        progress.advance(overall_task_id, 1)
                        return

                    # Determine repository folder path
                    repo_path = build_repo_path(repo_url)
                    logger.debug(f"Using path '{repo_path}' for repository '{repo_name}'")

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
        dirs_to_remove: List[Tuple[str, str, Path]],
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
                # Attempt to pull
                try:
                    await self.git_manager.git_pull(repo_folder)
                    progress.update(
                        repo_task_id,
                        description=f"[green]Pulled (update): {display_name}[/green]",
                        completed=1,
                    )
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Pull failed for {repo_name}: {e}")
                    self.failures.append((repo_name, "pull failed"))
                    progress.update(
                        repo_task_id,
                        description=f"[red]Pull Failed (update): {display_name}[/red]",
                        completed=1,
                    )
            else:
                msg = "Folder exists but is not a git repo."
                logger.warning(f"{repo_name}: {msg}")
                self.failures.append((repo_name, msg))
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
                await self.git_manager.git_clone(pat_url, repo_folder.parent, repo_folder.name)
                progress.update(
                    repo_task_id,
                    description=f"[green]Cloned: {display_name}[/green]",
                    completed=1,
                )
            except subprocess.CalledProcessError as e:
                logger.warning(f"Clone failed for {repo_name}: {e}")
                self.failures.append((repo_name, "clone failed"))
                progress.update(
                    repo_task_id,
                    description=f"[red]Clone Failed: {display_name}[/red]",
                    completed=1,
                )

        elif self.operation_type == OperationType.pull:
            if repo_folder.exists() and (repo_folder / ".git").exists():
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
                    logger.warning(f"Pull failed for {repo_name}: {e}")
                    self.failures.append((repo_name, "pull failed"))
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
    repositories: List[Repository],
    target_path: Path,
    update_mode: UpdateMode,
) -> Tuple[bool, List[Tuple[str, str, Path]]]:
    """
    Check for existing directories in force mode and get user confirmation.

    Returns:
        Tuple of (confirmed, dirs_to_remove)
    """
    dirs_to_remove = []
    confirmed_force_remove = False

    if update_mode == UpdateMode.force:
        logger.debug("Checking for existing directories to remove (force mode)...")
        for repo in repositories:
            repo_url = repo.clone_url
            repo_path = build_repo_path(repo_url)
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

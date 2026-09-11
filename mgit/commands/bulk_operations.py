"""Bulk repository operations for mgit.

Provides common logic for clone and pull operations across multiple repositories.
"""

import asyncio
import contextlib
import logging
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import Literal

from rich.console import Console
from rich.prompt import Confirm

from ..git import GitManager, resolve_local_repo_path, sanitize_url
from ..git.progress import GitProgress, ProgressCallback
from ..git.utils import classify_dirty_repo, find_case_collisions, parse_porcelain_z
from ..providers.base import Repository
from ..providers.manager import ProviderManager
from ..ui.sync_progress import SyncProgress

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
        # Clone URLs of repos whose dirtiness is purely a case-collision
        # checkout artifact; force-synced to origin instead of pulled. Tracked
        # separately so the summary can report them distinctly from ordinary
        # pulls.
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
        display: SyncProgress | None = None,
    ) -> list[tuple[str, str]]:
        """Process repositories and report actual work to one status display.

        An optional caller-owned display includes repositories skipped during
        preflight. Otherwise this processor owns the display for its batch.
        """
        self.failures = []
        self.skipped = []
        self.case_collision_repos = case_collision_repos or set()
        self.case_collision_synced = []
        sem = asyncio.Semaphore(concurrency)
        display_context = (
            contextlib.nullcontext(display)
            if display is not None
            else SyncProgress(
                len(repositories), phase="Syncing", disable=not show_progress
            )
        )

        with display_context as panel:

            async def process_one_repo(repo: Repository) -> None:
                async with sem:
                    repo_path = resolve_local_repo_path(
                        repo.clone_url, self.flat_layout, resolved_names
                    )
                    display_path = str(repo_path)
                    key = repo.clone_url
                    panel.start_repository(key, display_path, "Checking repository")

                    def report(event: GitProgress) -> None:
                        panel.update_repository(key, event)

                    on_progress = report if not panel.disable else None
                    try:
                        if repo.is_disabled:
                            self.skipped.append(
                                (display_path, "repository is disabled")
                            )
                            outcome = "skipped"
                        else:
                            repo_folder = target_path / repo_path
                            outcome = None
                            if repo_folder.exists():
                                outcome = await self._handle_existing_directory(
                                    repo,
                                    repo_folder,
                                    update_mode,
                                    display_path,
                                    confirmed_force_remove,
                                    dirs_to_remove or [],
                                    on_progress,
                                )
                            if outcome is None:
                                outcome = await self._perform_operation(
                                    repo, repo_folder, display_path, on_progress
                                )
                    except Exception:
                        panel.finish_repository(key, "failed")
                        raise
                    panel.finish_repository(key, outcome)

            tasks = [
                asyncio.create_task(process_one_repo(repo)) for repo in repositories
            ]
            try:
                await asyncio.gather(*tasks)
            finally:
                # All work belongs to this batch, including on callback failure.
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

        return self.failures

    async def _handle_existing_directory(
        self,
        repo: Repository,
        repo_folder: Path,
        update_mode: UpdateMode,
        display_path: str,
        confirmed_force_remove: bool,
        dirs_to_remove: list[tuple[str, str, Path]],
        on_progress: ProgressCallback | None,
    ) -> Literal["success", "skipped", "failed"] | None:
        """Return an outcome, or None when a fresh clone should follow."""
        if update_mode == UpdateMode.skip:
            self.skipped.append((display_path, "already exists"))
            return "skipped"

        if update_mode == UpdateMode.pull:
            if (repo_folder / ".git").exists():
                if await self.git_manager.is_repo_empty(repo_folder):
                    self.skipped.append((display_path, "empty repo (no commits)"))
                    return "skipped"
                if repo.clone_url in self.case_collision_repos:
                    return await self._force_sync_case_collision(
                        repo_folder, repo.name, display_path, on_progress
                    )
                return await self._pull_repository(
                    repo_folder, display_path, on_progress
                )
            if not any(repo_folder.iterdir()):
                repo_folder.rmdir()
                return None
            self.skipped.append((display_path, "dir exists, not a git repo"))
            return "skipped"

        if update_mode == UpdateMode.force:
            should_remove = confirmed_force_remove and any(
                folder == repo_folder for _, _, folder in dirs_to_remove
            )
            if not should_remove:
                self.skipped.append((display_path, "removal not confirmed"))
                return "skipped"
            if on_progress is not None:
                on_progress(GitProgress("Removing existing directory"))
            try:
                shutil.rmtree(repo_folder)
            except OSError as error:
                self.failures.append(
                    (display_path, f"Failed removing old folder: {error}")
                )
                return "failed"
            return None

        raise ValueError(f"Unsupported update mode: {update_mode}")

    async def _is_pure_case_collision(self, repo_folder: Path) -> bool:
        """Recheck that every dirty path is a case-collision checkout artifact."""
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
        collisions = await asyncio.to_thread(find_case_collisions, repo_folder)
        return classify_dirty_repo(dirty_paths, collisions) == "case_collision"

    async def _force_sync_case_collision(
        self,
        repo_folder: Path,
        repo_name: str,
        display_path: str,
        on_progress: ProgressCallback | None = None,
    ) -> Literal["success", "skipped", "failed"]:
        """Fetch/reset only after rechecking that no genuine edits would be lost."""
        if not await self._is_pure_case_collision(repo_folder):
            self.skipped.append(
                (display_path, "case-colliding paths plus genuine local edits")
            )
            return "skipped"
        try:
            await self.git_manager.git_fetch(repo_folder, on_progress=on_progress)
            upstream = await self.git_manager.get_upstream_ref(repo_folder)
            if upstream:
                if on_progress is not None:
                    on_progress(GitProgress("Updating checkout"))
                await self.git_manager.git_reset_hard(repo_folder, upstream)
            else:
                logger.info("%s: no upstream branch; fetched without reset", repo_name)
            self.case_collision_synced.append(display_path)
            return "success"
        except subprocess.CalledProcessError as error:
            self._record_failure(display_path, "case-collision sync", error)
            return "failed"

    def _record_failure(
        self, display_path: str, operation: str, error: subprocess.CalledProcessError
    ) -> None:
        # Progress records may precede the actual fatal message in captured stderr.
        # Keep the diagnostic, with credentials removed, for the final report.
        detail = sanitize_url((error.stderr or error.stdout or str(error)).strip())
        self.failures.append((display_path, f"{operation} failed: {detail}"))
        logger.debug("%s failed for %s: %s", operation, display_path, detail)

    async def _pull_repository(
        self, repo_folder: Path, display_path: str, on_progress: ProgressCallback | None
    ) -> Literal["success", "failed"]:
        try:
            await self.git_manager.git_pull(repo_folder, on_progress=on_progress)
            return "success"
        except subprocess.CalledProcessError as error:
            self._record_failure(display_path, "pull", error)
            return "failed"

    async def _perform_operation(
        self,
        repo: Repository,
        repo_folder: Path,
        display_path: str,
        on_progress: ProgressCallback | None,
    ) -> Literal["success", "skipped", "failed"]:
        """Clone or pull one repository, retaining a complete outcome tally."""
        if self.operation_type == OperationType.clone:
            pat_url = self.provider_manager.get_authenticated_clone_url(repo)
            try:
                repo_folder.parent.mkdir(parents=True, exist_ok=True)
                await self.git_manager.git_clone(
                    pat_url,
                    repo_folder.parent,
                    repo_folder.name,
                    on_progress=on_progress,
                )
                return "success"
            except subprocess.CalledProcessError as error:
                self._record_failure(display_path, "clone", error)
                return "failed"
        if self.operation_type == OperationType.pull:
            if not repo_folder.exists() or not (repo_folder / ".git").exists():
                self.skipped.append((display_path, "repository not found"))
                return "skipped"
            if await self.git_manager.is_repo_empty(repo_folder):
                self.skipped.append((display_path, "empty repo (no commits)"))
                return "skipped"
            return await self._pull_repository(repo_folder, display_path, on_progress)
        raise ValueError(f"Unsupported operation: {self.operation_type}")


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

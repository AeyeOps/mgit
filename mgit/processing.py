"""Core processing classes for mgit operations."""

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from mgit.content.embedding import (
    ContentEmbeddingEngine,
    ContentStrategy,
    EmbeddingConfig,
)
from mgit.git.manager import GitManager

logger = logging.getLogger(__name__)


@dataclass
class RepositoryChange:
    """Represents change information for a single repository."""

    repository_path: str
    repository_name: str
    timestamp: str
    has_uncommitted_changes: bool
    uncommitted_files: list[dict[str, Any]]
    recent_commits: list[dict[str, Any]]
    current_branch: str | None
    git_status: str
    error: str | None = None


class DiffProcessor:
    """Processes repositories to detect and collect change information."""

    def __init__(
        self,
        concurrency: int = 5,
        embed_content: bool = False,
        content_strategy: ContentStrategy = ContentStrategy.SAMPLE,
        content_memory_mb: int = 100,
    ):
        self.git_manager = GitManager()
        self.concurrency = concurrency
        self.embed_content = embed_content
        self.content_strategy = content_strategy
        self.content_memory_mb = content_memory_mb

        # Initialize content embedding engine if needed
        self.content_engine = None
        if embed_content:
            config = EmbeddingConfig(
                default_strategy=content_strategy, max_total_memory_mb=content_memory_mb
            )
            self.content_engine = ContentEmbeddingEngine(config)

    async def process_repositories(
        self,
        repositories: list[Path],
        progress: Any | None = None,
        task_id: Any | None = None,
    ) -> list[RepositoryChange]:
        """
        Process multiple repositories concurrently to detect changes.
        """
        semaphore = asyncio.Semaphore(self.concurrency)

        async def process_single_repo(repo_path: Path) -> RepositoryChange:
            async with semaphore:
                try:
                    change_data = await self._detect_repository_changes(repo_path)
                    if progress and task_id:
                        progress.advance(task_id)
                    return change_data
                except Exception as e:
                    logger.error(f"Error processing repository {repo_path}: {e}")
                    if progress and task_id:
                        progress.advance(task_id)
                    return RepositoryChange(
                        repository_path=str(repo_path),
                        repository_name=repo_path.name,
                        timestamp=datetime.now().isoformat(),
                        has_uncommitted_changes=False,
                        uncommitted_files=[],
                        recent_commits=[],
                        current_branch=None,
                        git_status="error",
                        error=str(e),
                    )

        tasks = [process_single_repo(repo) for repo in repositories]
        return await asyncio.gather(*tasks)

    async def _detect_repository_changes(self, repo_path: Path) -> RepositoryChange:
        """
        Detect changes in a single repository.
        """
        timestamp = datetime.now().isoformat()

        try:
            current_branch = await self.git_manager.get_current_branch(repo_path)
            diff_info = await self.git_manager.diff_files(repo_path)
            has_changes = diff_info.get("has_changes", False)

            uncommitted_files = []
            if has_changes:
                status_output = diff_info.get("status_output", "")
                uncommitted_files = self._parse_git_status(status_output, repo_path)

            recent_commits = await self._get_recent_commits(repo_path, limit=5)

            return RepositoryChange(
                repository_path=str(repo_path),
                repository_name=repo_path.name,
                timestamp=timestamp,
                has_uncommitted_changes=has_changes,
                uncommitted_files=uncommitted_files,
                recent_commits=recent_commits,
                current_branch=current_branch,
                git_status="clean" if not has_changes else "dirty",
                error=None,
            )

        except Exception as e:
            logger.debug(f"Repository {repo_path} change detection failed: {e}")
            return RepositoryChange(
                repository_path=str(repo_path),
                repository_name=repo_path.name,
                timestamp=timestamp,
                has_uncommitted_changes=False,
                uncommitted_files=[],
                recent_commits=[],
                current_branch=None,
                git_status="error",
                error=str(e),
            )

    def _parse_git_status(
        self, status_output: str, repo_path: Path
    ) -> list[dict[str, Any]]:
        """
        Parse git status output into structured file change information.
        """
        files = []
        for line in status_output.strip().split("\n"):
            if not line:
                continue

            if len(line) >= 3:
                index_status = line[0]
                worktree_status = line[1]
                filename = line[2:].lstrip()

                file_info = {
                    "filename": filename,
                    "index_status": index_status,
                    "worktree_status": worktree_status,
                    "change_type": self._interpret_git_status_codes(
                        index_status, worktree_status
                    ),
                }

                if self.embed_content and self.content_engine:
                    try:
                        file_path = repo_path / filename
                        if file_path.exists():
                            embedded_content = self.content_engine.embed_file_content(
                                file_path
                            )
                            file_info["embedded_content"] = asdict(embedded_content)
                    except Exception as e:
                        logger.debug(f"Failed to embed content for {filename}: {e}")
                        file_info["embedded_content"] = {"error": str(e)}

                files.append(file_info)

        return files

    def _interpret_git_status_codes(self, index: str, worktree: str) -> str:
        """Interpret git status codes into human-readable change types."""
        if index == "A":
            return "added"
        if index == "M":
            return "modified"
        if index == "D":
            return "deleted"
        if index == "R":
            return "renamed"
        if index == "C":
            return "copied"
        if worktree == "M":
            return "modified"
        if worktree == "D":
            return "deleted"
        if index == "?" and worktree == "?":
            return "untracked"
        return "unknown"

    async def _get_recent_commits(
        self, repo_path: Path, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Get recent commit information from the repository.
        """
        try:
            return await self.git_manager.get_recent_commits(repo_path, limit)
        except Exception as e:
            logger.debug(f"Could not get recent commits for {repo_path}: {e}")
            return []

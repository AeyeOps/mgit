"""Git operations manager for mgit CLI tool."""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GitManager:
    GIT_EXECUTABLE = "git"

    # Fix type hint for dir_name
    async def git_clone(
        self, repo_url: str, output_dir: Path, dir_name: Optional[str] = None
    ):
        """
        Use 'git clone' for the given repo_url, in output_dir.
        Optionally specify a directory name to clone into.
        Raises typer.Exit if the command fails.
        """
        # Format the message for better display in the console
        # Truncate long URLs to prevent log line truncation
        display_url = repo_url
        if len(display_url) > 60:
            parsed = urlparse(display_url)
            path_parts = parsed.path.split("/")
            if len(path_parts) > 2:
                # Show just the end of the path (organization/project/repo)
                short_path = "/".join(path_parts[-3:])
                display_url = f"{parsed.scheme}://{parsed.netloc}/.../{short_path}"

        if dir_name:
            display_dir = dir_name
            if len(display_dir) > 40:
                display_dir = display_dir[:37] + "..."

            logger.info(f"Cloning: [bold blue]{display_dir}[/bold blue]")
            cmd = [self.GIT_EXECUTABLE, "clone", repo_url, dir_name]
        else:
            logger.info(f"Cloning repository: {display_url} into {output_dir}")
            cmd = [self.GIT_EXECUTABLE, "clone", repo_url]

        await self._run_subprocess(cmd, cwd=output_dir)

    async def git_pull(self, repo_dir: Path):
        """
        Use 'git pull' for the existing repo in repo_dir.
        """
        # Extract repo name from path for nicer logging
        repo_name = repo_dir.name

        # Format the output with consistent width to prevent truncation
        # Limit the repo name to 40 characters if it's longer
        display_name = repo_name
        if len(display_name) > 40:
            display_name = display_name[:37] + "..."

        logger.info(f"Pulling: [bold green]{display_name}[/bold green]")
        cmd = [self.GIT_EXECUTABLE, "pull"]
        await self._run_subprocess(cmd, cwd=repo_dir)

    async def get_current_branch(self, repo_dir: Path) -> Optional[str]:
        """
        Get the current branch name for the repository.

        Args:
            repo_dir: Path to the repository

        Returns:
            Current branch name or None if detached HEAD or error
        """
        try:
            cmd = [self.GIT_EXECUTABLE, "branch", "--show-current"]
            result = await self._run_subprocess(cmd, cwd=repo_dir, capture_output=True)

            branch_name = result.stdout.strip()
            return branch_name if branch_name else None

        except subprocess.CalledProcessError:
            logger.debug(f"Could not get current branch for {repo_dir}")
            return None
        except Exception as e:
            logger.debug(f"Get current branch failed in {repo_dir}: {e}")
            return None

    async def get_recent_commits(
        self, repo_dir: Path, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get recent commit information from the repository.

        Args:
            repo_dir: Path to repository
            limit: Maximum number of commits to return

        Returns:
            List of commit information dictionaries
        """
        try:
            # Use git log with custom format for structured output
            format_str = "--format=%H|%an|%ae|%ai|%s"
            cmd = [self.GIT_EXECUTABLE, "log", f"-{limit}", format_str, "--no-merges"]

            result = await self._run_subprocess(cmd, cwd=repo_dir, capture_output=True)

            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|", 4)
                    if len(parts) == 5:
                        commits.append(
                            {
                                "hash": parts[0],
                                "author_name": parts[1],
                                "author_email": parts[2],
                                "date": parts[3],
                                "message": parts[4],
                            }
                        )

            return commits

        except subprocess.CalledProcessError as e:
            logger.debug(f"Git log failed in {repo_dir}: {e}")
            return []
        except Exception as e:
            logger.debug(f"Get recent commits failed in {repo_dir}: {e}")
            return []

    async def diff_files(self, repo_dir: Path) -> Dict[str, Any]:
        """
        Get diff information for a repository including git status.

        Args:
            repo_dir: Path to the repository

        Returns:
            Dictionary with diff information including:
            - has_changes: bool indicating if there are uncommitted changes
            - status_output: raw git status --porcelain output
            - diff_output: raw git diff output (optional)
        """
        try:
            # Check for uncommitted changes using git status
            status_cmd = [self.GIT_EXECUTABLE, "status", "--porcelain"]
            status_result = await self._run_subprocess(
                status_cmd, cwd=repo_dir, capture_output=True
            )

            status_output = status_result.stdout.strip()
            has_changes = len(status_output) > 0

            return {
                "has_changes": has_changes,
                "status_output": status_output,
            }

        except subprocess.CalledProcessError as e:
            logger.debug(f"Git status failed in {repo_dir}: {e}")
            raise
        except Exception as e:
            logger.debug(f"Diff files operation failed in {repo_dir}: {e}")
            raise

    async def _run_subprocess(
        self, cmd: list, cwd: Path, capture_output: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Run a subprocess command with proper error handling.

        Args:
            cmd: Command and arguments to run
            cwd: Working directory for the command
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess result if capture_output=True
        """
        try:
            if capture_output:
                result = subprocess.run(
                    cmd, cwd=cwd, capture_output=True, text=True, check=True
                )
                return result
            else:
                # Original behavior for non-capturing calls
                subprocess.run(cmd, cwd=cwd, check=True)
                return None

        except subprocess.CalledProcessError as e:
            # Log the error with context
            cmd_str = " ".join(cmd)
            logger.error(f"Command '{cmd_str}' failed in {cwd}: {e}")
            if capture_output and e.stdout:
                logger.debug(f"stdout: {e.stdout}")
            if capture_output and e.stderr:
                logger.debug(f"stderr: {e.stderr}")
            raise
        except Exception as e:
            cmd_str = " ".join(cmd)
            logger.error(f"Unexpected error running '{cmd_str}' in {cwd}: {e}")
            raise

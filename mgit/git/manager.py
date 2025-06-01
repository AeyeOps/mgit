"""Git operations manager for mgit CLI tool."""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional
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

    @staticmethod
    async def _run_subprocess(cmd: list, cwd: Path):
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if stdout:
            for line in stdout.decode().splitlines():
                logger.debug(f"[stdout] {line}")
        if stderr:
            for line in stderr.decode().splitlines():
                logger.debug(f"[stderr] {line}")
        if process.returncode != 0:
            # Ensure returncode is an int for CalledProcessError
            return_code = process.returncode
            if return_code is None:
                # This case should ideally not happen after communicate()
                logger.error(
                    f"Command '{' '.join(cmd)}' finished but return code is None. Assuming error."
                )
                return_code = 1  # Assign a default error code

            logger.error(
                f"Command '{' '.join(cmd)}' failed " f"with return code {return_code}."
            )
            # Raise the specific error for the caller to handle
            # Ensure stderr is bytes if stdout is bytes for CalledProcessError
            stderr_bytes = (
                stderr
                if isinstance(stderr, bytes)
                else stderr.encode("utf-8", errors="replace")
            )
            raise subprocess.CalledProcessError(
                return_code, cmd, output=stdout, stderr=stderr_bytes
            )

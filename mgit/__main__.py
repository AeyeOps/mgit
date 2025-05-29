#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess # Needed for CalledProcessError exception
import sys
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse, urlunparse, unquote

from dotenv import dotenv_values, load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress
from rich.prompt import Confirm # Added import
import typer

# Azure DevOps SDK imports
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.git import GitClient, GitRepository
from azure.devops.v7_1.core import CoreClient, TeamProjectReference
from azure.devops.exceptions import ClientRequestError, AzureDevOpsAuthenticationError

# Local imports - Sprint 3A integrations
from mgit.git import GitManager, embed_pat_in_url, sanitize_repo_name
from mgit.utils import AsyncExecutor
from mgit.providers.manager import ProviderManager
from mgit.exceptions import (
    MgitError,
    ConfigurationError,
    AuthenticationError,
    ConnectionError,
    RepositoryOperationError,
    ProjectNotFoundError,
    OrganizationNotFoundError,
    ValidationError,
    FileSystemError,
    CLIError,
    error_handler,
    async_error_handler,
    retry_with_backoff,
    error_context,
    validate_url,
    validate_path,
)
from mgit.providers import (
    GitProvider,
    ProviderFactory,
    ProviderError,
    RateLimitError,
    ProviderNotFoundError,
    RepositoryNotFoundError,
    PermissionError,
    APIError,
)
from mgit.providers.manager import ProviderManager
from mgit.legacy.azdevops_manager import AzDevOpsManager

__version__ = "0.2.1"

# Default values used if environment variables and config file don't provide values
DEFAULT_VALUES = {
    "AZURE_DEVOPS_ORG_URL": "https://www.visualstudio.com",
    "LOG_FILENAME": "mgit.log",
    "LOG_LEVEL": "DEBUG",
    "CON_LEVEL": "INFO",
    "DEFAULT_CONCURRENCY": "4",
    "DEFAULT_UPDATE_MODE": "skip",
}

# Configuration loading order:
# 1. Environment variables (highest priority)
# 2. Global config file in ~/.config/mgit/config
# 3. Default values (lowest priority)

# First load environment variables
load_dotenv(
    dotenv_path=None,
    verbose=True,
    override=True,
)

# Load global config file if environment variables are not set
CONFIG_DIR = Path.home() / ".config" / "mgit"
CONFIG_FILE = CONFIG_DIR / "config"
# Ensure config directory exists before setting up file logging
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Fix type hint for default_value
def get_config_value(key: str, default_value: Optional[str] = None) -> str:
    """
    Get a configuration value with the following priority:
    1. Environment variable
    2. Global config file
    3. Default value
    """
    # First check environment
    env_value = os.environ.get(key)
    if env_value:
        return env_value

    # Then check config file
    if CONFIG_FILE.exists():
        config_values = dotenv_values(dotenv_path=str(CONFIG_FILE))
        if key in config_values and config_values[key]:
            return config_values[key]

    # Finally use default
    return default_value or DEFAULT_VALUES.get(key, "")

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------


class MgitFormatter(logging.Formatter):
    """Formatter that removes PAT from the URL in logs."""

    def __init__(
        self,
        fmt=None,
        datefmt=None,
        style="%",
        validate=True,
    ):
        if fmt is None:
            fmt = "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
        super().__init__(
            fmt=fmt,
            datefmt=datefmt,
            style=style,
            validate=validate,
        )

    @staticmethod
    def _remove_pat(msg: str) -> str:
        pat = os.getenv("AZURE_DEVOPS_EXT_PAT")
        if not pat:
            return msg

        if "https://ado:" in msg:
            # Remove the PAT from the URL
            msg = msg.replace(
                "ado:" + pat,
                "ado:***",
            )
        elif "https://PersonalAccessToken:" in msg:
            # Remove the PAT from the URL
            msg = msg.replace(
                "https://PersonalAccessToken:" + pat,
                "https://PersonalAccessToken:***",
            )
        return msg

    def format(self, record):
        # Update the record so that %(message)s uses the filtered text
        record.msg = self._remove_pat(record.getMessage())
        record.args = None
        return super().format(record)


# Use an absolute path within the config directory for the log file
log_filename = CONFIG_DIR / get_config_value("LOG_FILENAME")
file_handler = RotatingFileHandler(
    log_filename, # Use the absolute path
    maxBytes=5_000_000,
    backupCount=3,
)

file_handler.setFormatter(MgitFormatter())

class ConsoleFriendlyRichHandler(RichHandler):
    """Enhanced Rich handler that formats long messages better for console display."""

    def emit(self, record):
        # Format repository URLs in a more readable way
        if record.levelname == "INFO":
            msg = str(record.msg)

            # Handle repository cloning messages
            if "Cloning repository:" in msg:
                # Extract repository name from URL
                if "_git/" in msg:
                    try:
                        # Extract repo name from URL pattern
                        repo_name = msg.split("_git/")[1].split(" into")[0]
                        # Truncate long repo names
                        if len(repo_name) > 40:
                            repo_name = repo_name[:37] + "..."
                        # Format message to be more concise
                        shortened_url = f"Cloning: [bold blue]{repo_name}[/bold blue]"
                        record.msg = shortened_url
                    except Exception:
                        # If parsing fails, keep original message
                        pass

            # Handle skipping disabled repositories message
            elif "Skipping disabled repository:" in msg:
                try:
                    repo_name = msg.split("Skipping disabled repository:")[1].strip()
                    # Truncate long repo names
                    if len(repo_name) > 40:
                        repo_name = repo_name[:37] + "..."
                    record.msg = f"Skipping disabled: [bold yellow]{repo_name}[/bold yellow]"
                except Exception:
                    pass

        # Call the parent class's emit method
        super().emit(record)

console_handler = ConsoleFriendlyRichHandler(
    rich_tracebacks=True,
    markup=True,
    show_path=False,  # Hide the file path in log messages
    show_time=False,  # Hide timestamp (already in the formatter)
)
console_handler.setLevel(
    get_config_value("CON_LEVEL")
)

logger = logging.getLogger(__name__)
logger.setLevel(
    get_config_value("LOG_LEVEL")
)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

console = Console()
app = typer.Typer(
    name="mgit",
    help=f"Multi-Git CLI Tool v{__version__} - A utility for managing repositories across " # Updated version will be picked up here automatically
    "multiple git platforms (Azure DevOps, GitHub, BitBucket) with bulk operations.",
    add_completion=False,
    no_args_is_help=True,
)

def version_callback(value: bool):
    if value:
        print(f"mgit version: {__version__}") # Updated version will be picked up here automatically
        raise typer.Exit()

@app.callback()
def main_options(
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True,
        help="Show the application's version and exit."
    )
):
    """
    Multi-Git CLI Tool - Manage repos across multiple git platforms easily.
    """
    pass


# -----------------------------------------------------------------------------
# Helper functions (moved to modules in Sprint 3A)
# -----------------------------------------------------------------------------
# embed_pat_in_url and sanitize_repo_name moved to mgit.git.utils


# -----------------------------------------------------------------------------
# Azure DevOps Manager - moved to mgit.legacy.azdevops_manager
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Git Manager
# -----------------------------------------------------------------------------
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
            path_parts = parsed.path.split('/')
            if len(path_parts) > 2:
                # Show just the end of the path (organization/project/repo)
                short_path = '/'.join(path_parts[-3:])
                display_url = f"{parsed.scheme}://{parsed.netloc}/.../{short_path}"

        if dir_name:
            display_dir = dir_name
            if len(display_dir) > 40:
                display_dir = display_dir[:37] + "..."

            logger.info(
                f"Cloning: [bold blue]{display_dir}[/bold blue]"
            )
            cmd = [self.GIT_EXECUTABLE, "clone", repo_url, dir_name]
        else:
            logger.info(
                f"Cloning repository: {display_url} into {output_dir}"
            )
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
                logger.error(f"Command '{' '.join(cmd)}' finished but return code is None. Assuming error.")
                return_code = 1 # Assign a default error code

            logger.error(
                f"Command '{' '.join(cmd)}' failed "
                f"with return code {return_code}."
            )
            # Raise the specific error for the caller to handle
            # Ensure stderr is bytes if stdout is bytes for CalledProcessError
            stderr_bytes = stderr if isinstance(stderr, bytes) else stderr.encode('utf-8', errors='replace')
            raise subprocess.CalledProcessError(return_code, cmd, output=stdout, stderr=stderr_bytes)


class UpdateMode(str, Enum):
    skip = "skip"
    pull = "pull"
    force = "force"


@app.command()
def clone_all(
    project: str = typer.Argument(
        ..., help="Project name (DevOps project, GitHub org/user, or BitBucket workspace)."
    ),
    rel_path: str = typer.Argument(
        ..., help="Relative path to clone into."
    ),
    url: Optional[str] = typer.Argument(
        None,
        help="Organization URL (auto-detects provider if provided, "
        f"defaults to {DEFAULT_VALUES['AZURE_DEVOPS_ORG_URL']} for backward compatibility).",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="Git provider (azuredevops, github, bitbucket). Auto-detected from URL if not specified.",
    ),
    concurrency: int = typer.Option(
        int(get_config_value("DEFAULT_CONCURRENCY", "4")),
        "--concurrency",
        "-c",
        help="Number of concurrent clone operations.",
    ),
    update_mode: UpdateMode = typer.Option(
        get_config_value("DEFAULT_UPDATE_MODE", "skip"),
        "--update-mode",
        "-u",
        help=(
            "How to handle existing folders: "
            "'skip' => do nothing if folder exists, "
            "'pull' => attempt a 'git pull' if it's a valid repo, "
            "'force' => remove the folder and clone fresh."
        ),
    ),
):
    """
    Clone all repositories from a git provider project/organization.
    
    Supports Azure DevOps, GitHub, and BitBucket providers.
    Provider is auto-detected from URL or can be specified explicitly.
    """

    # Initialize provider manager with provider selection
    try:
        # Auto-detect or use explicit provider
        if provider:
            provider_manager = ProviderManager(provider_type=provider)
        elif url:
            provider_manager = ProviderManager(auto_detect_url=url)
        else:
            # Default to Azure DevOps for backward compatibility
            provider_manager = ProviderManager(provider_type="azuredevops")
            
        logger.debug(f"Using provider: {provider_manager.provider_type}")
        
        # Check if provider is supported
        if not provider_manager.supports_provider():
            logger.error(
                f"Provider {provider_manager.provider_type} is not fully implemented yet. "
                "Fully supported: Azure DevOps. In development: GitHub, BitBucket"
            )
            raise typer.Exit(code=1)
            
        # Test connection
        if not provider_manager.test_connection():
            logger.error(
                f"Failed to connect or authenticate to {provider_manager.provider_type}. "
                "Please check your configuration and credentials."
            )
            raise typer.Exit(code=1)
            
    except Exception as e:
        logger.error(f"Provider initialization failed: {e}")
        raise typer.Exit(code=1)
        
    git_manager = GitManager()


    # Prepare local folder
    target_path = Path.cwd() / rel_path
    target_path.mkdir(parents=True, exist_ok=True)

    # List repositories using provider manager
    logger.debug(f"Fetching repository list for project: {project}...")
    try:
        repositories = provider_manager.list_repositories(project)
        logger.info(f"Found {len(repositories)} repositories in project '{project}'.")
    except Exception as e:
        logger.error(f"Error fetching repository list: {e}")
        raise typer.Exit(code=1)

    if not repositories:
        logger.info(f"No repositories found in project '{project}'.")
        return # Exit gracefully if no repos

    failures = []
    confirmed_force_remove = False # Flag to track user confirmation

    # --- Pre-check for force mode ---
    dirs_to_remove = []
    if update_mode == UpdateMode.force:
        logger.debug("Checking for existing directories to remove (force mode)...")
        for repo in repositories:
            repo_url = repo.clone_url
            sanitized_name = sanitize_repo_name(repo_url)
            repo_folder = target_path / sanitized_name
            if repo_folder.exists():
                dirs_to_remove.append((repo.name, sanitized_name, repo_folder))

        if dirs_to_remove:
            console.print("[bold yellow]Force mode selected. The following existing directories will be REMOVED:[/bold yellow]")
            for _, s_name, _ in dirs_to_remove:
                console.print(f" - {s_name}")
            if Confirm.ask("Proceed with removing these directories and cloning fresh?", default=False):
                confirmed_force_remove = True
                logger.info("User confirmed removal of existing directories.")
            else:
                logger.warning("User declined removal. Force mode aborted for existing directories.")
                # Optionally, switch mode or just let the tasks skip later
                # For simplicity, we'll let the tasks handle skipping based on confirmed_force_remove flag
    # --- End Pre-check ---


    async def do_clones():
        """
        Process repos asynchronously with a concurrency
        limit and a progress bar. lso embed the PAT in the remote URL.
        Handle each repo's failure gracefully, storing it in 'failures'.
        """
        sem = asyncio.Semaphore(concurrency)

        # Keep track of individual repo tasks
        repo_tasks = {}

        with Progress() as progress:
            overall_task_id = progress.add_task(
                "[green]Processing Repositories...",
                total=len(repositories),
            )

            async def process_one_repo(repo): # repo is now a Repository object
                repo_name = repo.name
                repo_url = repo.clone_url # Use clone_url from Repository object
                is_disabled = repo.is_disabled # Use is_disabled attribute
                display_name = repo_name[:30] + "..." if len(repo_name) > 30 else repo_name

                # Add a task for this specific repo early
                repo_task_id = progress.add_task(f"[grey50]Pending: {display_name}[/grey50]", total=1, visible=True)
                repo_tasks[repo_name] = repo_task_id

                async with sem:
                    # Check if repository is disabled
                    if is_disabled:
                        logger.info(f"Skipping disabled repository: {repo_name}")
                        failures.append((repo_name, "repository is disabled"))
                        progress.update(repo_task_id, description=f"[yellow]Disabled: {display_name}[/yellow]", completed=1)
                        progress.advance(overall_task_id, 1)
                        return

                    # Sanitize the repository name for filesystem use
                    # Use the actual repo name for the folder, sanitize the URL for logging/cloning if needed
                    # but the folder name should match the repo name ideally.
                    # Let's use the sanitized name based on the URL for consistency with previous behavior.
                    sanitized_name = sanitize_repo_name(repo_url)
                    if sanitized_name != repo_name:
                         logger.debug(
                             f"Using sanitized name '{sanitized_name}' for repository '{repo_name}' folder"
                         )

                    repo_folder = target_path / sanitized_name
                    # Decide how to handle if folder already exists
                    if repo_folder.exists():
                        if update_mode == UpdateMode.skip:
                            logger.info(f"Skipping existing repo folder: {sanitized_name}")
                            progress.update(repo_task_id, description=f"[blue]Skipped (exists): {display_name}[/blue]", completed=1)
                            progress.advance(overall_task_id, 1)
                            return
                        elif update_mode == UpdateMode.pull:
                            progress.update(repo_task_id, description=f"[cyan]Pulling: {display_name}...", visible=True)
                            if (
                                repo_folder / ".git"
                            ).exists():
                                # Attempt to do a pull
                                try:
                                    await git_manager.git_pull(repo_folder)
                                    progress.update(repo_task_id, description=f"[green]Pulled (update): {display_name}[/green]", completed=1)
                                except subprocess.CalledProcessError as e:
                                    logger.warning(f"Pull failed for {repo_name}: {e}")
                                    failures.append((repo_name, "pull failed"))
                                    progress.update(repo_task_id, description=f"[red]Pull Failed (update): {display_name}[/red]", completed=1)
                            else:
                                msg = "Folder exists but is not a git repo."
                                logger.warning(f"{repo_name}: {msg}")
                                failures.append((repo_name, msg))
                                progress.update(repo_task_id, description=f"[yellow]Skipped (not repo): {display_name}[/yellow]", completed=1)
                            progress.advance(overall_task_id, 1)
                            return
                        elif update_mode == UpdateMode.force:
                            # Check if removal was confirmed AND this dir was marked
                            should_remove = confirmed_force_remove and any(rf == repo_folder for _, _, rf in dirs_to_remove)
                            if should_remove:
                                progress.update(repo_task_id, description=f"[magenta]Removing: {display_name}...", visible=True)
                                logger.info(f"Removing existing folder: {sanitized_name}")
                                try:
                                    shutil.rmtree(repo_folder)
                                    # Removal successful, fall through to clone
                                except Exception as e:
                                    failures.append((repo_name, f"Failed removing old folder: {e}"))
                                    progress.update(repo_task_id, description=f"[red]Remove Failed: {display_name}[/red]", completed=1)
                                    progress.advance(overall_task_id, 1)
                                    return
                            else:
                                # Either user declined or this specific folder wasn't marked (shouldn't happen with current logic, but safe check)
                                logger.warning(f"Skipping removal of existing folder (not confirmed): {sanitized_name}")
                                progress.update(repo_task_id, description=f"[blue]Skipped (force declined/not applicable): {display_name}[/blue]", completed=1)
                                progress.advance(overall_task_id, 1)
                                return
                    # If we made it here:
                    # - Folder didn't exist OR
                    # - Force mode was confirmed AND removal succeeded
                    progress.update(repo_task_id, description=f"[cyan]Cloning: {display_name}...", visible=True)
                    # Get PAT from provider manager for URL embedding
                    if provider_manager.provider_type == "azuredevops":
                        legacy_manager = provider_manager.get_legacy_manager()
                        pat_url = embed_pat_in_url(repo_url, legacy_manager.ado_pat) if legacy_manager else repo_url
                    else:
                        # For other providers, use the clone URL as-is (PAT should be in config)
                        pat_url = repo_url
                    try:
                        # Use the sanitized name for the directory argument
                        await git_manager.git_clone(pat_url, target_path, sanitized_name)
                        progress.update(repo_task_id, description=f"[green]Cloned: {display_name}[/green]", completed=1)
                    except subprocess.CalledProcessError as e:
                        # Use the sanitized name for the directory argument
                        await git_manager.git_clone(pat_url, target_path, sanitized_name)
                        progress.update(repo_task_id, description=f"[green]Cloned: {display_name}[/green]", completed=1)
                    except subprocess.CalledProcessError as e:
                        logger.warning(f"Clone failed for {repo_name}: {e}")
                        failures.append((repo_name, "clone failed"))
                        progress.update(repo_task_id, description=f"[red]Clone Failed: {display_name}[/red]", completed=1)

                    progress.advance(overall_task_id, 1)

            # Iterate through the Repository objects from provider manager
            await asyncio.gather(*(process_one_repo(repo) for repo in repositories))

    logger.info(
        "Processing all repositories for project: "
        "%s into '%s' with update_mode='%s'",
        project,
        target_path,
        update_mode,
    )
    asyncio.run(do_clones())

    # Summarize
    if failures:
        logger.warning("Some repositories had issues:")
        for repo_name, reason in failures:
            logger.warning(f" - {repo_name}: {reason}")
    else:
        logger.info(
            "All repositories processed successfully with no errors."
        )


# -----------------------------------------------------------------------------
# pull_all Command
# -----------------------------------------------------------------------------
@app.command()
def pull_all(
    project: str = typer.Argument(
        ..., help="Project name (DevOps project, GitHub org/user, or BitBucket workspace)."
    ),
    rel_path: str = typer.Argument(
        ..., help="Relative path where repositories exist."
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="Git provider (azuredevops, github, bitbucket). Defaults to azuredevops for backward compatibility.",
    ),
    concurrency: int = typer.Option(
        int(get_config_value("DEFAULT_CONCURRENCY", "4")),
        "--concurrency",
        "-c",
        help="Number of concurrent pull operations.",
    ),
    update_mode: UpdateMode = typer.Option(
        get_config_value("DEFAULT_UPDATE_MODE", "skip"),
        "--update-mode",
        "-u",
        help=(
            "How to handle existing folders: "
            "'skip' => do nothing if folder exists, "
            "'pull' => attempt a 'git pull' if it's a valid repo, "
            "'force' => remove the folder and clone fresh."
        ),
    ),
):
    """
    Pull the latest changes for all repositories in the specified path.
    
    Supports Azure DevOps, GitHub, and BitBucket providers.
    Provider is auto-detected from URL or can be specified explicitly.
    """

    # Initialize provider manager with provider selection
    try:
        # Use explicit provider
        provider_manager = ProviderManager(provider_type=provider or "azuredevops")
            
        logger.debug(f"Using provider: {provider_manager.provider_type}")
        
        # Check if provider is supported
        if not provider_manager.supports_provider():
            logger.error(
                f"Provider {provider_manager.provider_type} is not fully implemented yet. "
                "Fully supported: Azure DevOps. In development: GitHub, BitBucket"
            )
            raise typer.Exit(code=1)
            
        # Test connection
        if not provider_manager.test_connection():
            logger.error(
                f"Failed to connect or authenticate to {provider_manager.provider_type}. "
                "Please check your configuration and credentials."
            )
            raise typer.Exit(code=1)
            
    except Exception as e:
        logger.error(f"Provider initialization failed: {e}")
        raise typer.Exit(code=1)
        
    git_manager = GitManager()

    # Prepare local folder
    target_path = Path.cwd() / rel_path
    if not target_path.exists():
        if update_mode == UpdateMode.force:
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            logger.error(f"Target path does not exist: {target_path}")
            raise typer.Exit(code=1)
    elif not target_path.is_dir():
        logger.error(f"Target path is not a directory: {target_path}")
        raise typer.Exit(code=1)

    # List repositories using provider manager
    logger.debug(f"Fetching repository list for project: {project}...")
    try:
        repositories = provider_manager.list_repositories(project)
        logger.info(f"Found {len(repositories)} repositories in project '{project}'.")
    except Exception as e:
        logger.error(f"Error fetching repository list: {e}")
        raise typer.Exit(code=1)

    if not repositories:
        logger.info(f"No repositories found in project '{project}'.")
        return # Exit gracefully if no repos

    failures = []
    confirmed_force_remove = False # Flag to track user confirmation

    # --- Pre-check for force mode ---
    dirs_to_remove = []
    if update_mode == UpdateMode.force:
        logger.debug("Checking for existing directories to remove (force mode)...")
        for repo in repositories:
            repo_url = repo.clone_url
            sanitized_name = sanitize_repo_name(repo_url)
            repo_folder = target_path / sanitized_name
            if repo_folder.exists():
                dirs_to_remove.append((repo.name, sanitized_name, repo_folder))

        if dirs_to_remove:
            console.print("[bold yellow]Force mode selected. The following existing directories will be REMOVED:[/bold yellow]")
            for _, s_name, _ in dirs_to_remove:
                console.print(f" - {s_name}")
            if Confirm.ask("Proceed with removing these directories and cloning fresh?", default=False):
                confirmed_force_remove = True
                logger.info("User confirmed removal of existing directories.")
            else:
                logger.warning("User declined removal. Force mode aborted for existing directories.")
                # Optionally, switch mode or just let the tasks skip later
                # For simplicity, we'll let the tasks handle skipping based on confirmed_force_remove flag
    # --- End Pre-check ---

    async def do_operations():
        """
        Process repos asynchronously with a concurrency
        limit and a progress bar. Also embed the PAT in the remote URL.
        Handle each repo's failure gracefully, storing it in 'failures'.
        """
        sem = asyncio.Semaphore(concurrency)

        # Keep track of individual repo tasks
        repo_tasks = {}

        with Progress() as progress:
            overall_task_id = progress.add_task(
                "[green]Processing Repositories...",
                total=len(repositories),
            )

            async def process_one_repo(repo): # repo is now a Repository object
                repo_name = repo.name
                repo_url = repo.clone_url # Use clone_url from Repository object
                is_disabled = repo.is_disabled # Use is_disabled attribute
                display_name = repo_name[:30] + "..." if len(repo_name) > 30 else repo_name

                # Add a task for this specific repo early
                repo_task_id = progress.add_task(f"[grey50]Pending: {display_name}[/grey50]", total=1, visible=True)
                repo_tasks[repo_name] = repo_task_id

                async with sem:
                    # Check if repository is disabled
                    if is_disabled:
                        logger.info(f"Skipping disabled repository: {repo_name}")
                        failures.append((repo_name, "repository is disabled"))
                        progress.update(repo_task_id, description=f"[yellow]Disabled: {display_name}[/yellow]", completed=1)
                        progress.advance(overall_task_id, 1)
                        return

                    # Sanitize the repository name for filesystem use
                    # Use the actual repo name for the folder, sanitize the URL for logging/cloning if needed
                    # but the folder name should match the repo name ideally.
                    # Let's use the sanitized name based on the URL for consistency with previous behavior.
                    sanitized_name = sanitize_repo_name(repo_url)
                    if sanitized_name != repo_name:
                         logger.debug(
                             f"Using sanitized name '{sanitized_name}' for repository '{repo_name}' folder"
                         )

                    repo_folder = target_path / sanitized_name
                    # Decide how to handle if folder already exists
                    if repo_folder.exists():
                        if update_mode == UpdateMode.skip:
                            logger.info(f"Skipping existing repo folder: {sanitized_name}")
                            progress.update(repo_task_id, description=f"[blue]Skipped (exists): {display_name}[/blue]", completed=1)
                            progress.advance(overall_task_id, 1)
                            return
                        elif update_mode == UpdateMode.pull:
                            progress.update(repo_task_id, description=f"[cyan]Pulling: {display_name}...", visible=True)
                            if (
                                repo_folder / ".git"
                            ).exists():
                                # Attempt to do a pull
                                try:
                                    await git_manager.git_pull(repo_folder)
                                    progress.update(repo_task_id, description=f"[green]Pulled (update): {display_name}[/green]", completed=1)
                                except subprocess.CalledProcessError as e:
                                    logger.warning(f"Pull failed for {repo_name}: {e}")
                                    failures.append((repo_name, "pull failed"))
                                    progress.update(repo_task_id, description=f"[red]Pull Failed (update): {display_name}[/red]", completed=1)
                            else:
                                msg = "Folder exists but is not a git repo."
                                logger.warning(f"{repo_name}: {msg}")
                                failures.append((repo_name, msg))
                                progress.update(repo_task_id, description=f"[yellow]Skipped (not repo): {display_name}[/yellow]", completed=1)
                            progress.advance(overall_task_id, 1)
                            return
                        elif update_mode == UpdateMode.force:
                            # Check if removal was confirmed AND this dir was marked
                            should_remove = confirmed_force_remove and any(rf == repo_folder for _, _, rf in dirs_to_remove)
                            if should_remove:
                                progress.update(repo_task_id, description=f"[magenta]Removing: {display_name}...", visible=True)
                                logger.info(f"Removing existing folder: {sanitized_name}")
                                try:
                                    shutil.rmtree(repo_folder)
                                    # Removal successful, fall through to clone
                                except Exception as e:
                                    failures.append((repo_name, f"Failed removing old folder: {e}"))
                                    progress.update(repo_task_id, description=f"[red]Remove Failed: {display_name}[/red]", completed=1)
                                    progress.advance(overall_task_id, 1)
                                    return
                            else:
                                # Either user declined or this specific folder wasn't marked (shouldn't happen with current logic, but safe check)
                                logger.warning(f"Skipping removal of existing folder (not confirmed): {sanitized_name}")
                                progress.update(repo_task_id, description=f"[blue]Skipped (force declined/not applicable): {display_name}[/blue]", completed=1)
                                progress.advance(overall_task_id, 1)
                                return
                    # If we made it here:
                    # - Folder didn't exist OR
                    # - Force mode was confirmed AND removal succeeded
                    progress.update(repo_task_id, description=f"[cyan]Cloning: {display_name}...", visible=True)
                    # Get PAT from provider manager for URL embedding
                    if provider_manager.provider_type == "azuredevops":
                        legacy_manager = provider_manager.get_legacy_manager()
                        pat_url = embed_pat_in_url(repo_url, legacy_manager.ado_pat) if legacy_manager else repo_url
                    else:
                        # For other providers, use the clone URL as-is (PAT should be in config)
                        pat_url = repo_url
                    try:
                        # Use the sanitized name for the directory argument
                        await git_manager.git_clone(pat_url, target_path, sanitized_name)
                        progress.update(repo_task_id, description=f"[green]Cloned: {display_name}[/green]", completed=1)
                    except subprocess.CalledProcessError as e:
                        logger.warning(f"Clone failed for {repo_name}: {e}")
                        failures.append((repo_name, "clone failed"))
                        progress.update(repo_task_id, description=f"[red]Clone Failed: {display_name}[/red]", completed=1)

                    progress.advance(overall_task_id, 1)

            # Iterate through the Repository objects from provider manager
            await asyncio.gather(*(process_one_repo(repo) for repo in repositories))

    logger.info(
        "Processing all repositories for project: "
        "%s into '%s' with update_mode='%s'",
        project,
        target_path,
        update_mode,
    )
    asyncio.run(do_operations())

    # Summarize
    if failures:
        logger.warning("Some repositories had issues:")
        for repo_name, reason in failures:
            logger.warning(f" - {repo_name}: {reason}")
    else:
        logger.info(
            "All repositories processed successfully with no errors."
        )


# -----------------------------------------------------------------------------
# generate_env Command
# -----------------------------------------------------------------------------
@app.command(help="Generate a sample environment file with configuration options for multiple git providers.")
def generate_env():
    """
    Generate a detailed sample environment file with all configuration options.

    This command creates a .env.sample file with example values and detailed
    comments explaining each configuration option. Users can copy this file
    to .env to set local environment variables.
    """
    env_content = """# Multi-Git CLI Configuration Sample
# Copy this file to .env to configure environment variables
# Or use ~/.config/mgit/config for global settings

# ===== Provider Configuration =====
# mgit supports multiple git providers: Azure DevOps, GitHub, and BitBucket

# Azure DevOps Configuration
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-org
AZURE_DEVOPS_EXT_PAT=<YOUR_AZURE_PAT>

# GitHub Configuration
GITHUB_ORG_URL=https://github.com/your-org
GITHUB_PAT=<YOUR_GITHUB_PAT>

# BitBucket Configuration
BITBUCKET_ORG_URL=https://bitbucket.org/your-workspace
BITBUCKET_APP_PASSWORD=<YOUR_BITBUCKET_APP_PASSWORD>

# ===== Default Settings =====

# Log file name (default: mgit.log)
LOG_FILENAME=mgit.log

# Logging level for file logs (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=DEBUG

# Logging level for console output (DEBUG, INFO, WARNING, ERROR)
CON_LEVEL=INFO

# Default concurrency for repository operations (default: 4)
# Higher values speed up cloning multiple repositories but increase resource usage
DEFAULT_CONCURRENCY=4

# Default update mode when repositories already exist:
# - skip: Don't touch existing repositories
# - pull: Try to git pull if it's a valid git repository
# - force: Remove existing folder and clone fresh
DEFAULT_UPDATE_MODE=skip

# Default provider (azuredevops, github, bitbucket)
DEFAULT_PROVIDER=azuredevops
"""

    counter = 0
    new_file = Path(".env.sample")
    while new_file.exists():
        counter += 1
        new_file = Path(f".env.sample{counter}")

    with new_file.open("w", encoding="utf-8") as wf:
        wf.write(env_content)

    console.print(f"[green]✓[/green] Created {new_file} with detailed configuration options.")

# For backward compatibility
@app.command(hidden=True)
def gen_env():
    """Alias for generate_env command (deprecated)."""
    generate_env()


# -----------------------------------------------------------------------------
# login Command
# -----------------------------------------------------------------------------
@app.command(help="Login to git provider and validate credentials. Supports Azure DevOps, GitHub, and BitBucket.")
def login(
    provider: Optional[str] = typer.Option(
        "azuredevops", "--provider", "-p", help="Git provider (azuredevops, github, bitbucket)."
    ),
    organization: Optional[str] = typer.Option(
        None, "--org", "-o", help="Provider organization/workspace URL (optional, uses config/env if not provided)."
    ),
    token: Optional[str] = typer.Option(
        None, "--token", "-t", help="Access token (PAT/API token, optional, uses config/env if not provided)."
    ),
    store: bool = typer.Option(
        False, # Default to False for explicit login command
        "--store/--no-store",
        help="Store provided credentials in global config file (~/.config/mgit/config)."
    )
):
    """
    Validate git provider credentials and optionally store them.

    Tests connection using credentials from arguments, environment variables,
    or global config file. If --store is used, saves the provided
    (or discovered) credentials to the global config.
    """
    # Create provider manager for selected provider
    provider_config = {}
    if organization:
        provider_config["organization_url"] = organization
    if token:
        provider_config["pat"] = token
    
    provider_manager = ProviderManager(
        provider_type=provider,
        config=provider_config
    )

    # Check if provider is supported, fallback to legacy for Azure DevOps
    try:
        provider_supported = provider_manager.supports_provider()
    except Exception as e:
        # Configuration error or other validation issue
        console.print(f"[red]✗[/red] Provider configuration error: {e}")
        raise typer.Exit(code=1)
        
    if not provider_supported:
        if provider == "azuredevops":
            # Use legacy Azure DevOps manager
            ado = AzDevOpsManager(organization_url=organization, pat=token)
            
            # Prompt if still missing after checking args/config/env
            if not ado.ado_org:
                ado.ado_org = typer.prompt(
                    "Enter Azure DevOps organization URL",
                    default=DEFAULT_VALUES["AZURE_DEVOPS_ORG_URL"]
                )
                # Re-initialize if org was prompted
                ado = AzDevOpsManager(organization_url=ado.ado_org, pat=ado.ado_pat)
            
            if not ado.ado_pat:
                ado.ado_pat = typer.prompt(
                    "Enter Personal Access Token (PAT)",
                    hide_input=True
                )
                # Re-initialize if PAT was prompted
                ado = AzDevOpsManager(organization_url=ado.ado_org, pat=ado.ado_pat)
            
            # Ensure URL format is correct after potential prompt
            if ado.ado_org and not ado.ado_org.startswith(("http://", "https://")):
                ado.ado_org = f"https://{ado.ado_org}"
                # Re-initialize if URL format changed
                ado = AzDevOpsManager(organization_url=ado.ado_org, pat=ado.ado_pat)
            
            # Test the connection
            if ado.test_connection():
                console.print(f"[green]✓[/green] Successfully connected to Azure DevOps organization: {ado.ado_org}")
                
                # Store credentials if requested and if they were provided/discovered
                if store and ado.ado_org and ado.ado_pat:
                    should_store = True
                    if CONFIG_FILE.exists():
                        # Ask for confirmation before overwriting
                        should_store = Confirm.ask(f"Overwrite existing credentials in {CONFIG_FILE}?", default=False)
                    if should_store:
                        # Use the potentially prompted/formatted values
                        store_credentials(ado.ado_org, ado.ado_pat)
                    else:
                        console.print("[yellow]Credentials not stored.[/yellow]")
                elif store:
                    logger.warning("Could not store credentials as organization URL or PAT was missing.")
            else:
                console.print(f"[red]✗[/red] Failed to connect/authenticate to {ado.ado_org}. Please check URL and PAT.")
                raise typer.Exit(code=1)
            return
        else:
            console.print(f"[red]✗[/red] Provider '{provider}' is not yet fully implemented.")
            console.print(f"[yellow]Available providers: {', '.join(provider_manager.list_supported_providers())}[/yellow]")
            raise typer.Exit(code=1)
    
    # Use new provider system
    try:
        # Test connection with the provider
        if provider_manager.test_connection():
            console.print(f"[green]✓[/green] Successfully connected to {provider} provider")
            
            # TODO: Implement credential storage for multi-provider
            if store:
                console.print(f"[yellow]Credential storage for {provider} provider not yet implemented.[/yellow]")
        else:
            console.print(f"[red]✗[/red] Failed to connect/authenticate to {provider} provider. Please check credentials.")
            raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗[/red] Error testing {provider} provider connection: {e}")
        raise typer.Exit(code=1)


def store_credentials(organization: str, pat: str):
    """Store credentials in global config file for future use."""
    # Create config directory if it doesn't exist
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Read existing config if available
    config_values = {}
    if CONFIG_FILE.exists():
        config_values = dotenv_values(dotenv_path=str(CONFIG_FILE))

    # Update with new values
    config_values["AZURE_DEVOPS_ORG_URL"] = organization
    config_values["AZURE_DEVOPS_EXT_PAT"] = pat

    # Write back to config file
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        for k, v in config_values.items():
            f.write(f"{k}={v}\n")

    console.print(f"[green]✓[/green] Credentials stored in {CONFIG_FILE}")
    os.chmod(CONFIG_FILE, 0o600)  # Set secure permissions


# -----------------------------------------------------------------------------
# config Command
# -----------------------------------------------------------------------------
@app.command(help="Set or view global configuration settings for mgit.")
def config(
    show: bool = typer.Option(False, "--show", help="Show current global configuration and exit."),
    organization: Optional[str] = typer.Option(
        None, "--org", help="Default organization/workspace URL (provider-specific)."
    ),
    concurrency: Optional[int] = typer.Option(
        None, "--concurrency", help="Default concurrency for clone operations."
    ),
    update_mode: Optional[UpdateMode] = typer.Option(
        None, "--update-mode", help="Default update mode (skip, pull, force)."
    ),
):
    """
    Configure global settings for mgit.

    This command allows you to set default values for common parameters
    that will be used across all invocations of mgit.
    """
    # Create config directory if it doesn't exist
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Read existing config if available
    config_values: Dict[str, Any] = {}
    if CONFIG_FILE.exists():
        config_values = dotenv_values(dotenv_path=str(CONFIG_FILE))

    # If show option is specified, display current config and exit
    if show:
        console.print("[bold]Current global configuration:[/bold]")
        if config_values:
            for key, value in config_values.items():
                # Mask the PAT token when displaying
                if key == "AZURE_DEVOPS_EXT_PAT":
                    masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
                    console.print(f"  {key}={masked_value}")
                else:
                    console.print(f"  {key}={value}")
        else:
            console.print("  No global configuration set.")
        return

    # Update config values with provided options
    if organization:
        # Ensure URL format is correct
        if not organization.startswith(("http://", "https://")):
            organization = f"https://{organization}"
        config_values["AZURE_DEVOPS_ORG_URL"] = organization

    if concurrency is not None:
        config_values["DEFAULT_CONCURRENCY"] = str(concurrency)

    if update_mode is not None:
        config_values["DEFAULT_UPDATE_MODE"] = update_mode.value # Store enum value

    # Write updated config
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        for k, v in config_values.items():
            f.write(f"{k}={v}\n")

    # Set secure permissions on config file
    os.chmod(CONFIG_FILE, 0o600)

    console.print(f"[green]✓[/green] Configuration updated successfully in {CONFIG_FILE}")


# The callback is no longer needed since we're using Typer's built-in help


def main():
    # Call the app directly - Typer will handle no args case with help
    app()


# Needed for Windows-specific behavior (not called on Linux/Mac)
def entrypoint():
    """Entry point for the application when packaged."""
    main()


if __name__ == "__main__":
    main()

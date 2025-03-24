#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
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
import typer

# Default values used if environment variables and config file don't provide values
DEFAULT_VALUES = {
    "AZURE_DEVOPS_ORG_URL": "https://www.visualstudio.com",
    "LOG_FILENAME": "ado-cli.log",
    "LOG_LEVEL": "DEBUG",
    "CON_LEVEL": "INFO",
    "DEFAULT_CONCURRENCY": "4",
    "DEFAULT_UPDATE_MODE": "skip",
}

# Configuration loading order:
# 1. Environment variables (highest priority)
# 2. Global config file in ~/.config/ado-cli/config
# 3. Default values (lowest priority)

# First load environment variables
load_dotenv(
    dotenv_path=None,
    verbose=True,
    override=True,
)

# Load global config file if environment variables are not set
CONFIG_DIR = Path.home() / ".config" / "ado-cli"
CONFIG_FILE = CONFIG_DIR / "config"

def get_config_value(key: str, default_value: str = None) -> str:
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


class AdoCliFormatter(logging.Formatter):
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


file_handler = RotatingFileHandler(
    get_config_value("LOG_FILENAME"),
    maxBytes=5_000_000,
    backupCount=3,
)

file_handler.setFormatter(AdoCliFormatter())

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
    name="ado-cli",
    help="Azure DevOps CLI Tool v0.1.0 - A utility for managing Azure DevOps "
    "repositories and providing project-level git functionality.",
    add_completion=False,
    no_args_is_help=True,
)


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def embed_pat_in_url(repo_url: str, pat: str) -> str:
    """
    Rewrite repo_url to embed the PAT as credentials:
      https://org@dev.azure.com ->
        https://PersonalAccessToken:PAT@dev.azure.com
    That way 'git clone' won't prompt for credentials.
    """
    parsed = urlparse(repo_url)
    # Some ADOS remoteUrls look like:
    # 'https://org@dev.azure.com/org/project/_git/repo'
    # We'll embed 'PersonalAccessToken:pat@' as netloc
    # credentials, ignoring any existing user
    # Some Azure DevOps setups require this exact username
    username = "PersonalAccessToken"
    netloc = f"{username}:{pat}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"

    new_parsed = parsed._replace(netloc=netloc)
    return urlunparse(new_parsed)

def sanitize_repo_name(repo_url: str) -> str:
    """
    Extract and sanitize repository name from URL for use as a directory name.
    Handles URL encoding, spaces, and special characters.
    
    Example:
      Input: https://dev.azure.com/org/project/_git/Repo%20Name%20With%20Spaces
      Output: Repo_Name_With_Spaces
    """
    # Extract repo name from URL
    parsed = urlparse(repo_url)
    path_parts = parsed.path.split('/')
    # The repo name is typically the last part of the path after _git
    repo_name = ""
    for i, part in enumerate(path_parts):
        if part == "_git" and i + 1 < len(path_parts):
            repo_name = path_parts[i + 1]
            break
    
    # If we couldn't find it after _git, use the last part of the path
    if not repo_name and path_parts:
        repo_name = path_parts[-1]
    
    # Decode URL encoding
    repo_name = unquote(repo_name)
    
    # Replace spaces and special characters with underscores
    # Keep alphanumeric, underscore, hyphen, and period
    repo_name = re.sub(r'[^\w\-\.]', '_', repo_name)
    
    return repo_name


# -----------------------------------------------------------------------------
# Azure DevOps Manager
# -----------------------------------------------------------------------------
class AzDevOpsManager:
    def __init__(self):
        # Get organization URL from config
        self.ado_org = get_config_value("AZURE_DEVOPS_ORG_URL")
        
        # Ensure the URL is properly formatted
        if self.ado_org and not self.ado_org.startswith(("http://", "https://")):
            self.ado_org = f"https://{self.ado_org}"
        
        # Get PAT - handle various formats and credential locations
        # First try standard environment variable
        self.ado_pat = get_config_value("AZURE_DEVOPS_EXT_PAT")
        
        # If not found, try alternative environment variables that might be used
        if not self.ado_pat:
            # Try common alternatives
            for env_var in ["AZURE_DEVOPS_PAT", "ADO_PAT", "AZURE_PAT"]:
                env_value = os.getenv(env_var)
                if env_value:
                    self.ado_pat = env_value
                    logger.debug(f"Using PAT from {env_var} environment variable")
                    # Set the standard environment variable for consistency
                    os.environ["AZURE_DEVOPS_EXT_PAT"] = self.ado_pat
                    break
        
        # No default for PAT - it must be provided

    def check_az_cli_installed(self):
        logger.debug(
            "Checking if Azure CLI is installed..."
        )
        try:
            proc = subprocess.run(
                ["az", "version", "--output", "json"],
                capture_output=True,
                text=True,
                check=True,
            )
            json.loads(proc.stdout)
            logger.debug(
                "Azure CLI is installed and functioning: %s",
                proc.stdout,
            )
        except Exception as e:
            logger.error(
                "Azure CLI is not installed or not functioning correctly."
            )
            raise typer.Exit(code=1) from e

    def ensure_ado_ext_installed(self):
        logger.debug(
            "Checking if azure-devops extension is installed..."
        )
        try:
            proc = subprocess.run(
                [
                    "az",
                    "extension",
                    "show",
                    "--name",
                    "azure-devops",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.debug(
                "azure-devops extension is installed."
            )
            logger.debug("Output: %s", proc.stdout)
        except subprocess.CalledProcessError:
            logger.info(
                "azure-devops extension is missing; attempting install..."
            )
            try:
                proc = subprocess.run(
                    [
                        "az",
                        "extension",
                        "add",
                        "--name",
                        "azure-devops",
                        "--allow-preview",
                        "true",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                logger.info(
                    "azure-devops extension installed successfully."
                )
                logger.debug("Output: %s", proc.stdout)
            except subprocess.CalledProcessError as e:
                logger.error(
                    "Failed to install azure-devops extension. "
                    "Install manually."
                )
                raise typer.Exit(code=1) from e

    def is_logged_into_az_devops(
        self, organization: str
    ) -> bool:
        """
        Check if the user is logged into Azure DevOps by attempting to list projects.
        
        This method verifies authentication by configuring the organization and 
        trying to list projects. It will return True if the authentication works,
        False otherwise.
        """
        logger.debug(
            "Checking if logged in to Azure DevOps organization: %s",
            organization,
        )
        
        # Ensure the organization URL is properly formatted
        if organization and not organization.startswith(("http://", "https://")):
            organization = f"https://{organization}"
        
        # Save current environment variable if it exists
        original_pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
        
        # Make sure the current PAT is set in the environment
        if self.ado_pat:
            os.environ["AZURE_DEVOPS_EXT_PAT"] = self.ado_pat
        
        try:
            # Configure the default organization
            try:
                proc = subprocess.run(
                    [
                        "az",
                        "devops",
                        "configure",
                        "--defaults",
                        f"organization={organization}",
                    ],
                    capture_output=True,
                    text=False,  # Use binary mode to avoid encoding issues
                    check=False,
                )
                # Safely decode the output
                stdout = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ""
                stderr = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else ""
                # Update the process object
                proc.stdout = stdout
                proc.stderr = stderr
            except Exception as e:
                logger.debug(f"Error configuring organization: {str(e)}")
                return False
            
            if proc.returncode != 0:
                logger.debug(
                    "Failed to configure default organization: %s", 
                    proc.stderr.strip()
                )
                return False
                
            logger.debug("Organization configured: %s", organization)

            # Try to list projects to verify authentication
            try:
                proc = subprocess.run(
                    [
                        "az",
                        "devops",
                        "project",
                        "list",
                        "--only-show-errors",
                    ],
                    capture_output=True,
                    text=False,  # Use binary mode to avoid encoding issues
                    check=False,
                    env=os.environ,
                )
                # Safely decode the output
                stdout = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ""
                stderr = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else ""
                # Update the process object
                proc.stdout = stdout
                proc.stderr = stderr
            except Exception as e:
                logger.debug(f"Error listing projects: {str(e)}")
                return False
            
            if proc.returncode == 0 and proc.stdout.strip():
                logger.debug("Already logged in to %s", organization)
                logger.debug("Projects found: %s", proc.stdout.strip())
                return True
                
            # Check if error is auth-related
            if proc.returncode != 0:
                error_msg = proc.stderr.strip().lower()
                if ("authentication" in error_msg or 
                    "authorize" in error_msg or 
                    "permission" in error_msg or
                    "credentials" in error_msg or
                    "unauthorized" in error_msg):
                    logger.debug(
                        "Authentication error detected: %s", 
                        proc.stderr.strip()
                    )
                    return False
                    
            logger.debug("Not logged in to %s", organization)
            return False
            
        except Exception as e:
            logger.debug(f"Error checking login status: {str(e)}")
            return False
            
        finally:
            # Restore original PAT environment variable if it existed
            if original_pat is not None:
                os.environ["AZURE_DEVOPS_EXT_PAT"] = original_pat
            elif "AZURE_DEVOPS_EXT_PAT" in os.environ and original_pat is None:
                # If there wasn't an original PAT, remove the one we set
                pass

    def login_to_az_devops(
        self, organization: str, pat: str
    ):
        logger.info(
            "Logging in to Azure DevOps with PAT to organization: %s",
            organization,
        )
        
        # Save current environment variable if it exists
        original_pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
        
        try:
            # Set environment variable method - most reliable method for authentication
            os.environ["AZURE_DEVOPS_EXT_PAT"] = pat
            
            # Configure the default organization
            logger.debug("Configuring default organization: %s", organization)
            proc = subprocess.run(
                [
                    "az",
                    "devops",
                    "configure",
                    "--defaults",
                    f"organization={organization}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if proc.returncode != 0:
                logger.warning(
                    "Warning: Could not set default organization. Error: %s",
                    proc.stderr.strip(),
                )
            
            # Test if we can access Azure DevOps resources with PAT
            logger.debug("Testing authentication by listing projects")
            try:
                test_proc = subprocess.run(
                    [
                        "az",
                        "devops",
                        "project",
                        "list",
                        "--only-show-errors",
                    ],
                    capture_output=True,
                    text=False,  # Use binary mode to avoid encoding issues
                    check=False,
                    env=os.environ,
                )
                # Safely decode the output
                stdout = test_proc.stdout.decode('utf-8', errors='replace') if test_proc.stdout else ""
                stderr = test_proc.stderr.decode('utf-8', errors='replace') if test_proc.stderr else ""
                # Create a surrogate object with the decoded text
                test_proc.stdout = stdout
                test_proc.stderr = stderr
            except Exception as e:
                logger.error(f"Error executing project list command: {str(e)}")
                test_proc = type('obj', (object,), {
                    'returncode': 1, 
                    'stdout': "", 
                    'stderr': f"Command execution error: {str(e)}"
                })
            
            if test_proc.returncode == 0 and test_proc.stdout.strip():
                logger.info(
                    "Logged in to Azure DevOps successfully using environment PAT."
                )
                return
                
            # If environment variable method fails, try explicit login
            logger.info("Environment variable login failed. Trying explicit login method...")
            
            # Use a different approach for the explicit login
            # First, check the explicit credential storage method
            logger.debug("Attempting to store credentials explicitly")
            try:
                with open('/dev/null', 'w') as devnull:
                    pat_bytes = pat.encode('utf-8') if isinstance(pat, str) else pat
                    cred_proc = subprocess.run(
                        [
                            "az",
                            "devops",
                            "login",
                            "--organization",
                            organization,
                        ],
                        input=pat_bytes,
                        text=False,  # Use binary mode to avoid encoding issues
                        stdout=devnull,
                        stderr=subprocess.PIPE,
                        check=False,
                    )
                    # Safely decode the output
                    stderr = cred_proc.stderr.decode('utf-8', errors='replace') if cred_proc.stderr else ""
                    # Update the process object
                    cred_proc.stderr = stderr
            except Exception as e:
                logger.error(f"Error during explicit login: {str(e)}")
                cred_proc = type('obj', (object,), {
                    'returncode': 1, 
                    'stderr': f"Login command error: {str(e)}"
                })
            
            # Test again after explicit login
            logger.debug("Testing authentication after explicit login")
            try:
                test_proc = subprocess.run(
                    [
                        "az",
                        "devops",
                        "project",
                        "list",
                        "--only-show-errors",
                    ],
                    capture_output=True,
                    text=False,  # Use binary mode to avoid encoding issues
                    check=False,
                    env=os.environ,
                )
                # Safely decode the output
                stdout = test_proc.stdout.decode('utf-8', errors='replace') if test_proc.stdout else ""
                stderr = test_proc.stderr.decode('utf-8', errors='replace') if test_proc.stderr else ""
                # Create a surrogate object with the decoded text
                test_proc.stdout = stdout
                test_proc.stderr = stderr
            except Exception as e:
                logger.error(f"Error checking authentication after explicit login: {str(e)}")
                test_proc = type('obj', (object,), {
                    'returncode': 1, 
                    'stdout': "", 
                    'stderr': f"Command execution error: {str(e)}"
                })
            
            if test_proc.returncode == 0 and test_proc.stdout.strip():
                logger.info(
                    "Logged in to Azure DevOps successfully using explicit login."
                )
                logger.debug("Auth test output: %s", test_proc.stdout.strip())
                return
            
            # Last resort - try token via basic auth in headers
            logger.info("Trying token via custom header method...")
            try:
                header_proc = subprocess.run(
                    [
                        "az",
                        "devops",
                        "project",
                        "list",
                        "--org",
                        organization,
                        "--only-show-errors",
                        "--detect",
                        "false",
                    ],
                    capture_output=True,
                    text=False,  # Use binary mode to avoid encoding issues
                    check=False,
                    env=os.environ,
                )
                # Safely decode the output
                stdout = header_proc.stdout.decode('utf-8', errors='replace') if header_proc.stdout else ""
                stderr = header_proc.stderr.decode('utf-8', errors='replace') if header_proc.stderr else ""
                # Create a surrogate object with the decoded text
                header_proc.stdout = stdout
                header_proc.stderr = stderr
            except Exception as e:
                logger.error(f"Error during custom header authentication: {str(e)}")
                header_proc = type('obj', (object,), {
                    'returncode': 1, 
                    'stdout': "", 
                    'stderr': f"Header auth error: {str(e)}"
                })
            
            if header_proc.returncode == 0 and header_proc.stdout.strip():
                logger.info(
                    "Logged in to Azure DevOps successfully using header auth."
                )
                return
            
            # If we get here, all login attempts failed
            error_details = (
                f"Env auth error: {test_proc.stderr.strip()}\n"
                f"Explicit auth error: {cred_proc.stderr.strip() if 'cred_proc' in locals() else 'Not attempted'}\n"
                f"Header auth error: {header_proc.stderr.strip() if 'header_proc' in locals() else 'Not attempted'}"
            )
            
            logger.error(
                "Failed to login to Azure DevOps using all available methods."
            )
            logger.debug("Login errors: %s", error_details)
            logger.error(
                "Please ensure your PAT is valid and has the correct permissions."
                "\n  Common issues:"
                "\n  - PAT is expired"
                "\n  - PAT lacks required scopes (needs 'Code (read)' at minimum)"
                "\n  - Organization URL is incorrect"
                "\n\nYou can manually set the PAT in your environment:"
                "\n  export AZURE_DEVOPS_EXT_PAT='your-pat-token'"
                "\n  Or add it to your .env file or global config at ~/.config/ado-cli/config"
            )
            raise typer.Exit(code=1)
            
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            raise typer.Exit(code=1)
            
        finally:
            # Restore original PAT environment variable if it existed
            if original_pat is not None:
                os.environ["AZURE_DEVOPS_EXT_PAT"] = original_pat
            elif "AZURE_DEVOPS_EXT_PAT" in os.environ:
                # If there was no original, but we set one, keep it set to the new value
                pass

    def configure_az_devops(
        self, organization: str, project: str
    ):
        """
        Configure Azure DevOps defaults for the organization and project.
        
        This method sets the default organization and project for subsequent
        az devops commands.
        """
        logger.debug(
            "Setting AZ DevOps defaults: org=%s, project=%s",
            organization,
            project,
        )
        
        # Ensure the organization URL is properly formatted
        if organization and not organization.startswith(("http://", "https://")):
            organization = f"https://{organization}"
            
        try:
            proc = subprocess.run(
                [
                    "az",
                    "devops",
                    "configure",
                    "--defaults",
                    f"organization={organization}",
                    f"project={project}",
                ],
                capture_output=True,
                text=False,  # Use binary mode to avoid encoding issues
                check=False,
            )
            # Safely decode the output
            stdout = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ""
            stderr = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else ""
            
            if proc.returncode != 0:
                logger.error(
                    "Failed to configure Azure DevOps defaults. Output: %s",
                    stderr.strip(),
                )
                raise typer.Exit(code=1)
            else:
                logger.debug(
                    "Azure DevOps defaults configured successfully."
                )
                logger.debug("Output: %s", stdout.strip())
        except Exception as e:
            logger.error(f"Error configuring Azure DevOps: {str(e)}")
            raise typer.Exit(code=1)


# -----------------------------------------------------------------------------
# Git Manager
# -----------------------------------------------------------------------------
class GitManager:
    GIT_EXECUTABLE = "git"

    async def git_clone(
        self, repo_url: str, output_dir: Path, dir_name: str = None
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
            logger.error(
                f"Command '{' '.join(cmd)}' failed "
                f"with return code {process.returncode}."
            )
            raise typer.Exit(code=1)


class UpdateMode(str, Enum):
    skip = "skip"
    pull = "pull"
    force = "force"


@app.command()
def clone_all(
    project: str = typer.Argument(
        ..., help="Azure DevOps project name."
    ),
    rel_path: str = typer.Argument(
        ..., help="Relative path to clone into."
    ),
    url: Optional[str] = typer.Argument(
        None,
        help="Organization URL (defaults to "
        f"{DEFAULT_VALUES['AZURE_DEVOPS_ORG_URL']} if not provided).",
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
    Clone all repositories from Azure DevOps project.
    """

    if not url:
        url = get_config_value("AZURE_DEVOPS_ORG_URL")

    ado = AzDevOpsManager()
    git_manager = GitManager()

    if not ado.ado_org or not ado.ado_pat:
        logger.error(
            "AZURE_DEVOPS_ORG_URL or AZURE_DEVOPS_EXT_PAT "
            "are not set in environment or config file. "
            "Use 'ado-cli config --org URL' and ensure your PAT is set."
        )
        raise typer.Exit(code=1)

    # Step 1: CLI + extension
    ado.check_az_cli_installed()
    ado.ensure_ado_ext_installed()

    # Step 2: Az DevOps login
    if not ado.is_logged_into_az_devops(ado.ado_org):
        ado.login_to_az_devops(ado.ado_org, ado.ado_pat)

    # Step 3: Prepare local folder
    target_path = Path.cwd() / rel_path
    target_path.mkdir(parents=True, exist_ok=True)

    # Step 4: Configure defaults in Az DevOps
    ado.configure_az_devops(url, project)

    # Step 5: List repos
    logger.debug(
        "Fetching repository list from Azure DevOps..."
    )
    try:
        proc = subprocess.run(
            [
                "az",
                "repos",
                "list",
                "--org",
                ado.ado_org,  # Explicitly set the org here to avoid redirection issues
                "--project",
                project,       # Explicitly set the project here
                "--query",
                "[].{Name:name, Url:remoteUrl, isDisabled:isDisabled}",
                "-o",
                "json",
            ],
            capture_output=True,
            text=False,  # Use binary mode to avoid encoding issues
            check=False,
        )
        # Safely decode the output
        stdout = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ""
        stderr = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else ""
        # Update the process object
        proc.stdout = stdout
        proc.stderr = stderr
    except Exception as e:
        logger.error(f"Error fetching repository list: {str(e)}")
        raise typer.Exit(code=1)
    if proc.returncode != 0:
        logger.error(
            "Failed to list repos. Error: %s",
            proc.stderr.strip(),
        )
        raise typer.Exit(code=1)
    else:
        logger.debug(
            "Repository list fetched successfully: %s",
            proc.stdout,
        )

    try:
        repos = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse repository list JSON."
        )
        raise typer.Exit(code=1) from e

    failures = []

    async def do_clones():
        """
        Process repos asynchronously with a concurrency
        limit and a progress bar. lso embed the PAT in the remote URL.
        Handle each repo's failure gracefully, storing it in 'failures'.
        """
        sem = asyncio.Semaphore(concurrency)

        with Progress() as progress:
            task_id = progress.add_task(
                "[green]Processing Repositories...",
                total=len(repos),
            )

            async def process_one_repo(
                repo_name: str, repo_url: str, repo_data: dict
            ):
                async with sem:
                    # Check if repository is disabled
                    if repo_data.get("isDisabled", False):
                        logger.info(
                            f"Skipping disabled repository: {repo_name}"
                        )
                        failures.append(
                            (repo_name, "repository is disabled")
                        )
                        progress.advance(task_id, 1)
                        return
                    
                    # Sanitize the repository name for filesystem use
                    sanitized_name = sanitize_repo_name(repo_url)
                    if sanitized_name != repo_name:
                        logger.debug(
                            f"Using sanitized name '{sanitized_name}' for repository '{repo_name}'"
                        )
                    
                    repo_folder = target_path / sanitized_name
                    # Decide how to handle if folder already exists
                    if repo_folder.exists():
                        if update_mode == "skip":
                            # Mark as "skipped" for the summary if you want
                            logger.info(
                                f"Skipping existing repo folder: {sanitized_name}"
                            )
                            progress.advance(task_id, 1)
                            return
                        elif update_mode == "pull":
                            # Check if .git exists
                            if (
                                repo_folder / ".git"
                            ).exists():
                                # Attempt to do a pull
                                try:
                                    await git_manager.git_pull(
                                        repo_folder
                                    )
                                except typer.Exit:
                                    failures.append(
                                        (
                                            repo_name,
                                            "pull failed",
                                        )
                                    )
                            else:
                                msg = "Folder exists but is not a git repo."
                                logger.warning(
                                    f"{repo_name}: {msg}"
                                )
                                failures.append(
                                    (repo_name, msg)
                                )
                            progress.advance(task_id, 1)
                            return
                        elif update_mode == "force":
                            logger.info(
                                f"Removing existing folder: {sanitized_name}"
                            )
                            try:
                                shutil.rmtree(repo_folder)
                            except Exception as e:
                                failures.append(
                                    (
                                        repo_name,
                                        f"Failed removing old folder: {e}",
                                    )
                                )
                                progress.advance(task_id, 1)
                                return
                            # Then we fall through to clone
                    # If we made it here, either folder didn't
                    # exist or we forced it away
                    pat_url = embed_pat_in_url(
                        repo_url, ado.ado_pat
                    )
                    try:
                        # Modified to include a directory argument to git clone
                        # This ensures the output directory has the sanitized name
                        await git_manager.git_clone(
                            pat_url, target_path, sanitized_name
                        )
                    except typer.Exit:
                        failures.append(
                            (repo_name, "clone failed")
                        )

                    progress.advance(task_id, 1)

            await asyncio.gather(
                *(
                    process_one_repo(r["Name"], r["Url"], r)
                    for r in repos
                )
            )

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
        ..., help="Azure DevOps project name."
    ),
    rel_path: str = typer.Argument(
        ..., help="Relative path where repositories exist."
    ),
):
    """
    Pull the latest changes for all repositories
    in the specified relative path.
    """
    ado = AzDevOpsManager()
    git_manager = GitManager()

    if not ado.ado_org or not ado.ado_pat:
        logger.error(
            "AZURE_DEVOPS_ORG_URL or AZURE_DEVOPS_EXT_PAT "
            "are not set in environment or config file."
        )
        raise typer.Exit(code=1)

    ado.check_az_cli_installed()
    ado.ensure_ado_ext_installed()

    if not ado.is_logged_into_az_devops(ado.ado_org):
        ado.login_to_az_devops(ado.ado_org, ado.ado_pat)

    target_path = Path.cwd() / rel_path
    if not target_path.exists():
        logger.error("Path does not exist: %s", target_path)
        raise typer.Exit(code=1)

    ado.configure_az_devops(ado.ado_org, project)

    logger.debug(
        "Fetching repository list from Azure DevOps..."
    )
    try:
        proc = subprocess.run(
            [
                "az",
                "repos",
                "list",
                "--org",
                ado.ado_org,  # Explicitly set the org here to avoid redirection issues
                "--project",
                project,       # Explicitly set the project here
                "--query",
                "[].{Name:name, Url:remoteUrl, isDisabled:isDisabled}",
                "-o",
                "json",
            ],
            capture_output=True,
            text=False,  # Use binary mode to avoid encoding issues
            check=False,
        )
        # Safely decode the output
        stdout = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ""
        stderr = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else ""
        # Update the process object
        proc.stdout = stdout
        proc.stderr = stderr
    except Exception as e:
        logger.error(f"Error fetching repository list: {str(e)}")
        raise typer.Exit(code=1)
    if proc.returncode != 0:
        logger.error(
            "Failed to list repos. Error: %s",
            proc.stderr.strip(),
        )
        raise typer.Exit(code=1)

    try:
        repos = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse repository list JSON."
        )
        raise typer.Exit(code=1) from e

    async def do_pulls():
        failures = []
        for repo in repos:
            repo_name = repo.get("Name")
            repo_url = repo.get("Url", "")
            if not repo_name:
                continue
                
            # Check if repository is disabled
            if repo.get("isDisabled", False):
                logger.info(
                    f"Skipping disabled repository: {repo_name}"
                )
                failures.append(
                    (repo_name, "repository is disabled")
                )
                continue
            
            # Sanitize the repository name for filesystem use
            sanitized_name = sanitize_repo_name(repo_url)
            if sanitized_name != repo_name:
                logger.debug(
                    f"Using sanitized name '{sanitized_name}' for repository '{repo_name}'"
                )
                
            repo_dir = target_path / sanitized_name
            if (
                repo_dir.exists()
                and (repo_dir / ".git").exists()
            ):
                try:
                    await git_manager.git_pull(repo_dir)
                except typer.Exit:
                    failures.append(
                        (repo_name, "pull failed")
                    )
            else:
                logger.warning(
                    f"Repository path is missing or not a git repo: {repo_dir}"
                )
        if failures:
            logger.warning(
                "Some repositories had pull failures:"
            )
            for name, reason in failures:
                logger.warning(f" - {name}: {reason}")
        else:
            logger.info(
                "All repositories have been pulled successfully."
            )

    logger.info(
        f"Pulling all repositories for project: {project} in '{target_path}'"
    )
    asyncio.run(do_pulls())


# -----------------------------------------------------------------------------
# generate_env Command
# -----------------------------------------------------------------------------
@app.command(help="Generate a sample environment file with configuration options.")
def generate_env():
    """
    Generate a detailed sample environment file with all configuration options.
    
    This command creates a .env.sample file with example values and detailed
    comments explaining each configuration option. Users can copy this file
    to .env to set local environment variables.
    """
    env_content = """# Azure DevOps CLI Configuration Sample
# Copy this file to .env to configure environment variables
# Or use ~/.config/ado-cli/config for global settings

# Azure DevOps organization URL (required)
AZURE_DEVOPS_ORG_URL=https://www.visualstudio.com

# Personal Access Token for authentication (required)
# Can also be set in ~/.config/ado-cli/config
AZURE_DEVOPS_EXT_PAT=<YOUR_PERSONAL_ACCESS_TOKEN>

# Log file name (default: ado-cli.log)
LOG_FILENAME=ado-cli.log

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
@app.command(help="Login to Azure DevOps and validate credentials.")
def login(
    organization: str = typer.Option(
        None, "--org", "-o", help="Azure DevOps organization URL."
    ),
    pat: str = typer.Option(
        None, "--pat", "-p", help="Personal Access Token for authentication."
    ),
    store: bool = typer.Option(
        True, 
        "--store/--no-store", 
        help="Store credentials in config file for future use."
    )
):
    """
    Login to Azure DevOps using a Personal Access Token (PAT).
    
    If organization or PAT are not provided, they will be read from 
    environment variables or prompted for interactively.
    """
    ado = AzDevOpsManager()
    
    # Check Azure CLI and extensions first
    ado.check_az_cli_installed()
    ado.ensure_ado_ext_installed()
    
    # If org not provided, use from environment or prompt
    if not organization:
        organization = ado.ado_org
        if organization == DEFAULT_VALUES["AZURE_DEVOPS_ORG_URL"]:
            organization = typer.prompt(
                "Enter Azure DevOps organization URL", 
                default=DEFAULT_VALUES["AZURE_DEVOPS_ORG_URL"]
            )
    
    # Ensure URL format is correct
    if not organization.startswith(("http://", "https://")):
        organization = f"https://{organization}"
    
    # If PAT not provided, use from environment or prompt securely
    if not pat:
        pat = ado.ado_pat
        if not pat:
            pat = typer.prompt(
                "Enter Personal Access Token (PAT)", 
                hide_input=True
            )
    
    # Try to login with provided credentials
    try:
        ado.login_to_az_devops(organization, pat)
        console.print("[green]✓[/green] Successfully logged in to Azure DevOps!")
        
        # Store credentials if requested
        if store:
            store_credentials(organization, pat)
    
    except typer.Exit:
        console.print("[red]✗[/red] Failed to login. Please check your credentials and try again.")
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
@app.command(help="Set or view global configuration settings for ado-cli.")
def config(
    show: bool = typer.Option(
        False, "--show", help="Show current configuration settings."
    ),
    organization: Optional[str] = typer.Option(
        None, "--org", help="Default Azure DevOps organization URL."
    ),
    concurrency: Optional[int] = typer.Option(
        None, "--concurrency", help="Default concurrency for clone operations."
    ),
    update_mode: Optional[UpdateMode] = typer.Option(
        None, "--update-mode", help="Default update mode (skip, pull, force)."
    ),
):
    """
    Configure global settings for ado-cli.
    
    This command allows you to set default values for common parameters
    that will be used across all invocations of ado-cli.
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
        config_values["DEFAULT_UPDATE_MODE"] = update_mode
    
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
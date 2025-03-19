#!/usr/bin/env python3

import os
import asyncio
import json
import subprocess
import logging
import shutil
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlunparse

import typer
from enum import Enum
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress
from dotenv import load_dotenv, dotenv_values

DEFAULT_VALUES = {
    "AZURE_DEVOPS_ORG_URL": "https://www.visualstudio.com",
    "AZURE_DEVOPS_EXT_PAT": "<your-pat-token>",
    "LOG_FILENAME": "ado-cli.log",
    "LOG_LEVEL": "DEBUG",
    "CON_LEVEL": "INFO",
}

load_dotenv(
    dotenv_path=None,
    verbose=True,
    override=True,
)

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
    os.getenv(
        "LOG_FILENAME", DEFAULT_VALUES["LOG_FILENAME"]
    ),
    maxBytes=5_000_000,
    backupCount=3,
)

file_handler.setFormatter(AdoCliFormatter())

console_handler = RichHandler(
    rich_tracebacks=True, markup=True
)
console_handler.setLevel(
    os.getenv("CON_LEVEL", DEFAULT_VALUES["CON_LEVEL"])
)

logger = logging.getLogger(__name__)
logger.setLevel(
    os.getenv("LOG_LEVEL", DEFAULT_VALUES["LOG_LEVEL"])
)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

console = Console()
app = typer.Typer(
    name=__name__,
    help="ado-cli v0.0.1 - CLI to provide project-level git"
    "functionality with Azure DevOps.",
    add_completion=False,
)


# -----------------------------------------------------------------------------
# Helper to insert PAT into the remote URL
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


# -----------------------------------------------------------------------------
# Azure DevOps Manager
# -----------------------------------------------------------------------------
class AzDevOpsManager:
    def __init__(self):
        # Get organization URL from environment
        self.ado_org = os.getenv(
            "AZURE_DEVOPS_ORG_URL",
            DEFAULT_VALUES["AZURE_DEVOPS_ORG_URL"],
        )
        
        # Ensure the URL is properly formatted
        if self.ado_org and not self.ado_org.startswith(("http://", "https://")):
            self.ado_org = f"https://{self.ado_org}"
        
        # Get PAT from environment - handle various formats and credential locations
        # First try standard environment variable
        self.ado_pat = os.getenv("AZURE_DEVOPS_EXT_PAT")
        
        # If not found, try alternative environment variables that might be used
        if not self.ado_pat or self.ado_pat == DEFAULT_VALUES["AZURE_DEVOPS_EXT_PAT"]:
            # Try common alternatives
            for env_var in ["AZURE_DEVOPS_PAT", "ADO_PAT", "AZURE_PAT"]:
                if os.getenv(env_var):
                    self.ado_pat = os.getenv(env_var)
                    logger.debug(f"Using PAT from {env_var} environment variable")
                    # Set the standard environment variable for consistency
                    os.environ["AZURE_DEVOPS_EXT_PAT"] = self.ado_pat
                    break
        
        # If still not found, use default
        if not self.ado_pat:
            self.ado_pat = DEFAULT_VALUES["AZURE_DEVOPS_EXT_PAT"]

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
        if self.ado_pat and self.ado_pat != DEFAULT_VALUES["AZURE_DEVOPS_EXT_PAT"]:
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
                "\n  Or add it to your .env file"
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
        self, repo_url: str, output_dir: Path
    ):
        """
        Use 'git clone' for the given repo_url, in output_dir.
        Raises typer.Exit if the command fails.
        """
        logger.info(
            f"Cloning repository: {repo_url} into {output_dir}"
        )
        cmd = [self.GIT_EXECUTABLE, "clone", repo_url]
        await self._run_subprocess(cmd, cwd=output_dir)

    async def git_pull(self, repo_dir: Path):
        """
        Use 'git pull' for the existing repo in repo_dir.
        """
        logger.info(f"Pulling repository in: {repo_dir}")
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
        4,
        "--concurrency",
        "-c",
        help="Number of concurrent clone operations.",
    ),
    update_mode: UpdateMode = typer.Option(
        UpdateMode.skip,
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
        url = DEFAULT_VALUES["AZURE_DEVOPS_ORG_URL"]

    ado = AzDevOpsManager()
    git_manager = GitManager()

    if not ado.ado_org or not ado.ado_pat:
        logger.error(
            "AZURE_DEVOPS_ORG_URL or AZURE_DEVOPS_EXT_PAT "
            "are not set. Check your .env file."
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
                "[].{Name:name, Url:remoteUrl}",
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
                repo_name: str, repo_url: str
            ):
                async with sem:
                    repo_folder = target_path / repo_name
                    # Decide how to handle if folder already exists
                    if repo_folder.exists():
                        if update_mode == "skip":
                            # Mark as "skipped" for the summary if you want
                            logger.info(
                                f"Skipping existing repo folder: {repo_name}"
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
                                f"Removing existing folder: {repo_name}"
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
                        await git_manager.git_clone(
                            pat_url, target_path
                        )
                    except typer.Exit:
                        failures.append(
                            (repo_name, "clone failed")
                        )

                    progress.advance(task_id, 1)

            await asyncio.gather(
                *(
                    process_one_repo(r["Name"], r["Url"])
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
            "are not set. Check your .env file."
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
                "[].{Name:name, Url:remoteUrl}",
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
            if not repo_name:
                continue
            repo_dir = target_path / repo_name
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
# gen_env Command
# -----------------------------------------------------------------------------
@app.command(help="Generate an environment file.")
def gen_env():
    env_keys = DEFAULT_VALUES
    existing = {}
    base_env_file = Path(".env")
    if base_env_file.exists():
        existing = dotenv_values(
            dotenv_path=str(base_env_file)
        )

    counter = 0
    new_file = Path(".env")
    while new_file.exists():
        counter += 1
        new_file = Path(f".env{counter}")

    with new_file.open("w", encoding="utf-8") as wf:
        for k, v in env_keys.items():
            wf.write(f"{k}={existing.get(k, v)}\n")

    console.print(
        f"Created {new_file} with collected environment variables."
    )


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
        help="Store credentials in .env file for future use."
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
        if pat == DEFAULT_VALUES["AZURE_DEVOPS_EXT_PAT"]:
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
    """Store credentials in .env file for future use."""
    env_file = Path(".env")
    
    # Read existing .env if available
    env_vars = {}
    if env_file.exists():
        env_vars = dotenv_values(dotenv_path=str(env_file))
    
    # Update with new values
    env_vars["AZURE_DEVOPS_ORG_URL"] = organization
    env_vars["AZURE_DEVOPS_EXT_PAT"] = pat
    
    # Write back to .env
    with env_file.open("w", encoding="utf-8") as f:
        for k, v in env_vars.items():
            f.write(f"{k}={v}\n")
    
    console.print(f"[green]✓[/green] Credentials stored in {env_file}")
    os.chmod(env_file, 0o600)  # Set secure permissions


def main():
    app()


if __name__ == "__main__":
    main()

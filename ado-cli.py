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
        self.ado_org = os.getenv(
            "AZURE_DEVOPS_ORG_URL",
            DEFAULT_VALUES["AZURE_DEVOPS_ORG_URL"],
        )
        self.ado_pat = os.getenv(
            "AZURE_DEVOPS_EXT_PAT",
            DEFAULT_VALUES["AZURE_DEVOPS_EXT_PAT"],
        )

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
        logger.debug(
            "Checking if logged in to Azure DevOps organization: %s",
            organization,
        )
        # Configure the default organization
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
        )
        logger.debug(
            "Configuration Output: %s", proc.stdout
        )

        proc = subprocess.run(
            [
                "az",
                "devops",
                "project",
                "list",
                "--only-show-errors",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            logger.debug(
                "Already logged in to %s", organization
            )
            logger.debug("Output: %s", proc.stdout.strip())
            return True
        logger.debug("Not logged in to %s", organization)
        return False

    def login_to_az_devops(
        self, organization: str, pat: str
    ):
        logger.info(
            "Logging in to Azure DevOps with PAT to organization: %s",
            organization,
        )
        proc = subprocess.run(
            [
                "az",
                "devops",
                "login",
                "--organization",
                organization,
                "--verbose",
            ],
            input=pat,
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            logger.error(
                "Failed to login to Azure DevOps. Output: %s",
                proc.stderr.strip(),
            )
            raise typer.Exit(code=1)
        else:
            logger.info(
                "Logged in to Azure DevOps successfully."
            )
            logger.debug("Output: %s", proc.stdout.strip())

    def configure_az_devops(
        self, organization: str, project: str
    ):
        logger.debug(
            "Setting AZ DevOps defaults: org=%s, project=%s",
            organization,
            project,
        )
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
            text=True,
        )
        if proc.returncode != 0:
            logger.error(
                "Failed to configure Azure DevOps defaults. Output: %s",
                proc.stderr.strip(),
            )
            raise typer.Exit(code=1)
        else:
            logger.debug(
                "Azure DevOps defaults configured successfully."
            )
            logger.debug("Output: %s", proc.stdout.strip())


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
    proc = subprocess.run(
        [
            "az",
            "repos",
            "list",
            "--query",
            "[].{Name:name, Url:remoteUrl}",
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
    )
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
    proc = subprocess.run(
        [
            "az",
            "repos",
            "list",
            "--query",
            "[].{Name:name, Url:remoteUrl}",
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
    )
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


def main():
    app()


if __name__ == "__main__":
    main()

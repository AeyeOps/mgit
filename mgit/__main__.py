#!/usr/bin/env python3

import asyncio
import contextlib
import logging
import os
import warnings
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Confirm

from mgit import __version__
from mgit.commands.bulk_operations import (
    UpdateMode as BulkUpdateMode,
)

# diff import will be added inside the command function
from mgit.commands.listing import format_results, list_repositories
from mgit.commands.status import display_status_results, get_repository_statuses

# Import sync command
from mgit.commands.sync import sync_command, sync_local_command
from mgit.config.yaml_manager import (
    CONFIG_DIR,
    add_provider_config,
    detect_provider_type,
    get_default_provider_name,
    get_global_config,
    get_global_setting,
    get_provider_config,
    get_provider_configs,
    list_provider_names,
    remove_provider_config,
    set_default_provider,
)
from mgit.exceptions import MgitError
from mgit.providers.manager import ProviderManager

# Suppress the specific UserWarning from PyInstaller's bootloader
warnings.filterwarnings(
    "ignore", message="pkg_resources is deprecated as an API", category=UserWarning
)

# Default values used if environment variables and config file don't provide values
DEFAULT_VALUES = {
    "LOG_FILENAME": "mgit.log",
    "LOG_LEVEL": "DEBUG",
    "CON_LEVEL": "INFO",
    "DEFAULT_CONCURRENCY": "4",
    "DEFAULT_UPDATE_MODE": "skip",
}

# Ensure config directory exists before setting up file logging
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Migrate old dotenv configuration if it exists


# Configuration loading with YAML system
def get_config_value(key: str, default_value: Optional[str] = None) -> str:
    """
    Get a configuration value with the following priority:
    1. Environment variable (highest priority)
    2. Global YAML configuration
    3. Default value (lowest priority)
    """
    # First check environment
    env_value = os.environ.get(key)
    if env_value:
        return env_value

    # Map old keys to new YAML keys
    key_mapping = {
        "LOG_FILENAME": "log_filename",
        "LOG_LEVEL": "log_level",
        "CON_LEVEL": "console_level",
        "DEFAULT_CONCURRENCY": "default_concurrency",
        "DEFAULT_UPDATE_MODE": "default_update_mode",
    }

    # Get from YAML config
    yaml_key = key_mapping.get(key, key.lower())
    yaml_value = get_global_setting(yaml_key)

    if yaml_value is not None:
        return str(yaml_value)

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
        # Check for any Azure DevOps tokens in new environment variable name
        pat = os.getenv("AZURE_DEVOPS_TOKEN")
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
    log_filename,  # Use the absolute path
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
                    record.msg = (
                        f"Skipping disabled: [bold yellow]{repo_name}[/bold yellow]"
                    )
                except Exception:
                    pass

        # Call the parent class's emit method
        super().emit(record)


console_handler = ConsoleFriendlyRichHandler(
    rich_tracebacks=True,
    markup=True,
    show_path=False,  # Hide the file path in log messages
    show_time=False,  # Hide timestamp (already in the formatter)
    console=Console(stderr=True),
)
console_handler.setLevel(get_config_value("CON_LEVEL"))


def _has_mgit_handler(target_logger: logging.Logger, marker: str) -> bool:
    for existing in target_logger.handlers:
        if getattr(existing, "_mgit_handler", None) == marker:
            return True
    return False


# Attach handlers to the "mgit" logger so all mgit.* modules are captured.
mgit_logger = logging.getLogger("mgit")
mgit_logger.setLevel(get_config_value("LOG_LEVEL"))
mgit_logger.propagate = False

if not _has_mgit_handler(mgit_logger, "file"):
    file_handler._mgit_handler = "file"
    mgit_logger.addHandler(file_handler)

if not _has_mgit_handler(mgit_logger, "console"):
    console_handler._mgit_handler = "console"
    mgit_logger.addHandler(console_handler)

# Install credential-masking filter on the mgit logger so that every handler
# (console + file) automatically strips PATs and other secrets from messages.
from mgit.security.logging import SecurityLogFilter  # noqa: E402

_security_filter = SecurityLogFilter()
if not any(isinstance(f, SecurityLogFilter) for f in mgit_logger.filters):
    mgit_logger.addFilter(_security_filter)

logger = logging.getLogger(__name__)

console = Console()
app = typer.Typer(
    name="mgit",
    help=f"Multi-Git CLI Tool v{__version__} - A utility for managing repositories across "
    "multiple git platforms (Azure DevOps, GitHub, BitBucket) with bulk operations.",
    add_completion=False,
    no_args_is_help=False,  # We handle this ourselves with animated help
    add_help_option=False,  # We add our own --help handler
)


def _infer_provider_from_query(query: str) -> Optional[str]:
    try:
        from mgit.config.yaml_manager import get_provider_configs

        org = (query.split("/")[0] if query else "").strip()
        if not org or any(ch in org for ch in ["*", "?"]):
            return None
        candidates = []
        providers = get_provider_configs()
        for name, cfg in providers.items():
            try:
                ptype = detect_provider_type(name)
            except Exception:
                continue
            user = str(cfg.get("user", "")).strip().lower()
            url = str(cfg.get("url", "")).strip().lower()
            o = org.lower()
            if ptype in ("github", "bitbucket") and user and user.lower() == o:
                candidates.append(name)
                continue
            if (
                ptype == "azuredevops"
                and o
                and (f"/{o}" in url or url.endswith(f"/{o}"))
            ):
                candidates.append(name)
        if len(candidates) == 1:
            return candidates[0]
        return None
    except Exception:
        return None


def _ensure_repo_list(repos):
    try:
        if isinstance(repos, list):
            return repos
        # Async iterable
        if hasattr(repos, "__aiter__"):

            async def collect(ait):
                return [item async for item in ait]

            try:
                return asyncio.run(collect(repos))
            except RuntimeError:
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as ex:
                    fut = ex.submit(lambda: asyncio.run(collect(repos)))
                    return fut.result()
        # Sync iterable
        if hasattr(repos, "__iter__"):
            return list(repos)
        return []
    except Exception:
        return []


def version_callback(value: bool):
    if value:
        print(
            f"mgit version: {__version__}"
        )  # Updated version will be picked up here automatically
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main_options(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the application's version and exit.",
    ),
    help_flag: Optional[bool] = typer.Option(
        None,
        "--help",
        "-h",
        is_eager=True,
        help="Show this message and exit.",
    ),
):
    """
    Multi-Git CLI Tool - Manage repos across multiple git platforms easily.
    """
    # Handle --help flag or no subcommand (show animated help)
    if help_flag or ctx.invoked_subcommand is None:
        import io
        import sys

        from mgit.ui.help_animation import show_animated_help

        # Capture the help text - Typer/Rich prints it as a side effect
        # so we redirect stdout to capture it
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            ctx.get_help()  # This prints to stdout (now captured)
            help_text = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        try:
            show_animated_help(help_text)
        except KeyboardInterrupt:
            # User interrupted, exit cleanly
            raise typer.Exit(code=130) from None
        raise typer.Exit()


# -----------------------------------------------------------------------------
# Helper functions (moved to modules in Sprint 3A)
# -----------------------------------------------------------------------------
# embed_pat_in_url and sanitize_repo_name moved to mgit.git.utils


# -----------------------------------------------------------------------------
# Azure DevOps Manager - moved to mgit.legacy.azdevops_manager
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Git Manager is now imported from mgit.git module
# -----------------------------------------------------------------------------


# UpdateMode is now imported from bulk_operations as BulkUpdateMode
UpdateMode = BulkUpdateMode


# -----------------------------------------------------------------------------
# Login Command Helper Functions
# -----------------------------------------------------------------------------


def _find_existing_azdevops_config(organization: str) -> Optional[str]:
    """Find existing Azure DevOps configuration for the same organization."""
    try:
        providers = get_provider_configs()

        for name, config in providers.items():
            try:
                # Check if it's an Azure DevOps provider
                provider_type = detect_provider_type(name)
                if provider_type == "azuredevops":
                    # Compare organization URLs (normalize them)
                    config_org = config.get("url", "").rstrip("/")
                    input_org = organization.rstrip("/")

                    if config_org == input_org:
                        return name
            except Exception:
                # Skip providers with detection issues
                continue

    except Exception:
        # If config loading fails, assume no duplicates
        pass

    return None


def _find_existing_github_config() -> Optional[str]:
    """Find existing GitHub configuration."""
    try:
        providers = get_provider_configs()

        for name, _config in providers.items():
            try:
                # Check if it's a GitHub provider
                provider_type = detect_provider_type(name)
                if provider_type == "github":
                    return name
            except Exception:
                # Skip providers with detection issues
                continue

    except Exception:
        # If config loading fails, assume no duplicates
        pass

    return None


def _find_existing_bitbucket_config(username: str) -> Optional[str]:
    """Find existing BitBucket configuration for the same username."""
    try:
        providers = get_provider_configs()

        for name, config in providers.items():
            try:
                # Check if it's a BitBucket provider
                provider_type = detect_provider_type(name)
                if provider_type == "bitbucket":
                    # Compare usernames
                    config_username = config.get("user", "")
                    if config_username == username:
                        return name
            except Exception:
                # Skip providers with detection issues
                continue

    except Exception:
        # If config loading fails, assume no duplicates
        pass

    return None


def _test_provider_connection(
    provider_type: str, provider_config: dict[str, Any]
) -> bool:
    """Test provider connection with the given configuration."""
    try:
        # Create a temporary provider manager instance for testing
        # We'll create a temporary config entry, test it, and remove it
        temp_name = f"_temp_test_{provider_type}"

        # Temporarily add the config
        add_provider_config(temp_name, provider_config)

        try:
            # Test the connection using the temporary config
            test_manager = ProviderManager(provider_name=temp_name)
            connection_result = test_manager.test_connection()
            return connection_result
        finally:
            # Always clean up the temporary config
            with contextlib.suppress(Exception):
                remove_provider_config(temp_name)

    except Exception as e:
        logger.debug(f"Connection test failed: {e}")
        return False


# -----------------------------------------------------------------------------
# login Command
# -----------------------------------------------------------------------------
@app.command(
    help="Login to git provider and validate credentials. Supports Azure DevOps, GitHub, and BitBucket."
)
def login(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-cfg",
        help="Named provider configuration to test (e.g., 'work_ado', 'github_personal').",
    ),
    provider_type: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="Provider type for new configuration (azuredevops, github, bitbucket).",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Name for new provider configuration (e.g., 'my_github').",
    ),
    organization: Optional[str] = typer.Option(
        None,
        "--org",
        "-o",
        help="Provider organization/workspace URL for new configuration.",
    ),
    token: Optional[str] = typer.Option(
        None,
        "--token",
        "-t",
        help="Access token (PAT/API token) for new configuration.",
    ),
    store: bool = typer.Option(
        True,
        "--store/--no-store",
        help="Store new configuration in global config file (~/.config/mgit/config.yaml).",
    ),
):
    """
    Login and validate provider credentials using YAML configuration system.

    Supports testing existing configurations or creating new ones.
    """
    # Case 1: Test existing named configuration
    if config:
        try:
            provider_manager = ProviderManager(provider_name=config)
            if provider_manager.test_connection():
                console.print(
                    f"[green]✓[/green] Successfully connected using configuration '{config}'"
                )
                console.print(f"   Provider type: {provider_manager.provider_type}")
            else:
                console.print(
                    f"[red]✗[/red] Failed to connect using configuration '{config}'"
                )
                raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]✗[/red] Error testing configuration '{config}': {e}")
            raise typer.Exit(code=1) from e
        return

    # Case 2: Create new configuration
    if not provider_type:
        console.print(
            "[yellow]Available provider types: azuredevops, github, bitbucket[/yellow]"
        )
        provider_type = typer.prompt("Enter provider type")

    # Collect provider-specific configuration
    provider_config = {}

    if provider_type == "azuredevops":
        if not organization:
            organization = typer.prompt("Enter Azure DevOps organization URL")

        # Ensure URL format
        if not organization.startswith(("http://", "https://")):
            organization = f"https://{organization}"

        # Check for existing configuration with same organization
        existing_config = _find_existing_azdevops_config(organization)
        if existing_config:
            console.print(
                f"[yellow]⚠ Found existing Azure DevOps configuration '{existing_config}' for this organization.[/yellow]"
            )
            console.print(f"   Organization: {organization}")
            console.print()
            console.print("Options:")
            console.print(f"  1. Update existing '{existing_config}' configuration")
            console.print("  2. Create new configuration with different name")
            console.print("  3. Cancel")

            choice = typer.prompt("Choose option (1/2/3)", type=str)

            if choice == "1":
                name = existing_config
                console.print(f"[blue]Updating existing configuration '{name}'[/blue]")
            elif choice == "2":
                if not name:
                    suggested_name = f"ado_{organization.split('/')[-1]}_new"
                    name = typer.prompt(
                        "Enter name for new configuration", default=suggested_name
                    )
            else:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(code=0)
        else:
            if not name:
                suggested_name = f"ado_{organization.split('/')[-1]}"
                name = typer.prompt(
                    "Enter name for this provider configuration", default=suggested_name
                )

        if not token:
            token = typer.prompt("Enter Personal Access Token (PAT)", hide_input=True)

        # Use unified field structure
        provider_config = {
            "url": organization,
            "user": "azure",  # Azure DevOps doesn't require username
            "token": token,
            "provider_type": "azuredevops",
        }

    elif provider_type == "github":
        # Check for existing GitHub configurations
        existing_config = _find_existing_github_config()
        if existing_config:
            console.print(
                f"[yellow]⚠ Found existing GitHub configuration '{existing_config}'.[/yellow]"
            )
            console.print()
            console.print("Options:")
            console.print(f"  1. Update existing '{existing_config}' configuration")
            console.print(
                "  2. Create new configuration (e.g., for different GitHub account)"
            )
            console.print("  3. Cancel")

            choice = typer.prompt("Choose option (1/2/3)", type=str)

            if choice == "1":
                name = existing_config
                console.print(f"[blue]Updating existing configuration '{name}'[/blue]")
            elif choice == "2":
                if not name:
                    name = typer.prompt(
                        "Enter name for new GitHub configuration", default="github_new"
                    )
            else:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(code=0)
        else:
            if not name:
                name = typer.prompt(
                    "Enter name for this provider configuration",
                    default="github_personal",
                )

        if not token:
            token = typer.prompt("Enter GitHub token", hide_input=True)

        # Prompt for username if not provided via --org
        if not organization:
            organization = typer.prompt("Enter GitHub username or organization")

        # Use unified field structure
        provider_config = {
            "url": "https://github.com",
            "user": organization,
            "token": token,
            "provider_type": "github",
        }

    elif provider_type == "bitbucket":
        if not organization:
            organization = typer.prompt("Enter BitBucket username")

        # Check for existing BitBucket configurations with same username
        existing_config = _find_existing_bitbucket_config(organization)
        if existing_config:
            console.print(
                f"[yellow]⚠ Found existing BitBucket configuration '{existing_config}' for username '{organization}'.[/yellow]"
            )
            console.print()
            console.print("Options:")
            console.print(f"  1. Update existing '{existing_config}' configuration")
            console.print("  2. Create new configuration with different name")
            console.print("  3. Cancel")

            choice = typer.prompt("Choose option (1/2/3)", type=str)

            if choice == "1":
                name = existing_config
                console.print(f"[blue]Updating existing configuration '{name}'[/blue]")
            elif choice == "2":
                if not name:
                    name = typer.prompt(
                        "Enter name for new configuration",
                        default=f"bitbucket_{organization}_new",
                    )
            else:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(code=0)
        else:
            if not name:
                name = typer.prompt(
                    "Enter name for this provider configuration",
                    default=f"bitbucket_{organization}",
                )

        if not token:
            token = typer.prompt("Enter BitBucket app password", hide_input=True)

        # Optionally prompt for workspace
        workspace = typer.prompt(
            "Enter BitBucket workspace (optional, press Enter to skip)", default=""
        )

        # Use unified field structure
        provider_config = {
            "url": "https://bitbucket.org",
            "user": organization,
            "token": token,
            "provider_type": "bitbucket",
        }

        # Add workspace if provided
        if workspace:
            provider_config["workspace"] = workspace
    else:
        console.print(f"[red]✗[/red] Unknown provider type: {provider_type}")
        raise typer.Exit(code=1)

    # Test the configuration BEFORE saving
    console.print(f"[blue]Testing connection to {provider_type}...[/blue]")
    try:
        # Test the connection directly with the provider configuration
        connection_successful = _test_provider_connection(
            provider_type, provider_config
        )

        if connection_successful:
            console.print(f"[green]✓[/green] Successfully connected to {provider_type}")

            if store:
                # Only save if connection test succeeded
                add_provider_config(name, provider_config)
                console.print(
                    f"[green]✓[/green] Stored configuration '{name}' in ~/.config/mgit/config.yaml"
                )

                # Ask if this should be the default
                if Confirm.ask(f"Set '{name}' as the default provider?", default=True):
                    set_default_provider(name)
                    console.print(f"[green]✓[/green] Set '{name}' as default provider")
            else:
                console.print(
                    "[yellow]Configuration tested but not saved (use --store to save)[/yellow]"
                )
        else:
            console.print(
                f"[red]✗[/red] Failed to connect to {provider_type}. Please check your credentials."
            )
            console.print(
                "[yellow]Tip: Ensure your token has the required permissions and hasn't expired.[/yellow]"
            )
            raise typer.Exit(code=1)

    except Exception as e:
        error_msg = str(e).strip()
        if error_msg:
            console.print(
                f"[red]✗[/red] Error testing {provider_type} connection: {error_msg}"
            )
        else:
            console.print(f"[red]✗[/red] Error testing {provider_type} connection")

        if "expired" in error_msg.lower():
            console.print(
                "[yellow]Tip: Your access token appears to have expired. Please generate a new one.[/yellow]"
            )
        elif "access denied" in error_msg.lower():
            console.print(
                "[yellow]Tip: Check that your token has the required permissions for repository access.[/yellow]"
            )
        raise typer.Exit(code=1) from e


# store_credentials function removed - using YAML configuration system instead


# -----------------------------------------------------------------------------
# config Command
# -----------------------------------------------------------------------------
@app.command(help="Manage provider configurations and global settings.")
def config(
    list_providers: bool = typer.Option(
        False, "--list", "-l", help="List all configured providers."
    ),
    show_provider: Optional[str] = typer.Option(
        None, "--show", "-s", help="Show details for a specific provider."
    ),
    set_default: Optional[str] = typer.Option(
        None, "--set-default", "-d", help="Set the default provider."
    ),
    remove_provider: Optional[str] = typer.Option(
        None, "--remove", "-r", help="Remove a provider configuration."
    ),
    global_settings: bool = typer.Option(
        False, "--global", "-g", help="Show global settings."
    ),
):
    """
    Manage provider configurations and global settings using YAML config.

    Examples:
      mgit config --list                    # List all providers
      mgit config --show ado_myorg          # Show provider details
      mgit config --set-default github_personal  # Set default provider
      mgit config --remove old_config       # Remove provider
      mgit config --global                  # Show global settings
    """
    # List all providers
    if list_providers:
        providers = list_provider_names()
        if not providers:
            console.print("[yellow]No provider configurations found.[/yellow]")
            console.print(
                "Use 'mgit login' to create your first provider configuration."
            )
            return

        default_provider = get_default_provider_name()
        console.print("[bold]Configured Providers:[/bold]")

        for name in providers:
            try:
                provider_type = detect_provider_type(name)
                default_marker = (
                    " [green](default)[/green]" if name == default_provider else ""
                )
                console.print(
                    f"  [blue]{name}[/blue] ({provider_type}){default_marker}"
                )
            except Exception as e:
                console.print(f"  [yellow]{name}[/yellow] (type detection failed: {e})")

        console.print("\nConfig file: ~/.config/mgit/config.yaml")
        return

    # Show specific provider
    if show_provider:
        try:
            config = get_provider_config(show_provider)
            provider_type = detect_provider_type(show_provider)

            console.print(f"[bold]Provider Configuration: {show_provider}[/bold]")
            console.print(f"  Type: {provider_type}")

            # Mask sensitive fields
            for key, value in config.items():
                if key in ["token"]:
                    masked_value = (
                        value[:4] + "*" * (len(value) - 8) + value[-4:]
                        if len(value) > 8
                        else "*" * len(value)
                    )
                    console.print(f"  {key}: {masked_value}")
                else:
                    console.print(f"  {key}: {value}")

        except Exception as e:
            console.print(f"[red]✗[/red] Error showing provider '{show_provider}': {e}")
            raise typer.Exit(code=1) from e
        return

    # Set default provider
    if set_default:
        try:
            set_default_provider(set_default)
            console.print(f"[green]✓[/green] Set '{set_default}' as default provider")
        except Exception as e:
            console.print(f"[red]✗[/red] Error setting default provider: {e}")
            raise typer.Exit(code=1) from e
        return

    # Remove provider
    if remove_provider:
        try:
            remove_provider_config(remove_provider)
            console.print(
                f"[green]✓[/green] Removed provider configuration '{remove_provider}'"
            )
        except Exception as e:
            console.print(f"[red]✗[/red] Error removing provider: {e}")
            raise typer.Exit(code=1) from e
        return

    # Show global settings
    if global_settings:
        try:
            global_config = get_global_config()
            console.print("[bold]Global Settings:[/bold]")

            if global_config:
                for key, value in global_config.items():
                    console.print(f"  {key}: {value}")
            else:
                console.print("  No global settings configured.")

        except Exception as e:
            console.print(f"[red]✗[/red] Error showing global settings: {e}")
            raise typer.Exit(code=1) from e
        return

    # Default behavior - show help
    console.print("Use one of the options to manage configurations:")
    console.print("  --list           List all providers")
    console.print("  --show NAME      Show provider details")
    console.print("  --set-default    Set default provider")
    console.print("  --remove NAME    Remove provider")
    console.print("  --global         Show global settings")
    console.print("\nRun 'mgit config --help' for more details.")


# -----------------------------------------------------------------------------
# list Command
# -----------------------------------------------------------------------------
@app.command(name="list")
def list_command(
    query: str = typer.Argument(..., help="Query pattern (org/project/repo)"),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="Provider configuration name"
    ),
    format_type: str = typer.Option(
        "table", "--format", "-f", help="Output format (table, json)"
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Maximum results to return"
    ),
):
    """
    List repositories matching query pattern across providers.

    Examples:
      mgit list "*/*/*"                    # List all repos from all providers
      mgit list "myorg/*/*"                # List all repos from myorg org
      mgit list "*/*/pay*"                 # List repos ending in 'pay' from any org
      mgit list "myorg/MyProject/*"        # List all repos in specific project
    """

    async def do_list():
        try:
            results = await list_repositories(query, provider, format_type, limit)
            format_results(results, format_type)
        except MgitError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1) from e

    asyncio.run(do_list())


# -----------------------------------------------------------------------------
# diff Command
# -----------------------------------------------------------------------------
@app.command(name="diff")
def diff_command(
    path: Path = typer.Argument(
        ".",
        help="Path to repository or directory containing repositories.",
        exists=True,
        resolve_path=True,
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for change data (JSONL format). If not specified, prints to stdout.",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="Recursively scan directories for repositories.",
    ),
    concurrency: int = typer.Option(
        5,
        "--concurrency",
        "-c",
        help="Number of concurrent repository operations.",
        min=1,
        max=50,
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    save_changeset: bool = typer.Option(
        False,
        "--save-changeset",
        "-s",
        help="Save changesets to persistent storage for incremental processing.",
    ),
    changeset_name: str = typer.Option(
        "default",
        "--changeset-name",
        "-n",
        help="Name of changeset collection to use for storage.",
    ),
    incremental: bool = typer.Option(
        False,
        "--incremental",
        "-i",
        help="Only report changes since last saved changeset.",
    ),
    embed_content: bool = typer.Option(
        False,
        "--embed-content",
        help="Embed file content in the output for changed files.",
    ),
    content_strategy: str = typer.Option(
        "sample",
        "--content-strategy",
        help="Content embedding strategy: 'none', 'summary', 'sample', or 'full'.",
    ),
    content_memory_mb: int = typer.Option(
        100,
        "--content-memory-mb",
        help="Memory budget for content embedding in MB.",
        min=10,
        max=1000,
    ),
    discover_pattern: str = typer.Option(
        None,
        "--discover-pattern",
        help="Discover additional repositories using this pattern before scanning.",
    ),
    discover_provider: str = typer.Option(
        None,
        "--discover-provider",
        help="Provider to use for repository discovery.",
    ),
    merge_discovered: bool = typer.Option(
        False,
        "--merge-discovered/--no-merge-discovered",
        help="Merge discovered repositories with local scan results.",
    ),
) -> None:
    """
    Detect changes in Git repositories and output structured change information.

    This command scans repositories for uncommitted changes, recent commits,
    and repository metadata, outputting the results in JSONL format for
    further processing or analysis.

    Enhanced with repository discovery capabilities to automatically find
    and include additional repositories matching patterns.

    Examples:
      mgit diff /path/to/repos --output changes.jsonl --recursive
      mgit diff . --verbose
      mgit diff /single/repo --concurrency 1
      mgit diff . --embed-content --content-strategy=sample
      mgit diff . --embed-content --content-memory-mb=50
      mgit diff . --discover-pattern "myorg/*/*" --merge-discovered
    """
    from mgit.commands.diff import execute_diff_command

    execute_diff_command(
        path,
        output,
        recursive,
        concurrency,
        verbose,
        save_changeset,
        changeset_name,
        incremental,
        embed_content,
        content_strategy,
        content_memory_mb,
        discover_pattern,
        discover_provider,
        merge_discovered,
    )


# -----------------------------------------------------------------------------
# diff-remote Command
# -----------------------------------------------------------------------------
@app.command(name="diff-remote")
def diff_remote_command(
    pattern: str = typer.Argument(
        ...,
        help="Repository search pattern (e.g., 'myorg/*/*', 'github/*/*', '*abc/*').",
    ),
    local_root: Path = typer.Option(
        None,
        "--local-root",
        "-l",
        help="Root directory to scan for local repository clones.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    provider: str = typer.Option(
        None,
        "--provider",
        "-p",
        help="Specific provider to query (overrides pattern-based provider detection).",
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for discovery results (JSONL format). If not specified, prints to stdout.",
    ),
    save_changeset: bool = typer.Option(
        False,
        "--save-changeset",
        "-s",
        help="Save changesets to persistent storage.",
    ),
    changeset_name: str = typer.Option(
        "remote-discovery",
        "--changeset-name",
        "-n",
        help="Name of changeset collection for storage.",
    ),
    include_remote_only: bool = typer.Option(
        True,
        "--include-remote-only/--local-only",
        help="Include repositories found remotely but not locally cloned.",
    ),
    concurrency: int = typer.Option(
        10,
        "--concurrency",
        "-c",
        help="Number of concurrent repository operations.",
        min=1,
        max=50,
    ),
    limit: int = typer.Option(
        None,
        "--limit",
        help="Maximum number of repositories to process.",
        min=1,
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Discover repositories through provider queries and detect their changes.

    This command combines repository discovery across Git providers with
    change detection, allowing you to track changes in repositories matching
    specific patterns across multiple providers.

    Examples:
      mgit diff-remote "myorg/*/*" --local-root ./repos --save-changeset
      mgit diff-remote "github*/*/*" --provider github_work --verbose
      mgit diff-remote "*abc/*" --include-remote-only --output discovery.jsonl
    """
    from mgit.commands.diff_remote import execute_remote_diff_command

    execute_remote_diff_command(
        pattern,
        local_root,
        provider,
        output,
        save_changeset,
        changeset_name,
        include_remote_only,
        concurrency,
        limit,
        verbose,
    )


# -----------------------------------------------------------------------------
# status Command
# -----------------------------------------------------------------------------
@app.command(name="status")
def status_command(
    path: Path = typer.Argument(
        ".",
        help="The path to scan for repositories.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    concurrency: int = typer.Option(
        10, "--concurrency", "-c", help="Number of concurrent status checks."
    ),
    output: str = typer.Option(
        "table", "--output", "-o", help="Output format (table, json)."
    ),
    show_clean: bool = typer.Option(
        False,
        "--show-clean",
        "--all",
        help="Show all repositories, not just those with changes.",
    ),
    fetch: bool = typer.Option(
        False, "--fetch", help="Run 'git fetch' before checking status."
    ),
    fail_on_dirty: bool = typer.Option(
        False,
        "--fail-on-dirty",
        help="Exit with an error code if any repository has changes.",
    ),
):
    """
    Get a high-performance status report for all Git repositories within a directory.
    """

    async def do_status():
        results = []
        try:
            results = await get_repository_statuses(
                path, concurrency, fetch, json_mode=(output == "json")
            )
            if output != "json":
                logger.info(
                    f"Got {len(results)} results, displaying in {output} format."
                )
            display_status_results(results, output, show_clean)
            if fail_on_dirty and any(not r.is_clean for r in results):
                raise typer.Exit(code=1)
        except MgitError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1) from e

    asyncio.run(do_status())


# -----------------------------------------------------------------------------
# sync Command
# -----------------------------------------------------------------------------
@app.command()
def sync(
    pattern: Optional[str] = typer.Argument(
        None, help="Repository pattern (remote) or local path (local mode)"
    ),
    path: Optional[str] = typer.Argument(
        None, help="Target path for remote sync (default: .)"
    ),
    filter_pattern: Optional[str] = typer.Option(
        None, "--filter", help="Explicit remote pattern (forces remote mode)"
    ),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="Specific provider (otherwise search all)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Delete and re-clone all repositories"
    ),
    concurrency: Optional[int] = typer.Option(
        None, "--concurrency", "-c", help="Number of concurrent operations"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes"
    ),
    progress: bool = typer.Option(
        True, "--progress/--no-progress", help="Show progress bar"
    ),
    summary: bool = typer.Option(
        True, "--summary/--no-summary", help="Show detailed summary"
    ),
    hierarchy: bool = typer.Option(
        False,
        "--hierarchy",
        help="Use hierarchical directory structure (host/org/project/repo) instead of flat",
    ),
):
    """
    Synchronize repositories locally or with remote providers.

    🚀 UNIFIED REPOSITORY SYNC - replaces clone-all and pull-all

    Intelligently handles your repository synchronization:
    - Clones repositories that don't exist locally
    - Pulls updates for repositories that already exist
    - Handles conflicts and errors gracefully
    - Provides detailed progress and summary reporting

    DIRECTORY LAYOUT (default: flat):
    - Flat (default): Repos cloned directly into target (./repo-name/)
    - Hierarchical (--hierarchy): Full path structure (./host/org/project/repo/)

    When using flat layout, repos with the same name from different orgs
    are automatically disambiguated (e.g., repo_org-a, repo_org-b).

    Remote PATTERN can be:
    - Exact: myorg/myproject/myrepo
    - Wildcards: myorg/*/myrepo, */myproject/*, myorg/*/*
    - Cross-provider: */*/* (searches ALL providers)

    When no --provider specified, patterns search ALL configured providers.

    Examples:
        # Local walk mode (current directory)
        mgit sync

        # Local walk mode (specific path)
        mgit sync ./workspace

        # Daily workspace sync (flat layout - default)
        mgit sync "myorg/*/*" ./workspace

        # Use hierarchical directory structure
        mgit sync "myorg/*/*" ./workspace --hierarchy

        # Force remote sync even if pattern matches a path
        mgit sync --filter "myorg/*/*" ./workspace

        # Preview changes first
        mgit sync "myorg/*/*" ./workspace --dry-run

        # Nuclear option - fresh everything
        mgit sync "myorg/*/*" ./workspace --force

        # Quiet sync for scripts
        mgit sync "myorg/*/*" ./workspace --no-progress --no-summary
    """
    if filter_pattern:
        target_path = path or pattern or "."
        asyncio.run(
            sync_command(
                filter_pattern,
                target_path,
                provider,
                force,
                concurrency,
                dry_run,
                progress,
                summary,
                hierarchy,
            )
        )
        return

    if path is not None:
        if pattern is None:
            console.print(
                "[red]Error:[/red] Pattern is required when a path is provided."
            )
            raise typer.Exit(code=1)
        asyncio.run(
            sync_command(
                pattern,
                path,
                provider,
                force,
                concurrency,
                dry_run,
                progress,
                summary,
                hierarchy,
            )
        )
        return

    if pattern is None:
        asyncio.run(
            sync_local_command(".", force, concurrency, dry_run, progress, summary)
        )
        return

    candidate_path = Path(pattern).expanduser()
    if candidate_path.exists():
        asyncio.run(
            sync_local_command(
                str(candidate_path), force, concurrency, dry_run, progress, summary
            )
        )
        return

    asyncio.run(
        sync_command(
            pattern,
            ".",
            provider,
            force,
            concurrency,
            dry_run,
            progress,
            summary,
            hierarchy,
        )
    )


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

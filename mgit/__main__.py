#!/usr/bin/env python3
"""mgit - Multi-repository Git management tool."""

import sys
import traceback
from pathlib import Path
from typing import List, Optional

import typer
from typer import Argument, Option
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from mgit import __version__
from mgit.config import ConfigManager
from mgit.monitoring.cli import monitoring_app
from mgit.monitoring.logger_compat import get_logger, configure_logging
from mgit.presentation.cli.commands.bulk_ops import app as bulk_ops_app
from mgit.application.container import get_container
from mgit.exceptions import MgitError
from mgit.providers.exceptions import ProviderNotConfiguredError
from mgit.security.monitor import SecurityMonitor

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Create the main app
app = typer.Typer(
    help="Multi-repository Git management tool",
    no_args_is_help=True,
    add_completion=True,
    pretty_exceptions_enable=False,
)

# Add sub-commands
app.add_typer(bulk_ops_app, name="bulk")
app.add_typer(monitoring_app, name="monitor")

# Console for rich output
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"mgit version {__version__}")
        raise typer.Exit()


def config_callback(show: bool = False) -> None:
    """Manage configuration."""
    if show:
        config = get_container().config_manager.config
        console.print("\n[bold]Current Configuration:[/bold]")
        
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Setting", style="cyan")
        table.add_column("Value")
        
        # General settings
        table.add_row("Config File", str(get_container().config_manager.config_path))
        table.add_row("Default Concurrency", str(config.get("default_concurrency", 4)))
        
        # Provider settings
        for provider in ["azure_devops", "github", "bitbucket"]:
            provider_config = config.get(provider, {})
            if provider_config:
                table.add_row(f"{provider.title()} Org", provider_config.get("org", "Not set"))
                table.add_row(
                    f"{provider.title()} Token", 
                    "****" if provider_config.get("pat") or provider_config.get("token") else "Not set"
                )
        
        console.print(table)
        raise typer.Exit()


@app.command()
def login(
    org: str = Option(..., "--org", help="Organization URL (e.g., https://dev.azure.com/myorg)"),
    token: str = Option(..., "--token", "--pat", help="Personal Access Token"),
    provider: Optional[str] = Option(None, "--provider", help="Provider type (azure-devops, github, bitbucket)"),
) -> None:
    """Configure authentication for a Git provider."""
    try:
        container = get_container()
        config_manager = container.config_manager
        
        # Auto-detect provider if not specified
        if provider is None:
            if "dev.azure.com" in org or "visualstudio.com" in org:
                provider = "azure-devops"
            elif "github.com" in org:
                provider = "github"
            elif "bitbucket.org" in org:
                provider = "bitbucket"
            else:
                console.print("[red]Could not auto-detect provider. Please specify with --provider[/red]")
                raise typer.Exit(1)
        
        # Normalize provider name
        provider_key = provider.lower().replace("-", "_")
        
        # Update configuration
        config = config_manager.config
        if provider_key not in config:
            config[provider_key] = {}
        
        config[provider_key]["org"] = org
        
        # Use appropriate token field based on provider
        if provider_key == "github":
            config[provider_key]["token"] = token
        else:
            config[provider_key]["pat"] = token
        
        # Save configuration
        config_manager.save_config(config)
        
        console.print(f"[green]✓[/green] Successfully configured {provider} authentication")
        console.print(f"  Organization: {org}")
        console.print(f"  Token: {'*' * 8}...")
        
    except Exception as e:
        logger.error(f"Login failed: {e}")
        console.print(f"[red]Error during login: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def clone_all(
    project: str = Argument(..., help="The project to clone repositories from"),
    destination: Path = Argument(..., help="The destination directory for cloned repositories"),
    concurrency: int = Option(4, "-c", "--concurrency", help="Number of concurrent operations"),
    update: str = Option("skip", "-u", "--update", help="How to handle existing repositories (skip/pull/force)"),
    exclude: Optional[List[str]] = Option(None, "-e", "--exclude", help="Repositories to exclude"),
    include: Optional[List[str]] = Option(None, "-i", "--include", help="Only include these repositories"),
    dry_run: bool = Option(False, "--dry-run", help="Show what would be done without doing it"),
) -> None:
    """Clone all repositories from a project."""
    # Import here to avoid circular imports
    from mgit.presentation.cli.commands.bulk_ops import clone_all as bulk_clone_all
    from mgit.domain.models.operations import UpdateMode
    
    # Convert update string to enum
    update_mode = UpdateMode(update)
    
    # Delegate to the bulk operations command
    bulk_clone_all(
        project=project,
        destination=destination,
        concurrency=concurrency,
        update_mode=update_mode,
        exclude=exclude,
        include=include,
        dry_run=dry_run,
    )


@app.command()
def pull_all(
    project: str = Argument(..., help="The project to pull repositories from"),
    repositories_path: Path = Argument(..., help="The directory containing the repositories"),
    concurrency: int = Option(4, "-c", "--concurrency", help="Number of concurrent operations"),
    exclude: Optional[List[str]] = Option(None, "-e", "--exclude", help="Repositories to exclude"),
    include: Optional[List[str]] = Option(None, "-i", "--include", help="Only include these repositories"),
    dry_run: bool = Option(False, "--dry-run", help="Show what would be done without doing it"),
) -> None:
    """Pull updates for all repositories in a project."""
    # Import here to avoid circular imports
    from mgit.presentation.cli.commands.bulk_ops import pull_all as bulk_pull_all
    
    # Delegate to the bulk operations command
    bulk_pull_all(
        project=project,
        repositories_path=repositories_path,
        concurrency=concurrency,
        exclude=exclude,
        include=include,
        dry_run=dry_run,
    )


@app.command()
def list_projects(
    provider: Optional[str] = Option(None, "--provider", help="Filter by provider (azure-devops, github, bitbucket)"),
) -> None:
    """List all available projects."""
    try:
        container = get_container()
        provider_manager = container.provider_manager
        
        if provider:
            providers = [provider]
        else:
            # List from all configured providers
            config = container.config_manager.config
            providers = []
            if config.get("azure_devops", {}).get("pat"):
                providers.append("azure-devops")
            if config.get("github", {}).get("token"):
                providers.append("github")
            if config.get("bitbucket", {}).get("pat"):
                providers.append("bitbucket")
        
        if not providers:
            console.print("[yellow]No providers configured. Use 'mgit login' to configure a provider.[/yellow]")
            raise typer.Exit(0)
        
        for provider_name in providers:
            try:
                console.print(f"\n[bold]{provider_name.title()} Projects:[/bold]")
                projects = provider_manager.list_projects(provider=provider_name)
                
                if not projects:
                    console.print("  [dim]No projects found[/dim]")
                else:
                    for project in projects:
                        console.print(f"  • {project}")
                        
            except ProviderNotConfiguredError:
                console.print(f"  [yellow]{provider_name} is not configured[/yellow]")
            except Exception as e:
                console.print(f"  [red]Error listing projects: {e}[/red]")
                
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_repos(
    project: str = Argument(..., help="The project to list repositories from"),
    tree: bool = Option(False, "--tree", help="Display as a tree structure"),
) -> None:
    """List all repositories in a project."""
    try:
        container = get_container()
        provider_adapter = container.provider_adapter
        
        # Get repositories
        repos = provider_adapter.list_repositories(project)
        
        if not repos:
            console.print(f"[yellow]No repositories found in project '{project}'[/yellow]")
            raise typer.Exit(0)
        
        if tree:
            # Display as tree
            tree_obj = Tree(f"[bold]{project}[/bold]")
            for repo in repos:
                tree_obj.add(f"📁 {repo.name}")
            console.print(tree_obj)
        else:
            # Display as table
            table = Table(title=f"Repositories in {project}")
            table.add_column("Repository", style="cyan")
            table.add_column("URL", style="blue")
            
            for repo in repos:
                table.add_row(repo.name, repo.clone_url)
            
            console.print(table)
            
    except Exception as e:
        logger.error(f"Failed to list repositories: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    project: str = Argument(..., help="The project to check status for"),
    repositories_path: Path = Argument(..., help="The directory containing the repositories"),
) -> None:
    """Check the status of all repositories in a project."""
    try:
        from mgit.commands.status import check_status
        
        # Delegate to the status command
        check_status(project, repositories_path)
        
    except ImportError:
        # Status command not yet refactored
        console.print("[red]Status command is being refactored[/red]")
        raise typer.Exit(1)


@app.callback()
def main(
    version: bool = Option(None, "--version", callback=version_callback, is_eager=True, help="Show version"),
    config: bool = Option(None, "--config", "--show-config", callback=config_callback, is_eager=True, help="Show configuration"),
    debug: bool = Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Multi-repository Git management tool."""
    if debug:
        # Reconfigure logging with debug level
        configure_logging(level="DEBUG")
        logger.debug("Debug logging enabled")


def run() -> None:
    """Run the CLI application."""
    try:
        # Initialize security monitor
        security_monitor = SecurityMonitor()
        
        # Run the app
        app()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except MgitError as e:
        logger.error(f"mgit error: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        console.print(f"[red]Unexpected error: {e}[/red]")
        if "--debug" in sys.argv:
            console.print("\n[dim]Traceback:[/dim]")
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run()
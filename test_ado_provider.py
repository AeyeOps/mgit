#!/usr/bin/env python3
"""Test script for ado_pdidev provider configuration."""

import asyncio
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# Add mgit to path
sys.path.insert(0, str(Path(__file__).parent))

# Set HOME to Steve's directory to find config
os.environ['HOME'] = '/home/steve'

from mgit.config.yaml_manager import get_provider_config
from mgit.providers.azdevops import AzureDevOpsProvider
from mgit.exceptions import AuthenticationError, ProviderError

console = Console()


async def test_ado():
    """Test Azure DevOps provider with ado_pdidev configuration."""
    
    try:
        # Load configuration
        console.print("\n[bold blue]Loading ado_pdidev configuration...[/bold blue]")
        config = get_provider_config('ado_pdidev')
        
        if not config:
            console.print("[red]Error: ado_pdidev configuration not found![/red]")
            return
            
        # Display loaded configuration (masking sensitive data)
        console.print(Panel(
            f"[green]Configuration loaded successfully[/green]\n"
            f"URL: {config.get('url', 'Not set')}\n"
            f"User: {config.get('user', 'Not set')}\n"
            f"Token: {'*' * 10 if config.get('token') else 'Not set'}\n"
            f"Workspace: {config.get('workspace', 'Not set')}",
            title="Configuration"
        ))
        
        # Create provider instance
        console.print("\n[bold blue]Creating AzureDevOpsProvider instance...[/bold blue]")
        provider = AzureDevOpsProvider(config)
        
        # Authenticate
        console.print("\n[bold blue]Authenticating...[/bold blue]")
        auth_result = await provider.authenticate()
        
        if auth_result:
            console.print("[green]✓ Authentication successful![/green]")
        else:
            console.print("[red]✗ Authentication failed![/red]")
            return
            
        # List organizations
        console.print("\n[bold blue]Fetching organizations...[/bold blue]")
        organizations = await provider.list_organizations()
        
        if not organizations:
            console.print("[yellow]No organizations found[/yellow]")
            return
            
        # Display organizations in a table
        org_table = Table(title="Organizations Found")
        org_table.add_column("Name", style="cyan")
        org_table.add_column("Provider", style="green")
        org_table.add_column("URL", style="blue")
        
        for org in organizations:
            org_table.add_row(
                org.name,
                org.provider,
                org.url
            )
        
        console.print(org_table)
        
        # List projects for the first organization
        first_org = organizations[0]
        console.print(f"\n[bold blue]Fetching projects for organization: {first_org.name}...[/bold blue]")
        
        projects = await provider.list_projects(organization=first_org.name)
        
        if not projects:
            console.print("[yellow]No projects found[/yellow]")
            return
            
        # Display projects in a table
        project_table = Table(title=f"Projects in {first_org.name}")
        project_table.add_column("Name", style="cyan")
        project_table.add_column("Organization", style="green")
        project_table.add_column("Description", style="blue")
        
        for project in projects[:5]:  # Show first 5 projects
            project_table.add_row(
                project.name,
                project.organization,
                project.description or "No description"
            )
        
        console.print(project_table)
        
        if len(projects) > 5:
            console.print(f"\n[dim]... and {len(projects) - 5} more projects[/dim]")
        
        # List repositories for the first project
        first_project = projects[0]
        console.print(f"\n[bold blue]Fetching repositories for project: {first_project.name}...[/bold blue]")
        
        repositories = []
        async for repo in provider.list_repositories(
            organization=first_org.name,
            project=first_project.name
        ):
            repositories.append(repo)
        
        if not repositories:
            console.print("[yellow]No repositories found[/yellow]")
            return
            
        # Display repositories in a table
        repo_table = Table(title=f"Repositories in {first_project.name}")
        repo_table.add_column("Name", style="cyan")
        repo_table.add_column("Clone URL", style="green", max_width=50)
        repo_table.add_column("Default Branch", style="yellow")
        repo_table.add_column("Is Private", style="magenta")
        
        # Show first 10 repositories
        for repo in repositories[:10]:
            # Truncate long URLs for display
            clone_url = repo.clone_url
            if len(clone_url) > 47:
                clone_url = clone_url[:44] + "..."
            
            repo_table.add_row(
                repo.name,
                clone_url,
                repo.default_branch,
                "Yes" if repo.is_private else "No"
            )
            
        console.print(repo_table)
        
        # Show full clone URL for reference
        if repositories:
            console.print(f"\n[dim]Full clone URL example: {repositories[0].clone_url}[/dim]")
        
        if len(repositories) > 10:
            console.print(f"\n[dim]... and {len(repositories) - 10} more repositories[/dim]")
        
        # Summary
        console.print(Panel(
            f"[green bold]Test Summary[/green bold]\n"
            f"Total Organizations: {len(organizations)}\n"
            f"Total Projects: {len(projects)}\n"
            f"Total Repositories in {first_project.name}: {len(repositories)}",
            title="Results",
            border_style="green"
        ))
        
    except AuthenticationError as e:
        console.print(f"[red]Authentication Error: {e}[/red]")
    except ProviderError as e:
        console.print(f"[red]Provider Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected Error: {type(e).__name__}: {e}[/red]")
        import traceback
        traceback.print_exc()


async def main():
    """Main entry point."""
    console.print(Panel(
        "[bold]Azure DevOps Provider Test[/bold]\n"
        "Testing ado_pdidev configuration",
        title="mgit Provider Test",
        border_style="blue"
    ))
    
    await test_ado()
    
    console.print("\n[bold blue]Test completed![/bold blue]")


if __name__ == "__main__":
    asyncio.run(main())
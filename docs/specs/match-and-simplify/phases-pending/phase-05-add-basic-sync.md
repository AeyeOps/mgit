# Phase 5: Add Basic Sync Command

## Summary
Implement the new unified `sync` command that replaces both `clone-all` and `pull-all` with simpler, more intuitive behavior. The sync command intelligently clones missing repositories and pulls updates for existing ones, eliminating user confusion about which command to use.

## Effort Estimate
2 hours

## Dependencies
- Phase 1: Pattern matching logic extracted
- Phase 2: Multi-provider resolution logic extracted
- Phase 3: Multi-provider support in clone-all working
- Phase 4: Multi-provider support in pull-all working

## Implementation Details

### Files to Create
- `mgit/commands/sync.py` - New sync command implementation

### Files to Modify
- `mgit/__main__.py` - Add sync command registration
- Tests for the new sync command

### Key Changes

#### 1. Create Sync Command (`mgit/commands/sync.py`)

```python
"""
Sync command implementation.

Provides a unified interface for repository synchronization that combines
the functionality of clone-all and pull-all into a single, intuitive command.
"""
import asyncio
import logging
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.prompt import Confirm

from mgit.commands.bulk_operations import (
    BulkOperationProcessor,
    OperationType, 
    UpdateMode as BulkUpdateMode,
    check_force_mode_confirmation,
)
from mgit.config.yaml_manager import get_global_setting, list_provider_names
from mgit.exceptions import MgitError
from mgit.git import GitManager
from mgit.providers.manager import ProviderManager
from mgit.providers.base import Repository
from mgit.utils.pattern_matching import analyze_pattern
from mgit.utils.multi_provider_resolver import resolve_repositories_multi_provider

logger = logging.getLogger(__name__)
console = Console()

async def resolve_repositories_for_sync(
    pattern: str,
    provider_manager,
    explicit_provider: Optional[str] = None,
    explicit_url: Optional[str] = None
) -> tuple[List[Repository], bool]:
    """
    Resolve repositories for sync operation with clear logging.
    
    Returns:
        Tuple of (repositories, is_multi_provider_operation)
    """
    pattern_analysis = analyze_pattern(pattern, explicit_provider, explicit_url)
    
    # Validate pattern
    if pattern_analysis.validation_errors:
        for error in pattern_analysis.validation_errors:
            console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1)

    logger.debug(f"Resolving repositories for sync pattern: {pattern}")
    
    try:
        if pattern_analysis.is_multi_provider:
            # Multi-provider search
            available_providers = list_provider_names()
            console.print(f"[blue]Synchronizing across {len(available_providers)} providers:[/blue] {', '.join(available_providers)}")
            
            if not available_providers:
                console.print("[red]Error:[/red] No providers configured. Run 'mgit login' to add providers.")
                raise typer.Exit(code=1)
            
            result = await resolve_repositories_multi_provider(
                pattern=pattern_analysis.normalized_pattern,
                explicit_provider=None,
                explicit_url=None,
                limit=None,
            )
            repositories = result.repositories
            
            # Log detailed results
            console.print(
                f"[green]Found {len(repositories)} repositories[/green] "
                f"from {len(result.successful_providers)} providers"
            )
            
            if result.failed_providers:
                console.print(
                    f"[yellow]Warning:[/yellow] Failed to query {len(result.failed_providers)} providers: "
                    f"{', '.join(result.failed_providers)}"
                )
            
            if result.duplicates_removed > 0:
                console.print(f"[blue]Info:[/blue] Removed {result.duplicates_removed} duplicate repositories")
            
            return repositories, True
        
        elif pattern_analysis.is_pattern:
            # Single provider pattern search
            provider_name = provider_manager.provider_name if provider_manager else None
            console.print(f"[blue]Synchronizing from provider:[/blue] {provider_name}")
            
            result = await resolve_repositories_multi_provider(
                pattern=pattern_analysis.normalized_pattern,
                explicit_provider=provider_name,
                explicit_url=explicit_url,
                limit=None,
            )
            repositories = result.repositories
            
            console.print(f"[green]Found {len(repositories)} repositories[/green] in provider '{provider_name}'")
            
            return repositories, False
        
        else:
            # Non-pattern query: use provider manager directly
            repositories = provider_manager.list_repositories(pattern)
            if hasattr(repositories, '__len__'):
                repo_list = list(repositories) 
            else:
                repo_list = [repositories] if repositories else []
            
            console.print(f"[green]Found {len(repo_list)} repositories[/green] for exact match")
            
            return repo_list, False

    except Exception as e:
        logger.error(f"Error resolving repositories: {e}")
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

def sync_command(
    pattern: str = typer.Argument(..., help="Repository pattern (org/project/repo)"),
    path: str = typer.Argument(".", help="Local path to synchronize repositories into"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Specific provider (otherwise search all)"),
    force: bool = typer.Option(False, "--force", "-f", help="Delete and re-clone all repositories"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c", help="Number of concurrent operations"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
) -> None:
    """
    Synchronize repositories with remote providers.
    
    The sync command intelligently:
    - Clones repositories that don't exist locally
    - Pulls updates for repositories that already exist
    - Optionally force re-clones everything with --force
    
    PATTERN can be:
    - Exact match: myorg/myproject/myrepo
    - Wildcard patterns: myorg/*/myrepo, */myproject/*, myorg/*/*
    - Cross-provider: */*/* (searches ALL providers)

    When no --provider is specified, patterns search ALL configured providers.
    
    Examples:
        # Initial sync - clones all myorg repositories
        mgit sync "myorg/*/*" ./workspace

        # Daily update - pulls changes, clones any new repos  
        mgit sync "myorg/*/*" ./workspace

        # Fresh start - deletes and re-clones everything
        mgit sync "myorg/*/*" ./workspace --force

        # Specific provider only
        mgit sync "myorg/*/*" ./workspace --provider github_work

        # Preview what would be done
        mgit sync "myorg/*/*" ./workspace --dry-run
    """
    # Load configuration
    default_concurrency = int(get_global_setting("default_concurrency") or 4)
    if concurrency is None:
        concurrency = default_concurrency

    # Initialize managers
    git_manager = GitManager()
    
    # Setup provider manager
    if provider:
        provider_manager = ProviderManager(provider_name=provider)
    else:
        provider_manager = ProviderManager()  # Will be used for non-pattern queries only

    # Setup target path
    target_path = Path(path).resolve()
    target_path.mkdir(parents=True, exist_ok=True)
    
    console.print(f"[blue]Synchronizing to:[/blue] {target_path}")

    # Resolve repositories
    repositories, is_multi_provider = asyncio.run(
        resolve_repositories_for_sync(pattern, provider_manager, provider, None)
    )

    if not repositories:
        console.print(f"[yellow]No repositories found for pattern '{pattern}'[/yellow]")
        return

    if dry_run:
        console.print(f"\n[yellow]DRY RUN - Would sync {len(repositories)} repositories:[/yellow]")
        for repo in repositories:
            local_path = target_path / repo.organization / (repo.project or "") / repo.name
            local_path = Path(str(local_path).replace("//", "/"))  # Clean double slashes
            
            if local_path.exists():
                if local_path.is_dir() and (local_path / ".git").exists():
                    action = "[blue]PULL[/blue] (update existing)"
                else:
                    action = "[yellow]SKIP[/yellow] (not a git repo)"
            else:
                action = "[green]CLONE[/green] (create new)"
                
            if force:
                action = "[red]FORCE CLONE[/red] (delete and re-clone)"
                
            console.print(f"  {action}: {repo.organization}/{repo.name}")
        
        return

    # Determine update mode based on force flag
    update_mode = BulkUpdateMode.force if force else BulkUpdateMode.pull

    # Handle force confirmation
    if force:
        force_confirmed = Confirm.ask(
            f"[red]WARNING:[/red] Force mode will DELETE and re-clone {len(repositories)} repositories. "
            f"All local changes will be lost. Continue?"
        )
        if not force_confirmed:
            console.print("Sync cancelled.")
            return
    
    confirmed_force_remove = force
    dirs_to_remove = []  # Will be calculated by processor if needed

    # Create processor - use appropriate provider manager
    if is_multi_provider:
        # For multi-provider operations, let the processor handle individual repo URLs
        processor_provider_manager = ProviderManager()
    else:
        processor_provider_manager = provider_manager
        
    processor = BulkOperationProcessor(
        git_manager=git_manager,
        provider_manager=processor_provider_manager,
        operation_type=OperationType.clone,  # Sync uses clone operation type but with pull update mode
    )

    console.print(f"\n[blue]Synchronizing {len(repositories)} repositories...[/blue]")
    
    # Run the sync operation
    try:
        failures = await processor.process_bulk_operation(
            repositories=repositories,
            target_path=target_path,
            concurrency=concurrency,
            update_mode=update_mode,
            confirmed_force_remove=confirmed_force_remove,
            dirs_to_remove=dirs_to_remove,
        )

        # Report results
        success_count = len(repositories) - len(failures)
        
        if failures:
            console.print(f"\n[yellow]Sync completed with issues:[/yellow]")
            console.print(f"  [green]Successful:[/green] {success_count}")
            console.print(f"  [red]Failed:[/red] {len(failures)}")
            
            console.print(f"\n[red]Failures:[/red]")
            for failure in failures:
                console.print(f"  ❌ {failure}")
                
            raise typer.Exit(code=1)
        else:
            console.print(f"\n[green]✅ Successfully synchronized {success_count} repositories![/green]")

    except KeyboardInterrupt:
        console.print(f"\n[yellow]Sync interrupted by user[/yellow]")
        raise typer.Exit(code=130)
    except Exception as e:
        console.print(f"\n[red]Sync failed:[/red] {e}")
        logger.error(f"Sync operation failed: {e}")
        raise typer.Exit(code=1)
```

#### 2. Register Sync Command (`mgit/__main__.py`)

Add the sync command to the main app:

```python
# Import sync command
from mgit.commands.sync import sync_command

# Add command registration  
app.command("sync", help="Synchronize repositories (clone missing, pull existing)")(sync_command)
```

#### 3. Add Command Alias Support

To help with migration, add the sync command in a more discoverable way:

```python
# In mgit/__main__.py, add after other command definitions:

@app.command("sync")
def sync_repositories(
    pattern: str = typer.Argument(..., help="Repository pattern (org/project/repo)"),
    path: str = typer.Argument(".", help="Local path to synchronize repositories into"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Specific provider (otherwise search all)"),
    force: bool = typer.Option(False, "--force", "-f", help="Delete and re-clone all repositories"),  
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c", help="Number of concurrent operations"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
):
    """
    Synchronize repositories with remote providers.
    
    🚀 NEW UNIFIED COMMAND - replaces clone-all and pull-all
    
    Intelligently clones missing repositories and pulls updates for existing ones.
    """
    return sync_command(pattern, path, provider, force, concurrency, dry_run)
```

## Testing Strategy

### Unit Tests
Create `tests/unit/test_sync_command.py`:

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from mgit.commands.sync import sync_command, resolve_repositories_for_sync

class TestSyncCommand:
    def test_sync_command_help(self):
        """Test that sync command has proper help text."""
        # Test that the command is properly documented
        pass
    
    def test_resolve_repositories_multi_provider(self):
        """Test multi-provider repository resolution for sync."""
        pass
    
    def test_resolve_repositories_single_provider(self):
        """Test single provider resolution for sync."""
        pass
    
    def test_sync_dry_run_output(self):
        """Test that dry run shows correct actions for each repository."""
        pass
    
    def test_sync_force_confirmation(self):
        """Test that force mode requires confirmation."""
        pass
    
    @pytest.mark.asyncio
    async def test_sync_mixed_repositories(self):
        """Test sync behavior with mix of existing and new repositories."""
        # Mock some repos existing locally, others not
        # Verify correct clone vs pull actions
        pass
```

### Integration Tests
Create `tests/integration/test_sync_integration.py`:

```python
class TestSyncIntegration:
    @pytest.mark.integration
    def test_sync_replaces_clone_all(self):
        """Test that sync command can replace clone-all functionality."""
        # Compare sync results with what clone-all would produce
        pass
    
    @pytest.mark.integration
    def test_sync_replaces_pull_all(self):
        """Test that sync command can replace pull-all functionality."""
        # Compare sync results with what pull-all would produce
        pass
    
    @pytest.mark.integration
    def test_sync_multi_provider_pattern(self):
        """Test that sync properly searches all providers for patterns."""
        pass
```

### Manual Verification Commands

Test the new sync command thoroughly:

```bash
# Basic functionality
poetry run mgit sync "myorg/*/*" /tmp/sync-test --dry-run
poetry run mgit sync "myorg/*/*" /tmp/sync-test

# Multi-provider behavior
poetry run mgit sync "*/*/*" /tmp/sync-all --provider github_work
poetry run mgit sync "*/project/*" /tmp/sync-pattern --dry-run

# Force mode
poetry run mgit sync "myorg/test/*" /tmp/sync-force --force --dry-run

# Compare with existing commands (should find same repositories)
poetry run mgit list "myorg/*/*" --format json > /tmp/list-output.json
poetry run mgit sync "myorg/*/*" /tmp/sync-test --dry-run 2>&1 | grep "Found.*repositories"

# Test error handling
poetry run mgit sync "invalid//pattern" /tmp/test  # Should show validation error
poetry run mgit sync "org/proj/repo" /tmp/test --provider nonexistent  # Should show provider error
```

### Performance Comparison

Create a simple performance test:

```bash
#!/bin/bash
# Compare sync performance with clone-all + pull-all

PATTERN="myorg/*/*"
TESTDIR="/tmp/perf-test"

echo "Testing sync command performance..."
time poetry run mgit sync "$PATTERN" "$TESTDIR-sync" --dry-run

echo "Testing clone-all command performance..."  
time poetry run mgit clone-all "$PATTERN" "$TESTDIR-clone" --dry-run

echo "Performance comparison complete"
```

## Success Criteria
- [ ] Sync command successfully clones missing repositories
- [ ] Sync command successfully pulls updates for existing repositories
- [ ] Sync command respects --force flag and requires confirmation  
- [ ] Sync command searches all providers when no --provider specified
- [ ] Sync command limits search to specific provider when --provider used
- [ ] Sync command validates patterns and shows helpful error messages
- [ ] Dry run mode accurately shows what actions would be taken
- [ ] Sync command performance is equivalent to or better than clone-all/pull-all
- [ ] Unit tests cover all sync command scenarios with >90% coverage
- [ ] Integration tests validate sync behavior end-to-end
- [ ] Manual verification confirms sync works as intended
- [ ] Command help text is clear and provides useful examples

## Rollback Plan
If the sync command has issues:
1. Remove sync command registration from `mgit/__main__.py`
2. Remove `mgit/commands/sync.py` file
3. Keep existing clone-all and pull-all commands working
4. Git repository returns to working state
5. Users can continue using clone-all and pull-all as before

## Notes
- Sync command provides the user experience improvement identified in the original analysis
- Command uses the same battle-tested bulk operation processor as clone-all and pull-all
- Multi-provider logic is identical to the fixed clone-all and pull-all commands
- Force mode safety is maintained with confirmation prompt
- Dry run capability helps users preview actions before execution
- The command is designed to be the primary interface users will prefer going forward
- Clear, actionable help text guides users on proper usage
- Performance should be equivalent to existing commands since it uses same underlying infrastructure
- Error handling and validation are comprehensive and user-friendly
# Phase 6: Enhance Sync Features and Deprecation

## Summary
Enhance the sync command with advanced features like progress reporting, better error handling, and repository status awareness. Add deprecation warnings to clone-all and pull-all commands to guide users toward the new sync command, preparing for eventual removal.

## Effort Estimate
1.5 hours

## Dependencies
- Phase 1: Pattern matching logic extracted
- Phase 2: Multi-provider resolution logic extracted  
- Phase 3: Multi-provider support in clone-all working
- Phase 4: Multi-provider support in pull-all working
- Phase 5: Basic sync command implemented

## Implementation Details

### Files to Create
None (enhancing existing files)

### Files to Modify
- `mgit/commands/sync.py` - Add enhanced features (progress bars, better error handling)
- `mgit/__main__.py` - Add deprecation warnings to clone-all and pull-all
- Documentation updates for the sync command

### Key Changes

#### 1. Enhance Sync Command with Progress Reporting (`mgit/commands/sync.py`)

Add rich progress reporting and better status awareness:

```python
# Add imports for enhanced features
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

# Enhance the sync command with progress tracking
def sync_command(
    pattern: str = typer.Argument(..., help="Repository pattern (org/project/repo)"),
    path: str = typer.Argument(".", help="Local path to synchronize repositories into"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Specific provider (otherwise search all)"),
    force: bool = typer.Option(False, "--force", "-f", help="Delete and re-clone all repositories"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c", help="Number of concurrent operations"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    progress: bool = typer.Option(True, "--progress/--no-progress", help="Show progress bar"),
    summary: bool = typer.Option(True, "--summary/--no-summary", help="Show detailed summary"),
) -> None:
    """
    Synchronize repositories with remote providers.
    
    🚀 UNIFIED REPOSITORY SYNC - replaces clone-all and pull-all
    
    Intelligently handles your repository synchronization:
    - Clones repositories that don't exist locally  
    - Pulls updates for repositories that already exist and are clean
    - Skips repositories with uncommitted changes (unless --force)
    - Handles conflicts and errors gracefully
    - Provides detailed progress and summary reporting
    
    PATTERN can be:
    - Exact: myorg/myproject/myrepo
    - Wildcards: myorg/*/myrepo, */myproject/*, myorg/*/*  
    - Cross-provider: */*/* (searches ALL providers)

    When no --provider specified, patterns search ALL configured providers.
    
    Examples:
        # Daily workspace sync
        mgit sync "myorg/*/*" ./workspace
        
        # Preview changes first
        mgit sync "myorg/*/*" ./workspace --dry-run
        
        # Nuclear option - fresh everything
        mgit sync "myorg/*/*" ./workspace --force
        
        # Quiet sync for scripts
        mgit sync "myorg/*/*" ./workspace --no-progress --no-summary
    """
    # ... existing parameter setup ...

    # Analyze repositories before operation
    if not dry_run:
        repo_analysis = await analyze_repository_states(repositories, target_path)
        
        if repo_analysis.dirty_repos and not force:
            console.print("\n[yellow]⚠️  Repositories with uncommitted changes:[/yellow]")
            for repo_name in repo_analysis.dirty_repos:
                console.print(f"  • {repo_name}")
            console.print("\n[blue]These will be skipped. Use --force to override (will lose changes)[/blue]")

    # Enhanced dry run with repository analysis
    if dry_run:
        await show_sync_preview(repositories, target_path, force, summary)
        return

    # Run sync with progress tracking
    if progress:
        await run_sync_with_progress(
            repositories, target_path, processor, concurrency, update_mode,
            confirmed_force_remove, dirs_to_remove
        )
    else:
        await run_sync_quiet(
            repositories, target_path, processor, concurrency, update_mode,
            confirmed_force_remove, dirs_to_remove
        )

async def analyze_repository_states(repositories: List[Repository], target_path: Path):
    """Analyze current state of repositories in target path."""
    from dataclasses import dataclass
    
    @dataclass
    class RepoAnalysis:
        clean_repos: List[str]
        dirty_repos: List[str]
        missing_repos: List[str]
        non_git_dirs: List[str]
    
    clean_repos = []
    dirty_repos = []
    missing_repos = []
    non_git_dirs = []
    
    for repo in repositories:
        local_path = target_path / repo.organization / (repo.project or "") / repo.name
        local_path = Path(str(local_path).replace("//", "/"))
        
        if not local_path.exists():
            missing_repos.append(repo.name)
        elif not (local_path / ".git").exists():
            non_git_dirs.append(repo.name)
        else:
            # Check if repo has uncommitted changes
            try:
                result = await asyncio.subprocess.run(
                    ["git", "status", "--porcelain"], 
                    cwd=local_path,
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    dirty_repos.append(repo.name)
                else:
                    clean_repos.append(repo.name)
            except Exception:
                # If git status fails, consider it dirty for safety
                dirty_repos.append(repo.name)
    
    return RepoAnalysis(clean_repos, dirty_repos, missing_repos, non_git_dirs)

async def show_sync_preview(repositories: List[Repository], target_path: Path, force: bool, detailed: bool):
    """Show detailed preview of sync operations."""
    repo_analysis = await analyze_repository_states(repositories, target_path)
    
    # Create summary table
    table = Table(title="Sync Preview")
    table.add_column("Repository", style="cyan", no_wrap=True)
    table.add_column("Current State", style="yellow")
    table.add_column("Planned Action", style="green")
    table.add_column("Notes", style="dim")
    
    for repo in repositories:
        local_path = target_path / repo.organization / (repo.project or "") / repo.name
        repo_name = f"{repo.organization}/{repo.name}"
        
        if repo.name in repo_analysis.missing_repos:
            table.add_row(repo_name, "Missing", "🔄 Clone", "New repository")
        elif repo.name in repo_analysis.non_git_dirs:
            table.add_row(repo_name, "Non-Git", "⚠️ Skip", "Directory exists but not git repo")
        elif repo.name in repo_analysis.dirty_repos:
            if force:
                table.add_row(repo_name, "Dirty", "🗑️ Force Clone", "Will delete local changes")
            else:
                table.add_row(repo_name, "Dirty", "⏭️ Skip", "Has uncommitted changes")
        else:  # clean repo
            if force:
                table.add_row(repo_name, "Clean", "🗑️ Force Clone", "Will re-clone fresh")
            else:
                table.add_row(repo_name, "Clean", "⬇️ Pull", "Update to latest")
    
    console.print(table)
    
    # Summary counts
    if detailed:
        summary_table = Table(title="Operation Summary")
        summary_table.add_column("Action", style="bold")
        summary_table.add_column("Count", justify="right", style="green")
        
        clone_count = len(repo_analysis.missing_repos) + (len(repositories) if force else 0)
        pull_count = len(repo_analysis.clean_repos) if not force else 0
        skip_count = len(repo_analysis.dirty_repos) + len(repo_analysis.non_git_dirs)
        if force:
            skip_count = len(repo_analysis.non_git_dirs)  # Only non-git dirs skipped in force mode
        
        summary_table.add_row("Clone", str(clone_count))
        summary_table.add_row("Pull", str(pull_count))
        summary_table.add_row("Skip", str(skip_count))
        
        console.print(summary_table)

async def run_sync_with_progress(repositories, target_path, processor, concurrency, update_mode, confirmed_force_remove, dirs_to_remove):
    """Run sync operation with rich progress reporting."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        # Add main progress task
        sync_task = progress.add_task("Synchronizing repositories...", total=len(repositories))
        
        # Custom callback to update progress
        async def progress_callback(completed: int, total: int, current_repo: str):
            progress.update(
                sync_task, 
                completed=completed, 
                description=f"Syncing: {current_repo}"
            )
        
        # Run sync with progress callback
        failures = await processor.process_bulk_operation_with_progress(
            repositories=repositories,
            target_path=target_path,
            concurrency=concurrency,
            update_mode=update_mode,
            confirmed_force_remove=confirmed_force_remove,
            dirs_to_remove=dirs_to_remove,
            progress_callback=progress_callback
        )
    
    # Show final results
    success_count = len(repositories) - len(failures)
    
    if failures:
        console.print(f"\n[yellow]Sync completed with issues:[/yellow]")
        console.print(f"  [green]✅ Successful:[/green] {success_count}")
        console.print(f"  [red]❌ Failed:[/red] {len(failures)}")
        
        # Group failures by type for better reporting
        failure_table = Table(title="Failed Operations")
        failure_table.add_column("Repository", style="red")
        failure_table.add_column("Error", style="yellow")
        
        for failure in failures:
            # Parse failure string to extract repo name and error
            parts = str(failure).split(":", 1)
            repo_name = parts[0] if len(parts) > 0 else "Unknown"
            error_msg = parts[1].strip() if len(parts) > 1 else str(failure)
            failure_table.add_row(repo_name, error_msg)
            
        console.print(failure_table)
        raise typer.Exit(code=1)
    else:
        console.print(f"\n[green]✅ Successfully synchronized {success_count} repositories![/green]")

async def run_sync_quiet(repositories, target_path, processor, concurrency, update_mode, confirmed_force_remove, dirs_to_remove):
    """Run sync operation without progress reporting."""
    failures = await processor.process_bulk_operation(
        repositories=repositories,
        target_path=target_path,
        concurrency=concurrency,
        update_mode=update_mode,
        confirmed_force_remove=confirmed_force_remove,
        dirs_to_remove=dirs_to_remove,
    )
    
    success_count = len(repositories) - len(failures)
    
    if failures:
        logger.error(f"Sync completed with {len(failures)} failures out of {len(repositories)} repositories")
        for failure in failures:
            logger.error(f"Failed: {failure}")
        raise typer.Exit(code=1)
    else:
        logger.info(f"Successfully synchronized {success_count} repositories")
```

#### 2. Add Deprecation Warnings (`mgit/__main__.py`)

Add deprecation warnings to guide users toward sync:

```python
def clone_all(
    # ... existing parameters ...
):
    """
    Clone all repositories in a project or matching a pattern.
    
    ⚠️  DEPRECATED: Use 'mgit sync' instead for better experience.
    
    The 'sync' command provides the same functionality with:
    - Simpler usage (no confusing update modes)  
    - Better progress reporting
    - Intelligent clone + pull behavior
    - Enhanced error handling
    
    Migration: Replace 'mgit clone-all' with 'mgit sync'
    """
    # Show deprecation warning
    console.print(
        "[yellow]⚠️  Deprecation Warning:[/yellow] "
        "'clone-all' command will be removed in a future version.\n"
        "[blue]Use 'mgit sync' instead for better experience and identical functionality.[/blue]\n"
        "Run with --no-warnings to suppress this message."
    )
    
    # ... rest of existing function ...

def pull_all(
    # ... existing parameters ...
):
    """
    Pull updates for all repositories matching a pattern or in a project.
    
    ⚠️  DEPRECATED: Use 'mgit sync' instead for better experience.
    
    The 'sync' command provides the same functionality with:
    - Automatic handling of missing repositories  
    - Better progress reporting
    - Intelligent clone + pull behavior
    - Enhanced error handling
    
    Migration: Replace 'mgit pull-all' with 'mgit sync'
    """
    # Show deprecation warning
    console.print(
        "[yellow]⚠️  Deprecation Warning:[/yellow] "
        "'pull-all' command will be removed in a future version.\n"
        "[blue]Use 'mgit sync' instead for better experience and identical functionality.[/blue]\n"
        "Run with --no-warnings to suppress this message."
    )
    
    # ... rest of existing function ...

# Add global --no-warnings flag
def add_global_options(func):
    """Add global options to commands."""
    func = typer.Option(False, "--no-warnings", help="Suppress deprecation warnings")(func)
    return func

# Apply to deprecated commands
@add_global_options
def clone_all(..., no_warnings: bool = False):
    if not no_warnings:
        # Show warning
        pass
    # ... rest of function

@add_global_options  
def pull_all(..., no_warnings: bool = False):
    if not no_warnings:
        # Show warning
        pass
    # ... rest of function
```

#### 3. Add Migration Helper Command

Add a helper command to assist with migration:

```python
@app.command()
def migrate_help():
    """
    Show how to migrate from old commands to new sync command.
    """
    migration_table = Table(title="Command Migration Guide")
    migration_table.add_column("Old Command", style="red")
    migration_table.add_column("New Command", style="green")  
    migration_table.add_column("Notes", style="blue")
    
    migration_table.add_row(
        "mgit clone-all 'pattern' ./path",
        "mgit sync 'pattern' ./path", 
        "Identical behavior"
    )
    migration_table.add_row(
        "mgit clone-all 'pattern' ./path --update-mode pull",
        "mgit sync 'pattern' ./path",
        "Default sync behavior"  
    )
    migration_table.add_row(
        "mgit pull-all 'pattern' ./path",
        "mgit sync 'pattern' ./path",
        "Handles missing repos automatically"
    )
    migration_table.add_row(
        "mgit clone-all 'pattern' ./path --force",
        "mgit sync 'pattern' ./path --force",
        "Identical force behavior"
    )
    migration_table.add_row(
        "mgit pull-all 'pattern' ./path --update-mode force", 
        "mgit sync 'pattern' ./path --force",
        "Cleaner force syntax"
    )
    
    console.print(migration_table)
    
    console.print("\n[blue]Benefits of migrating to 'sync':[/blue]")
    console.print("• Single command handles both clone and pull intelligently")
    console.print("• Better progress reporting and error handling") 
    console.print("• Cleaner syntax without confusing update modes")
    console.print("• Enhanced dry-run preview capabilities")
    console.print("• Future-proof - clone-all and pull-all will be removed")
```

## Testing Strategy

### Unit Tests
Add to `tests/unit/test_sync_command.py`:

```python
class TestEnhancedSyncCommand:
    def test_sync_progress_reporting(self):
        """Test that progress reporting works correctly."""
        pass
    
    def test_sync_repository_analysis(self):
        """Test repository state analysis (clean, dirty, missing)."""
        pass
    
    def test_sync_preview_output(self):
        """Test that dry-run preview shows correct information."""
        pass
    
    def test_sync_summary_reporting(self):
        """Test detailed summary after operations."""
        pass

class TestDeprecationWarnings:
    def test_clone_all_shows_deprecation_warning(self):
        """Test that clone-all shows deprecation warning by default."""
        pass
    
    def test_pull_all_shows_deprecation_warning(self):
        """Test that pull-all shows deprecation warning by default."""
        pass
    
    def test_no_warnings_flag_suppresses_warnings(self):
        """Test that --no-warnings flag works."""
        pass
```

### Integration Tests  
Add to `tests/integration/test_enhanced_sync.py`:

```python
class TestEnhancedSyncIntegration:
    @pytest.mark.integration
    def test_sync_handles_mixed_repository_states(self):
        """Test sync with mix of missing, clean, and dirty repositories."""
        pass
    
    @pytest.mark.integration  
    def test_sync_progress_with_real_repositories(self):
        """Test progress reporting with real repository operations."""
        pass
    
    @pytest.mark.integration
    def test_migration_parity(self):
        """Test that sync produces same results as clone-all/pull-all.""" 
        pass
```

### Manual Verification Commands

Test enhanced features thoroughly:

```bash
# Test enhanced dry run preview
poetry run mgit sync "myorg/*/*" /tmp/sync-test --dry-run --summary

# Test progress reporting
poetry run mgit sync "myorg/*/*" /tmp/sync-test --progress

# Test quiet mode for scripting
poetry run mgit sync "myorg/*/*" /tmp/sync-test --no-progress --no-summary

# Test deprecation warnings
poetry run mgit clone-all "myorg/*/*" /tmp/test
poetry run mgit pull-all "myorg/*/*" /tmp/test

# Test warning suppression
poetry run mgit clone-all "myorg/*/*" /tmp/test --no-warnings

# Test migration helper
poetry run mgit migrate-help

# Test repository state handling
cd /tmp/sync-test/myorg/somerepo
echo "test" > uncommitted-file.txt  # Create dirty repo
cd -
poetry run mgit sync "myorg/*/*" /tmp/sync-test --dry-run  # Should show dirty repo handling
```

### Performance and UX Testing

```bash
#!/bin/bash
# Test enhanced sync UX improvements

PATTERN="myorg/*/*"
TESTDIR="/tmp/ux-test"

echo "Testing sync command UX enhancements..."

# Test dry run preview
echo "1. Testing dry-run preview..."
poetry run mgit sync "$PATTERN" "$TESTDIR" --dry-run

# Test progress reporting
echo "2. Testing progress reporting..."
poetry run mgit sync "$PATTERN" "$TESTDIR" --progress

# Test quiet mode
echo "3. Testing quiet mode..."  
poetry run mgit sync "$PATTERN" "$TESTDIR-quiet" --no-progress --no-summary

echo "UX testing complete"
```

## Success Criteria
- [ ] Sync command provides rich progress reporting during operations
- [ ] Sync command analyzes repository states and shows intelligent preview
- [ ] Sync command handles dirty repositories appropriately (skip unless --force)
- [ ] Sync command provides detailed success/failure summaries
- [ ] Clone-all command shows deprecation warning by default
- [ ] Pull-all command shows deprecation warning by default  
- [ ] --no-warnings flag suppresses deprecation warnings
- [ ] Migration helper command provides clear guidance
- [ ] Enhanced sync features work correctly with all pattern types
- [ ] Progress reporting performance doesn't significantly impact operation speed
- [ ] Unit tests cover all enhanced features with >90% coverage
- [ ] Integration tests validate enhanced behavior end-to-end
- [ ] Manual verification confirms all enhancements work as expected

## Rollback Plan
If enhanced features cause issues:
1. Revert enhancements to `mgit/commands/sync.py` (keep basic version from Phase 5)
2. Remove deprecation warnings from `mgit/__main__.py`
3. Remove migration helper command
4. Test that basic sync command still works correctly
5. Keep all other Phase 1-4 improvements (they're working)
6. Git repository returns to working state

## Notes
- This phase completes the user experience transformation
- Enhanced features make sync command significantly better than clone-all/pull-all
- Deprecation warnings help users discover the better sync command
- Migration helper reduces friction for users adopting the new command  
- Progress reporting provides much-needed feedback for long-running operations
- Repository state analysis prevents common issues (like overwriting uncommitted changes)
- The enhancements maintain backward compatibility - all existing functionality works
- Performance impact of enhancements should be minimal due to async implementation
- Clear migration path helps users transition away from deprecated commands
- Enhanced error reporting makes troubleshooting much easier
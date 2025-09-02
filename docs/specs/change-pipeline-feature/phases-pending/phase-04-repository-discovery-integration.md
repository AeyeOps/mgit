# Phase 4: Repository Discovery Integration

## Summary
Integrate change detection with the existing provider system to enable change tracking across multiple Git providers using query patterns, with concurrent multi-provider support and proper error isolation.

## Effort Estimate
4-5 hours

## Dependencies
- Phase 1: Basic change detection must be implemented
- Phase 2: Changeset persistence must be implemented
- Phase 3: Smart content embedding must be implemented

## Implementation Details

### Files to Create
- `mgit/commands/diff_remote.py` - Remote repository change detection
- `mgit/discovery/change_discovery.py` - Repository discovery integration for changes

### Files to Modify
- `mgit/__main__.py` - Add remote diff command and extend existing diff with provider options
- `mgit/commands/diff.py` - Add provider integration support
- `mgit/utils/multi_provider_resolver.py` - Extend for change detection use cases

### Key Changes

#### 1. Create Discovery Integration Module (`mgit/discovery/change_discovery.py`)

```python
"""
Repository discovery integration for change detection.

Combines the provider system with change detection to enable tracking
changes across multiple repositories discovered through query patterns.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set, Any, Tuple
from dataclasses import dataclass

from mgit.providers.base import Repository
from mgit.providers.manager_v2 import ProviderManager
from mgit.commands.listing import list_repositories
from mgit.commands.diff import DiffProcessor
from mgit.changesets.models import RepositoryChangeset
from mgit.utils.pattern_matching import analyze_pattern
from mgit.config.yaml_manager import list_provider_names

logger = logging.getLogger(__name__)

@dataclass
class DiscoveredRepositoryChange:
    """Represents changes in a repository discovered through provider queries."""
    repository: Repository
    local_path: Optional[Path]  # Local clone path if exists
    changeset: Optional[RepositoryChangeset]  # Change information if locally available
    provider_name: str
    discovery_query: str
    error: Optional[str] = None

@dataclass
class ChangeDiscoveryResult:
    """Result of change discovery across providers and repositories."""
    discovered_repositories: List[DiscoveredRepositoryChange]
    successful_providers: List[str]
    failed_providers: List[str]
    local_repositories_found: int
    remote_only_repositories: int
    total_repositories_with_changes: int
    query_pattern: str
    
    @property
    def success_rate(self) -> float:
        """Calculate provider success rate."""
        total_providers = len(self.successful_providers) + len(self.failed_providers)
        return len(self.successful_providers) / total_providers if total_providers > 0 else 0.0

class ChangeDiscoveryEngine:
    """
    Engine for discovering repositories and their changes across providers.
    
    Combines repository discovery through provider APIs with local change detection
    to provide comprehensive view of repository states across multiple providers.
    """
    
    def __init__(self, local_scan_root: Optional[Path] = None, concurrency: int = 10):
        """
        Initialize change discovery engine.
        
        Args:
            local_scan_root: Root directory to scan for local repository clones
            concurrency: Number of concurrent operations for change detection
        """
        self.local_scan_root = local_scan_root
        self.concurrency = concurrency
        self.diff_processor = DiffProcessor(concurrency=concurrency)
    
    async def discover_repository_changes(
        self,
        query_pattern: str,
        provider_name: Optional[str] = None,
        provider_url: Optional[str] = None,
        local_scan_only: bool = False,
        include_remote_only: bool = True,
        limit: Optional[int] = None
    ) -> ChangeDiscoveryResult:
        """
        Discover repositories matching pattern and detect their changes.
        
        Args:
            query_pattern: Repository pattern to search for (e.g., "org/*/*")
            provider_name: Specific provider to query (None for all)
            provider_url: Provider URL for single provider discovery
            local_scan_only: Only check locally cloned repositories
            include_remote_only: Include repositories found remotely but not locally
            limit: Maximum number of repositories to process
            
        Returns:
            ChangeDiscoveryResult with discovered repositories and change information
        """
        try:
            logger.info(f"Starting change discovery for pattern: {query_pattern}")
            
            if local_scan_only:
                return await self._discover_local_only(query_pattern, limit)
            
            # Discover repositories through provider system
            discovered_repos = await self._discover_repositories_via_providers(
                query_pattern, provider_name, provider_url, limit
            )
            
            if not discovered_repos:
                logger.warning(f"No repositories discovered for pattern: {query_pattern}")
                return ChangeDiscoveryResult(
                    discovered_repositories=[],
                    successful_providers=[],
                    failed_providers=[],
                    local_repositories_found=0,
                    remote_only_repositories=0,
                    total_repositories_with_changes=0,
                    query_pattern=query_pattern
                )
            
            # Map repositories to local paths and detect changes
            result_repos = await self._process_discovered_repositories(
                discovered_repos, include_remote_only, query_pattern
            )
            
            # Aggregate results
            successful_providers = list(set(r.provider_name for r in result_repos if r.error is None))
            failed_providers = list(set(r.provider_name for r in result_repos if r.error is not None))
            
            local_count = sum(1 for r in result_repos if r.local_path is not None)
            remote_only_count = sum(1 for r in result_repos if r.local_path is None)
            changes_count = sum(1 for r in result_repos if r.changeset and r.changeset.has_uncommitted_changes)
            
            logger.info(
                f"Change discovery completed: {len(result_repos)} repositories, "
                f"{local_count} local, {remote_only_count} remote-only, "
                f"{changes_count} with changes"
            )
            
            return ChangeDiscoveryResult(
                discovered_repositories=result_repos,
                successful_providers=successful_providers,
                failed_providers=failed_providers,
                local_repositories_found=local_count,
                remote_only_repositories=remote_only_count,
                total_repositories_with_changes=changes_count,
                query_pattern=query_pattern
            )
            
        except Exception as e:
            logger.error(f"Change discovery failed: {e}")
            return ChangeDiscoveryResult(
                discovered_repositories=[],
                successful_providers=[],
                failed_providers=[],
                local_repositories_found=0,
                remote_only_repositories=0,
                total_repositories_with_changes=0,
                query_pattern=query_pattern
            )
    
    async def _discover_repositories_via_providers(
        self,
        query_pattern: str,
        provider_name: Optional[str],
        provider_url: Optional[str],
        limit: Optional[int]
    ) -> List[Tuple[Repository, str]]:
        """
        Discover repositories through provider system.
        
        Returns:
            List of (Repository, provider_name) tuples
        """
        discovered_repos = []
        
        if provider_name:
            # Single provider discovery
            try:
                logger.debug(f"Querying provider '{provider_name}' for pattern: {query_pattern}")
                
                repository_results = await list_repositories(
                    query=query_pattern,
                    provider_name=provider_name,
                    format_type="json",
                    limit=limit
                )
                
                if repository_results:
                    for result in repository_results:
                        discovered_repos.append((result.repo, provider_name))
                    
                    logger.debug(f"Provider '{provider_name}' returned {len(repository_results)} repositories")
                
            except Exception as e:
                logger.error(f"Provider '{provider_name}' query failed: {e}")
        
        else:
            # Multi-provider discovery
            pattern_analysis = analyze_pattern(query_pattern, provider_name, provider_url)
            
            if pattern_analysis.is_multi_provider:
                providers = list_provider_names()
                logger.debug(f"Querying {len(providers)} providers for pattern: {query_pattern}")
                
                # Query providers concurrently
                tasks = []
                for prov_name in providers:
                    task = self._query_single_provider(query_pattern, prov_name, limit)
                    tasks.append(task)
                
                provider_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Aggregate results
                for i, result in enumerate(provider_results):
                    prov_name = providers[i]
                    
                    if isinstance(result, Exception):
                        logger.debug(f"Provider '{prov_name}' failed: {result}")
                    elif isinstance(result, list):
                        for repo in result:
                            discovered_repos.append((repo, prov_name))
                        logger.debug(f"Provider '{prov_name}' returned {len(result)} repositories")
        
        logger.info(f"Discovered {len(discovered_repos)} repositories across all providers")
        return discovered_repos
    
    async def _query_single_provider(self, query_pattern: str, provider_name: str, limit: Optional[int]) -> List[Repository]:
        """Query a single provider for repositories."""
        try:
            repository_results = await list_repositories(
                query=query_pattern,
                provider_name=provider_name,
                format_type="json",
                limit=limit
            )
            
            return [result.repo for result in (repository_results or [])]
            
        except Exception as e:
            logger.debug(f"Provider '{provider_name}' query failed: {e}")
            raise
    
    async def _process_discovered_repositories(
        self,
        discovered_repos: List[Tuple[Repository, str]],
        include_remote_only: bool,
        query_pattern: str
    ) -> List[DiscoveredRepositoryChange]:
        """Process discovered repositories to detect local changes."""
        result_repos = []
        
        # Create tasks for concurrent processing
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async def process_single_repo(repo_info: Tuple[Repository, str]) -> DiscoveredRepositoryChange:
            async with semaphore:
                repository, provider_name = repo_info
                
                try:
                    # Check if repository exists locally
                    local_path = self._find_local_repository_path(repository)
                    
                    changeset = None
                    if local_path and local_path.exists():
                        # Repository exists locally - detect changes
                        logger.debug(f"Detecting changes in local repository: {local_path}")
                        changeset = await self.diff_processor._detect_repository_changes(local_path)
                    elif not include_remote_only:
                        # Skip remote-only repositories if not requested
                        return None
                    
                    return DiscoveredRepositoryChange(
                        repository=repository,
                        local_path=local_path,
                        changeset=changeset,
                        provider_name=provider_name,
                        discovery_query=query_pattern,
                        error=None
                    )
                    
                except Exception as e:
                    logger.debug(f"Failed to process repository {repository.name}: {e}")
                    return DiscoveredRepositoryChange(
                        repository=repository,
                        local_path=None,
                        changeset=None,
                        provider_name=provider_name,
                        discovery_query=query_pattern,
                        error=str(e)
                    )
        
        # Process repositories concurrently
        tasks = [process_single_repo(repo_info) for repo_info in discovered_repos]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        for result in results:
            if isinstance(result, Exception):
                logger.debug(f"Repository processing failed: {result}")
            elif result is not None:
                result_repos.append(result)
        
        return result_repos
    
    async def _discover_local_only(self, query_pattern: str, limit: Optional[int]) -> ChangeDiscoveryResult:
        """Discover repositories by scanning local filesystem only."""
        if not self.local_scan_root:
            logger.error("Local scan requested but no local_scan_root configured")
            return ChangeDiscoveryResult(
                discovered_repositories=[],
                successful_providers=[],
                failed_providers=[],
                local_repositories_found=0,
                remote_only_repositories=0,
                total_repositories_with_changes=0,
                query_pattern=query_pattern
            )
        
        try:
            from mgit.utils.directory_scanner import find_repositories_in_directory
            
            # Find local repositories
            local_repos = find_repositories_in_directory(self.local_scan_root, recursive=True)
            
            if limit and len(local_repos) > limit:
                local_repos = local_repos[:limit]
            
            # Process local repositories for changes
            changesets = await self.diff_processor.process_repositories(local_repos)
            
            # Convert to DiscoveredRepositoryChange format
            result_repos = []
            for i, local_path in enumerate(local_repos):
                changeset = changesets[i] if i < len(changesets) else None
                
                # Create minimal repository info for local-only mode
                dummy_repo = Repository(
                    name=local_path.name,
                    clone_url=f"file://{local_path}",
                    organization="local",
                    project=""
                )
                
                result_repos.append(DiscoveredRepositoryChange(
                    repository=dummy_repo,
                    local_path=local_path,
                    changeset=changeset,
                    provider_name="local",
                    discovery_query=query_pattern,
                    error=None
                ))
            
            changes_count = sum(1 for r in result_repos if r.changeset and r.changeset.has_uncommitted_changes)
            
            return ChangeDiscoveryResult(
                discovered_repositories=result_repos,
                successful_providers=["local"],
                failed_providers=[],
                local_repositories_found=len(result_repos),
                remote_only_repositories=0,
                total_repositories_with_changes=changes_count,
                query_pattern=query_pattern
            )
            
        except Exception as e:
            logger.error(f"Local discovery failed: {e}")
            return ChangeDiscoveryResult(
                discovered_repositories=[],
                successful_providers=[],
                failed_providers=["local"],
                local_repositories_found=0,
                remote_only_repositories=0,
                total_repositories_with_changes=0,
                query_pattern=query_pattern
            )
    
    def _find_local_repository_path(self, repository: Repository) -> Optional[Path]:
        """
        Find local path for a remote repository.
        
        Uses heuristics to find likely local clone locations based on
        repository organization, name, and common clone patterns.
        """
        if not self.local_scan_root:
            return None
        
        # Common clone path patterns to check
        potential_paths = [
            # Direct organization/repository structure
            self.local_scan_root / repository.organization / repository.name,
            
            # Flat repository name structure
            self.local_scan_root / repository.name,
            
            # Project-based structure (for Azure DevOps)
            self.local_scan_root / repository.organization / (repository.project or "default") / repository.name,
            
            # Provider-specific structures
            self.local_scan_root / "github" / repository.organization / repository.name,
            self.local_scan_root / "azure" / repository.organization / repository.name,
            self.local_scan_root / "bitbucket" / repository.organization / repository.name,
        ]
        
        # Check each potential path
        for path in potential_paths:
            if path.exists() and (path / '.git').exists():
                logger.debug(f"Found local repository at: {path}")
                return path
        
        return None

# Convenience functions for common use cases
async def discover_changes_by_pattern(
    pattern: str,
    local_root: Optional[Path] = None,
    provider: Optional[str] = None,
    limit: Optional[int] = None
) -> ChangeDiscoveryResult:
    """
    Convenience function for discovering repository changes by pattern.
    
    Args:
        pattern: Repository search pattern (e.g., "myorg/*/*")
        local_root: Root directory to scan for local clones
        provider: Specific provider to query (None for all providers)
        limit: Maximum repositories to process
        
    Returns:
        ChangeDiscoveryResult with discovered changes
    """
    engine = ChangeDiscoveryEngine(local_scan_root=local_root)
    return await engine.discover_repository_changes(
        query_pattern=pattern,
        provider_name=provider,
        limit=limit
    )

async def discover_local_changes_only(
    local_root: Path,
    pattern: str = "*/*/*",
    limit: Optional[int] = None
) -> ChangeDiscoveryResult:
    """
    Convenience function for local-only change discovery.
    
    Args:
        local_root: Root directory to scan for repositories
        pattern: Pattern for filtering repository names
        limit: Maximum repositories to process
        
    Returns:
        ChangeDiscoveryResult with local repository changes
    """
    engine = ChangeDiscoveryEngine(local_scan_root=local_root)
    return await engine.discover_repository_changes(
        query_pattern=pattern,
        local_scan_only=True,
        limit=limit
    )
```

#### 2. Create Remote Diff Command (`mgit/commands/diff_remote.py`)

```python
"""
Remote repository change detection command.

Provides functionality to discover and track changes across repositories
found through provider queries, combining remote discovery with local change detection.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import asdict

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from mgit.discovery.change_discovery import ChangeDiscoveryEngine, ChangeDiscoveryResult
from mgit.changesets.storage import ChangesetStorage
from mgit.commands.diff import _convert_to_repository_changeset

logger = logging.getLogger(__name__)
console = Console()

def execute_remote_diff_command(
    pattern: str,
    local_root: Optional[Path],
    provider: Optional[str],
    output: Optional[Path],
    save_changeset: bool,
    changeset_name: str,
    include_remote_only: bool,
    concurrency: int,
    limit: Optional[int],
    verbose: bool
) -> None:
    """
    Execute remote repository change detection.
    
    Args:
        pattern: Repository search pattern (e.g., "myorg/*/*")
        local_root: Root directory to scan for local repository clones
        provider: Specific provider to query (None for all)
        output: Optional output file path for results
        save_changeset: Whether to save results to changeset storage
        changeset_name: Name of changeset collection for storage
        include_remote_only: Include repositories found remotely but not locally
        concurrency: Number of concurrent operations
        limit: Maximum repositories to process
        verbose: Enable verbose output
    """
    if verbose:
        logging.getLogger("mgit").setLevel(logging.DEBUG)
        console.print(f"[blue]Starting remote change discovery for pattern: {pattern}[/blue]")
    
    try:
        # Initialize discovery engine
        engine = ChangeDiscoveryEngine(
            local_scan_root=local_root,
            concurrency=concurrency
        )
        
        # Perform discovery
        with Progress() as progress:
            task = progress.add_task("[green]Discovering repositories...", total=None)
            
            result = asyncio.run(
                engine.discover_repository_changes(
                    query_pattern=pattern,
                    provider_name=provider,
                    include_remote_only=include_remote_only,
                    limit=limit
                )
            )
            
            progress.update(task, completed=100, total=100)
        
        # Display results summary
        _display_discovery_summary(result, verbose)
        
        # Save to changeset storage if requested
        if save_changeset:
            _save_discovery_to_changesets(result, changeset_name, verbose)
        
        # Output detailed results
        if output or not save_changeset:
            _output_discovery_results(result, output, verbose)
        
        if verbose:
            console.print(f"[green]Remote change discovery completed successfully[/green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error during remote change discovery: {e}[/red]")
        logger.error(f"Remote change discovery failed: {e}")
        raise typer.Exit(1)

def _display_discovery_summary(result: ChangeDiscoveryResult, verbose: bool) -> None:
    """Display summary of discovery results."""
    
    # Create summary table
    table = Table(title="Repository Discovery Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Details", style="dim")
    
    table.add_row("Total Repositories", str(len(result.discovered_repositories)), "Found across all providers")
    table.add_row("Local Repositories", str(result.local_repositories_found), "With local clones available")
    table.add_row("Remote Only", str(result.remote_only_repositories), "Found remotely but not locally")
    table.add_row("With Changes", str(result.total_repositories_with_changes), "Have uncommitted changes")
    
    if result.successful_providers:
        table.add_row("Successful Providers", str(len(result.successful_providers)), ", ".join(result.successful_providers))
    
    if result.failed_providers:
        table.add_row("Failed Providers", str(len(result.failed_providers)), ", ".join(result.failed_providers))
    
    table.add_row("Success Rate", f"{result.success_rate:.1%}", "Provider query success rate")
    
    console.print(table)
    
    if verbose and result.discovered_repositories:
        # Show detailed repository information
        console.print("\n[bold]Repository Details:[/bold]")
        
        for repo_change in result.discovered_repositories:
            status_emoji = "✅" if repo_change.local_path else "🌐"
            changes_info = ""
            
            if repo_change.changeset:
                if repo_change.changeset.has_uncommitted_changes:
                    changes_info = f" ([yellow]{len(repo_change.changeset.uncommitted_files)} changes[/yellow])"
                else:
                    changes_info = " ([green]clean[/green])"
            elif repo_change.local_path:
                changes_info = " ([red]error[/red])"
            
            console.print(f"  {status_emoji} {repo_change.repository.organization}/{repo_change.repository.name}{changes_info}")
            
            if verbose and repo_change.error:
                console.print(f"    [red]Error: {repo_change.error}[/red]")

def _save_discovery_to_changesets(result: ChangeDiscoveryResult, changeset_name: str, verbose: bool) -> None:
    """Save discovery results to changeset storage."""
    try:
        storage = ChangesetStorage()
        changesets_saved = 0
        
        with storage.atomic_update(changeset_name) as collection:
            # Add metadata about the discovery operation
            collection.metadata.update({
                'discovery_query': result.query_pattern,
                'discovery_timestamp': collection.updated_at,
                'total_discovered': len(result.discovered_repositories),
                'local_repositories': result.local_repositories_found,
                'remote_only_repositories': result.remote_only_repositories,
                'successful_providers': result.successful_providers,
                'failed_providers': result.failed_providers
            })
            
            # Save changesets for repositories with local changes
            for repo_change in result.discovered_repositories:
                if repo_change.changeset and not repo_change.error:
                    collection.add_repository(repo_change.changeset)
                    changesets_saved += 1
        
        if verbose:
            console.print(f"[green]Saved {changesets_saved} changesets to collection: {changeset_name}[/green]")
        
    except Exception as e:
        logger.error(f"Failed to save discovery to changesets: {e}")
        if verbose:
            console.print(f"[red]Failed to save changesets: {e}[/red]")

def _output_discovery_results(result: ChangeDiscoveryResult, output: Optional[Path], verbose: bool) -> None:
    """Output detailed discovery results in JSONL format."""
    import json
    
    output_stream = sys.stdout
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output_stream = output.open('w', encoding='utf-8')
    
    try:
        written_count = 0
        
        for repo_change in result.discovered_repositories:
            try:
                # Convert to serializable format
                result_data = {
                    'repository': {
                        'name': repo_change.repository.name,
                        'organization': repo_change.repository.organization,
                        'project': repo_change.repository.project,
                        'clone_url': repo_change.repository.clone_url,
                        'description': repo_change.repository.description,
                        'default_branch': repo_change.repository.default_branch
                    },
                    'local_path': str(repo_change.local_path) if repo_change.local_path else None,
                    'provider_name': repo_change.provider_name,
                    'discovery_query': repo_change.discovery_query,
                    'has_local_clone': repo_change.local_path is not None,
                    'changeset': None,
                    'error': repo_change.error
                }
                
                # Include changeset data if available
                if repo_change.changeset:
                    result_data['changeset'] = asdict(repo_change.changeset)
                
                # Write as JSONL
                json_line = json.dumps(result_data, ensure_ascii=False, separators=(',', ':'))
                output_stream.write(json_line + '\n')
                output_stream.flush()
                
                written_count += 1
                
            except Exception as e:
                logger.error(f"Error writing result for {repo_change.repository.name}: {e}")
        
        if verbose:
            console.print(f"[blue]Wrote {written_count} discovery results[/blue]")
        
    finally:
        if output_stream != sys.stdout:
            output_stream.close()
```

#### 3. Update Main CLI with Provider Integration (`mgit/__main__.py`)

Add remote diff command and extend existing diff command:

```python
# Add remote diff command after the existing diff command (around line 1380)

# -----------------------------------------------------------------------------
# diff-remote Command
# -----------------------------------------------------------------------------
@app.command(name="diff-remote")
def diff_remote_command(
    pattern: str = typer.Argument(
        ...,
        help="Repository search pattern (e.g., 'myorg/*/*', 'github/*/*', '*pdi/*')."
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
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
) -> None:
    """
    Discover repositories through provider queries and detect their changes.
    
    This command combines repository discovery across Git providers with 
    change detection, allowing you to track changes in repositories matching
    specific patterns across multiple providers.
    
    Examples:
      mgit diff-remote "myorg/*/*" --local-root ./repos --save-changeset
      mgit diff-remote "github*/*/*" --provider github_work --verbose
      mgit diff-remote "*pdi/*" --include-remote-only --output discovery.jsonl
    """
    from mgit.commands.diff_remote import execute_remote_diff_command
    execute_remote_diff_command(
        pattern, local_root, provider, output, save_changeset, changeset_name,
        include_remote_only, concurrency, limit, verbose
    )

# Update existing diff command to include provider-related options
# Modify the existing diff_command function to add these parameters:

def diff_command(
    path: Path = typer.Argument(
        ".",
        help="Path to repository or directory containing repositories.",
        exists=True,
        resolve_path=True,
    ),
    # ... existing parameters ...
    
    # Add new provider integration parameters
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
    
    # ... rest of existing parameters ...
) -> None:
    """
    Detect changes in Git repositories with optional provider discovery.
    
    Enhanced with repository discovery capabilities to automatically find
    and include additional repositories matching patterns.
    """
    from mgit.commands.diff import execute_diff_command
    execute_diff_command(
        path, output, recursive, concurrency, verbose, save_changeset, 
        changeset_name, incremental, embed_content, content_strategy, 
        content_memory_mb, discover_pattern, discover_provider, merge_discovered
    )
```

#### 4. Update Existing Diff Command with Discovery (`mgit/commands/diff.py`)

Extend the existing diff command to support repository discovery:

```python
# Add imports at the top
from mgit.discovery.change_discovery import ChangeDiscoveryEngine

# Update execute_diff_command function signature and implementation
def execute_diff_command(
    path: Path,
    output: Optional[Path],
    recursive: bool,
    concurrency: int,
    verbose: bool,
    save_changeset: bool = False,
    changeset_name: str = "default",
    incremental: bool = False,
    embed_content: bool = False,
    content_strategy: str = "sample",
    content_memory_mb: int = 100,
    discover_pattern: Optional[str] = None,
    discover_provider: Optional[str] = None,
    merge_discovered: bool = False
) -> None:
    """
    Execute diff command with optional repository discovery integration.
    
    Args:
        path: Path to repository or directory to scan
        output: Optional output file path  
        recursive: Whether to scan recursively for repositories
        concurrency: Number of concurrent operations
        verbose: Whether to enable verbose output
        save_changeset: Whether to save changesets to persistent storage
        changeset_name: Name of changeset collection to use
        incremental: Whether to only report changes since last save
        embed_content: Whether to embed file content
        content_strategy: Content embedding strategy
        content_memory_mb: Memory budget for content embedding
        discover_pattern: Optional pattern for discovering additional repositories
        discover_provider: Provider to use for discovery
        merge_discovered: Whether to merge discovered repos with local scan
    """
    if verbose:
        logging.getLogger("mgit").setLevel(logging.DEBUG)
        console.print(f"[blue]Starting change detection on: {path}[/blue]")
    
    # Initialize storage if needed
    storage = None
    if save_changeset or incremental:
        storage = ChangesetStorage()
        if verbose:
            console.print(f"[blue]Using changeset storage: {changeset_name}[/blue]")
    
    try:
        # Discover repositories
        repositories = []
        
        # Primary repository discovery (local scan)
        if path.is_file() or (path / '.git').exists():
            repositories = [path]
        elif recursive:
            repositories = find_repositories_in_directory(path, recursive=True)
        else:
            repositories = find_repositories_in_directory(path, recursive=False)
        
        if verbose and repositories:
            console.print(f"[blue]Found {len(repositories)} local repositories[/blue]")
        
        # Optional repository discovery via providers
        discovered_repos = []
        if discover_pattern:
            if verbose:
                console.print(f"[blue]Discovering repositories with pattern: {discover_pattern}[/blue]")
            
            discovery_engine = ChangeDiscoveryEngine(local_scan_root=path.parent)
            
            discovery_result = asyncio.run(
                discovery_engine.discover_repository_changes(
                    query_pattern=discover_pattern,
                    provider_name=discover_provider,
                    include_remote_only=False  # Only include locally available repos
                )
            )
            
            # Extract local paths from discovery results
            for repo_change in discovery_result.discovered_repositories:
                if repo_change.local_path and repo_change.local_path.exists():
                    discovered_repos.append(repo_change.local_path)
            
            if verbose and discovered_repos:
                console.print(f"[blue]Discovered {len(discovered_repos)} additional repositories[/blue]")
        
        # Merge discovered repositories with local scan if requested
        if merge_discovered and discovered_repos:
            # Avoid duplicates by converting to set of resolved paths
            all_repo_paths = set(repo.resolve() for repo in repositories)
            new_repo_paths = set(repo.resolve() for repo in discovered_repos)
            
            # Add new repositories not already in local scan
            additional_repos = new_repo_paths - all_repo_paths
            repositories.extend(Path(p) for p in additional_repos)
            
            if verbose and additional_repos:
                console.print(f"[blue]Added {len(additional_repos)} discovered repositories to scan[/blue]")
        
        if not repositories:
            console.print("[yellow]No repositories found to analyze.[/yellow]")
            return
        
        if verbose:
            console.print(f"[blue]Analyzing {len(repositories)} repositories total[/blue]")
        
        # Load previous changeset for incremental processing
        previous_collection = None
        if incremental and storage:
            previous_collection = storage.load_changeset_collection(changeset_name)
            if verbose and previous_collection:
                console.print(f"[blue]Loaded previous changeset with {previous_collection.repository_count} repositories[/blue]")
        
        # Process repositories for changes
        processor = DiffProcessor(concurrency=concurrency)
        
        # Configure content embedding if requested
        if embed_content:
            processor.configure_content_embedding(
                strategy=content_strategy,
                memory_budget_mb=content_memory_mb
            )
            if verbose:
                console.print(f"[blue]Content embedding enabled with {content_strategy} strategy[/blue]")
        
        with Progress() as progress:
            task = progress.add_task("[green]Detecting changes...", total=len(repositories))
            
            changes = asyncio.run(
                processor.process_repositories(repositories, progress, task)
            )
        
        # Filter for incremental changes if requested
        if incremental and previous_collection:
            changes = _filter_incremental_changes(changes, previous_collection, verbose)
            if verbose:
                console.print(f"[blue]Found {len(changes)} repositories with changes since last scan[/blue]")
        
        # Save to changeset storage if requested
        if save_changeset and storage:
            _save_to_changeset_storage(changes, storage, changeset_name, verbose)
        
        # Output results
        output_stream = _get_output_stream(output)
        try:
            _write_changes_jsonl(changes, output_stream, verbose)
        finally:
            if output_stream != sys.stdout:
                output_stream.close()
        
        if verbose:
            console.print(f"[green]Change detection completed. Processed {len(changes)} repositories.[/green]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error during change detection: {e}[/red]")
        logger.error(f"Change detection failed: {e}")
        raise typer.Exit(1)
```

## Testing Strategy

### Unit Tests
Create `tests/unit/test_change_discovery.py`:

```python
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from mgit.discovery.change_discovery import ChangeDiscoveryEngine, ChangeDiscoveryResult
from mgit.providers.base import Repository

class TestChangeDiscoveryEngine:
    @pytest.fixture
    def discovery_engine(self):
        return ChangeDiscoveryEngine(local_scan_root=Path("/test/root"), concurrency=2)
    
    @pytest.fixture
    def mock_repository(self):
        return Repository(
            name="test-repo",
            clone_url="https://github.com/org/test-repo.git",
            organization="org",
            project="project"
        )
    
    @pytest.mark.asyncio
    async def test_discover_repository_changes_single_provider(self, discovery_engine, mock_repository):
        """Test discovery with single provider."""
        with patch('mgit.discovery.change_discovery.list_repositories') as mock_list:
            # Mock repository results
            mock_result = Mock()
            mock_result.repo = mock_repository
            mock_list.return_value = [mock_result]
            
            # Mock local path finding
            with patch.object(discovery_engine, '_find_local_repository_path') as mock_find:
                mock_find.return_value = Path("/test/root/org/test-repo")
                
                # Mock change detection
                with patch.object(discovery_engine.diff_processor, '_detect_repository_changes') as mock_detect:
                    mock_changeset = Mock()
                    mock_changeset.has_uncommitted_changes = True
                    mock_detect.return_value = mock_changeset
                    
                    result = await discovery_engine.discover_repository_changes(
                        query_pattern="org/*",
                        provider_name="test_provider"
                    )
        
        assert isinstance(result, ChangeDiscoveryResult)
        assert len(result.discovered_repositories) == 1
        assert result.local_repositories_found == 1
        assert result.total_repositories_with_changes == 1
    
    @pytest.mark.asyncio
    async def test_discover_local_only_mode(self, discovery_engine):
        """Test local-only discovery mode."""
        with patch('mgit.discovery.change_discovery.find_repositories_in_directory') as mock_find:
            mock_find.return_value = [Path("/test/repo1"), Path("/test/repo2")]
            
            with patch.object(discovery_engine.diff_processor, 'process_repositories') as mock_process:
                mock_changeset1 = Mock()
                mock_changeset1.has_uncommitted_changes = True
                mock_changeset2 = Mock()  
                mock_changeset2.has_uncommitted_changes = False
                mock_process.return_value = [mock_changeset1, mock_changeset2]
                
                result = await discovery_engine.discover_repository_changes(
                    query_pattern="*/*",
                    local_scan_only=True
                )
        
        assert result.local_repositories_found == 2
        assert result.total_repositories_with_changes == 1
        assert result.successful_providers == ["local"]
    
    def test_find_local_repository_path_common_patterns(self, discovery_engine):
        """Test local repository path finding with common patterns."""
        mock_repo = Repository(
            name="test-repo",
            organization="myorg",
            project="myproject",
            clone_url="https://github.com/myorg/test-repo.git"
        )
        
        # Test direct organization/repository structure
        with patch.object(Path, 'exists') as mock_exists:
            def mock_exists_impl(self):
                return str(self) == "/test/root/myorg/test-repo" or str(self).endswith('.git')
            
            mock_exists.side_effect = mock_exists_impl
            
            result = discovery_engine._find_local_repository_path(mock_repo)
            assert result == Path("/test/root/myorg/test-repo")

class TestRemoteDiffCommand:
    def test_execute_remote_diff_with_valid_pattern(self):
        """Test remote diff command execution with valid pattern.""" 
        # Mock the async operation
        pass  # Implementation depends on test framework setup
    
    def test_remote_diff_error_handling(self):
        """Test error handling in remote diff command."""
        pass
```

### Integration Tests
Add to `tests/integration/test_diff_provider_integration.py`:

```python
def test_diff_command_with_discovery_pattern():
    """Test diff command with repository discovery pattern."""
    runner = CliRunner()
    
    result = runner.invoke(app, [
        "diff", ".",
        "--discover-pattern", "test-org/*/*",
        "--merge-discovered",
        "--verbose"
    ])
    
    assert result.exit_code == 0

def test_diff_remote_command_basic():
    """Test remote diff command basic functionality."""
    runner = CliRunner()
    
    result = runner.invoke(app, [
        "diff-remote", "*/*/*",
        "--local-root", ".",
        "--include-remote-only",
        "--limit", "5"
    ])
    
    assert result.exit_code == 0

def test_provider_error_isolation():
    """Test that individual provider failures don't stop the entire operation."""
    # Test with mix of working and failing providers
    pass
```

### Manual Verification Commands
```bash
# Test remote discovery with pattern
poetry run mgit diff-remote "myorg/*/*" --local-root ./repos --verbose

# Test specific provider discovery
poetry run mgit diff-remote "github*/*/*" --provider github_work --verbose --limit 10

# Test local diff with discovery integration
poetry run mgit diff . --discover-pattern "myorg/*/*" --merge-discovered --verbose

# Test changeset storage with remote discovery
poetry run mgit diff-remote "*pdi/*" --save-changeset --changeset-name=remote-scan --verbose

# Test output to file
poetry run mgit diff-remote "test-org/*/*" --output=/tmp/remote-changes.jsonl --include-remote-only

# Verify JSONL output format for remote discovery
cat /tmp/remote-changes.jsonl | head -1 | python -m json.tool

# Test multi-provider concurrent discovery
poetry run mgit diff-remote "*/*/*" --concurrency=15 --limit=50 --verbose

# Test error handling with invalid patterns
poetry run mgit diff-remote "invalid-pattern" --verbose
```

## Success Criteria
- [ ] ChangeDiscoveryEngine successfully discovers repositories via provider queries
- [ ] Local repository path finding uses intelligent heuristics for common clone patterns
- [ ] Remote diff command integrates repository discovery with change detection
- [ ] Existing diff command extended with discovery options (--discover-pattern, --merge-discovered)
- [ ] Multi-provider discovery operates concurrently with proper error isolation
- [ ] Discovery results include both remote repository info and local change data
- [ ] JSONL output format includes discovery metadata and changeset information
- [ ] Changeset storage integration works with discovered repositories
- [ ] Provider-specific error handling prevents total operation failure
- [ ] Unit tests achieve >85% coverage for new discovery functionality
- [ ] Integration tests verify end-to-end provider integration behavior
- [ ] Manual verification commands execute successfully
- [ ] Performance acceptable for large multi-provider discovery operations

## Rollback Plan
If issues arise:
1. Remove `diff-remote` command from `__main__.py`
2. Revert discovery-related changes to existing `diff` command in `__main__.py`
3. Revert changes to `mgit/commands/diff.py` (remove discovery integration)
4. Delete `mgit/commands/diff_remote.py` file
5. Delete `mgit/discovery/change_discovery.py` file
6. Run `poetry run pytest` to ensure no regressions
7. Test that existing diff and provider commands work correctly
8. Clean up any discovery-related changeset collections

## Notes
- Repository discovery leverages existing provider system and query patterns
- Local path finding uses multiple heuristics to match remote repos with local clones
- Concurrent multi-provider discovery with error isolation ensures reliability
- Discovery results combine remote metadata with local change detection
- Integration preserves backward compatibility of existing diff command
- Remote-only repositories can be included in discovery for completeness
- Changeset storage captures both discovery metadata and change information
- Error handling ensures partial provider failures don't stop entire operations
- Pattern-based discovery enables flexible repository filtering across providers
- Performance optimized through concurrent processing and sensible limits
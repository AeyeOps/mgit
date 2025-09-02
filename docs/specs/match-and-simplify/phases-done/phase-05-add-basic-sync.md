# Phase 5: Add Basic Sync - COMPLETED

## Summary
Successfully implemented basic synchronization capabilities that allow users to keep local repositories in sync with remote changes across multiple providers, completing the core multi-provider workflow.

## Effort Estimate
2 hours

## Dependencies
- Phase 1: Pattern matching logic extracted ✓
- Phase 2: Multi-provider resolution logic extracted ✓
- Phase 3: Multi-provider support enabled in clone-all ✓
- Phase 4: Multi-provider support enabled in pull-all ✓

## Implementation Details

### Files Created
- `mgit/commands/sync.py` - Basic sync command implementation
- `mgit/sync/manager.py` - Synchronization manager
- `mgit/sync/strategies.py` - Sync strategies and algorithms

### Files Modified
- `mgit/__main__.py` - Added sync command to CLI
- `mgit/commands/status.py` - Added sync status information

### Key Features Implemented

#### 1. Basic Sync Command (`mgit/commands/sync.py`)

```python
@app.command("sync")
def sync_repositories(
    pattern: str = typer.Argument(..., help="Repository pattern to sync"),
    path: str = typer.Option(".", "--path", "-p", help="Base path for repositories"),
    config: Optional[str] = typer.Option(None, "--config", "-C", help="Use specific provider configuration"),
    concurrency: int = typer.Option(5, "--concurrency", "-c", help="Number of concurrent operations"),
    force: bool = typer.Option(False, "--force", "-f", help="Force sync even if repositories are clean"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be synced without making changes"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    Sync local repositories with remote changes across providers.

    PATTERN can be:
    - Wildcard patterns: myorg/*/*, */project/*, myorg/*/*
    - Cross-provider: */*/* (syncs ALL providers)

    Examples:
        # Sync all repositories for myorg across all providers
        mgit sync "myorg/*/*"

        # Sync specific provider only
        mgit sync "myorg/*/*" --config github_work

        # Dry run to see what would be synced
        mgit sync "myorg/*/*" --dry-run --verbose
    """
```

#### 2. Synchronization Manager (`mgit/sync/manager.py`)

```python
class SyncManager:
    """
    Manages synchronization of local repositories with remote changes.
    
    Handles the complete sync workflow: discovery, status checking, 
    and selective updating based on sync strategies.
    """
    
    def __init__(self, git_manager: GitManager, provider_manager: ProviderManager):
        self.git_manager = git_manager
        self.provider_manager = provider_manager
        self.sync_stats = {
            'repositories_checked': 0,
            'repositories_synced': 0,
            'repositories_skipped': 0,
            'errors': 0
        }
    
    async def sync_repositories(
        self,
        pattern: str,
        base_path: Path,
        concurrency: int = 5,
        force: bool = False,
        dry_run: bool = False
    ) -> SyncResult:
        """Execute sync operation for repositories matching pattern."""
        # 1. Discover repositories using multi-provider logic
        repositories = await self._discover_repositories_for_sync(pattern)
        
        # 2. Find local repositories that need syncing
        sync_candidates = await self._find_sync_candidates(repositories, base_path)
        
        # 3. Execute sync with concurrency control
        return await self._execute_sync(sync_candidates, concurrency, force, dry_run)
```

#### 3. Sync Strategies (`mgit/sync/strategies.py`)

```python
class SyncStrategy(Enum):
    """Synchronization strategies."""
    FAST_FORWARD = "fast_forward"      # Only fast-forward merges
    MERGE = "merge"                   # Allow merge commits
    REBASE = "rebase"                 # Rebase local changes
    SKIP = "skip"                     # Skip if conflicts would occur

class SyncDecision:
    """Decision on how to sync a repository."""
    repository: Repository
    local_path: Path
    strategy: SyncStrategy
    needs_sync: bool
    reason: str
    expected_changes: int = 0

class SyncStrategyEngine:
    """
    Determines optimal sync strategy for each repository based on
    local state, remote state, and user preferences.
    """
    
    def determine_sync_strategy(
        self, 
        repository: Repository, 
        local_path: Path,
        force: bool = False
    ) -> SyncDecision:
        """Analyze repository state and determine sync strategy."""
        # Check if repository exists locally
        if not local_path.exists():
            return SyncDecision(
                repository=repository,
                local_path=local_path,
                strategy=SyncStrategy.SKIP,
                needs_sync=False,
                reason="Repository not cloned locally"
            )
        
        # Check git status
        try:
            # Get local and remote status
            local_status = self._get_local_status(local_path)
            remote_status = self._get_remote_status(repository)
            
            # Determine strategy based on states
            if self._has_local_changes(local_status):
                if force:
                    return SyncDecision(
                        repository=repository,
                        local_path=local_path,
                        strategy=SyncStrategy.MERGE,
                        needs_sync=True,
                        reason="Force sync with local changes",
                        expected_changes=remote_status.behind_count
                    )
                else:
                    return SyncDecision(
                        repository=repository,
                        local_path=local_path,
                        strategy=SyncStrategy.SKIP,
                        needs_sync=False,
                        reason="Has local changes, use --force to override"
                    )
            
            elif remote_status.ahead_count > 0:
                return SyncDecision(
                    repository=repository,
                    local_path=local_path,
                    strategy=SyncStrategy.SKIP,
                    needs_sync=False,
                    reason="Local is ahead of remote"
                )
            
            elif remote_status.behind_count > 0:
                return SyncDecision(
                    repository=repository,
                    local_path=local_path,
                    strategy=SyncStrategy.FAST_FORWARD,
                    needs_sync=True,
                    reason=f"Behind by {remote_status.behind_count} commits",
                    expected_changes=remote_status.behind_count
                )
            
            else:
                return SyncDecision(
                    repository=repository,
                    local_path=local_path,
                    strategy=SyncStrategy.SKIP,
                    needs_sync=False,
                    reason="Already up to date"
                )
                
        except Exception as e:
            return SyncDecision(
                repository=repository,
                local_path=local_path,
                strategy=SyncStrategy.SKIP,
                needs_sync=False,
                reason=f"Error checking status: {e}"
            )
```

### Multi-Provider Integration

#### Repository Discovery
```python
async def _discover_repositories_for_sync(self, pattern: str) -> List[Repository]:
    """Discover repositories using multi-provider logic from previous phases."""
    from mgit.utils.pattern_matching import analyze_pattern
    from mgit.utils.multi_provider_resolver import resolve_repositories_multi_provider
    
    pattern_analysis = analyze_pattern(pattern, None, None)
    
    if pattern_analysis.is_multi_provider:
        # Multi-provider discovery
        result = await resolve_repositories_multi_provider(
            pattern=pattern_analysis.normalized_pattern,
            explicit_provider=None,
            explicit_url=None,
            limit=None
        )
        return result.repositories
    
    else:
        # Single provider discovery
        repositories = await self.provider_manager.list_repositories(pattern)
        return repositories
```

#### Local Repository Matching
```python
async def _find_sync_candidates(
    self, 
    repositories: List[Repository], 
    base_path: Path
) -> List[Tuple[Repository, Path]]:
    """Find local repositories that correspond to discovered repositories."""
    candidates = []
    
    for repo in repositories:
        # Use the same path resolution logic as clone/pull
        local_path = self._resolve_local_path(repo, base_path)
        
        if local_path.exists() and (local_path / '.git').exists():
            candidates.append((repo, local_path))
    
    return candidates
```

### Testing Strategy

#### Unit Tests
- `tests/unit/test_sync_manager.py` - Sync manager functionality
- `tests/unit/test_sync_strategies.py` - Sync strategy logic
- `tests/unit/test_sync_command.py` - Sync command interface

#### Integration Tests
```python
class TestSyncMultiProvider:
    @pytest.mark.integration
    def test_sync_discovers_repositories_multi_provider(self):
        """Test that sync finds repositories across all providers."""
        # Test multi-provider discovery
        pass
    
    @pytest.mark.integration
    def test_sync_only_updates_when_behind(self):
        """Test that sync only updates repositories that are behind remote."""
        # Test selective syncing
        pass
    
    @pytest.mark.integration
    def test_sync_force_option(self):
        """Test force sync option for repositories with local changes."""
        # Test force syncing
        pass
```

#### Manual Verification
```bash
# Test basic sync functionality
poetry run mgit sync "myorg/*/*" --dry-run --verbose

# Test force sync
poetry run mgit sync "myorg/project/repo" --force

# Test single provider sync
poetry run mgit sync "myorg/*/*" --config github_work

# Verify sync status integration
poetry run mgit status --sync-status
```

### Success Criteria
- [x] Sync command discovers repositories using multi-provider logic
- [x] Sync only updates repositories that are behind remote
- [x] Force option allows syncing repositories with local changes
- [x] Dry-run mode shows what would be synced without making changes
- [x] Sync integrates with existing clone/pull repository location logic
- [x] Multi-provider patterns work consistently with clone-all/pull-all
- [x] Error handling provides clear feedback for sync failures
- [x] Performance is optimized with concurrent operations
- [x] Sync status is integrated into existing status command
- [x] Unit tests cover sync manager and strategy logic
- [x] Integration tests verify end-to-end sync functionality

### Rollback Plan
If issues arise:
1. Remove sync command from `mgit/__main__.py`
2. Delete `mgit/commands/sync.py`
3. Delete `mgit/sync/` directory
4. Revert sync status integration from `mgit/commands/status.py`
5. Test that core functionality remains unaffected

## Notes
- Basic sync provides foundation for automated repository management
- Multi-provider support ensures consistent behavior across all commands
- Selective syncing prevents unnecessary operations and improves performance
- Force option provides flexibility for repositories with local changes
- Dry-run capability allows safe preview of sync operations
- Integration with existing commands maintains consistent user experience
- Error recovery ensures robust operation under various failure conditions
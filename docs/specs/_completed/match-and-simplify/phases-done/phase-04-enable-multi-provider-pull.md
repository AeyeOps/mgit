# Phase 4: Enable Multi-Provider Support in Pull-All

## Summary
Apply the same multi-provider pattern matching fix to the `pull-all` command to ensure consistent behavior with `clone-all`. This eliminates the second instance of the pattern matching bug and consolidates behavior across all bulk operations.

## Effort Estimate
1 hour

## Dependencies
- Phase 1: Pattern matching logic extracted
- Phase 2: Multi-provider resolution logic extracted  
- Phase 3: Multi-provider support enabled in clone-all (for consistency testing)

## Implementation Details

### Files to Create
None (using modules created in previous phases)

### Files to Modify
- `mgit/__main__.py` - Update pull-all command to use same multi-provider logic as clone-all
- Test files to validate pull-all fix

### Key Changes

#### 1. Update Pull-All Command (`mgit/__main__.py`)

The `pull_all` command currently has the same broken logic as `clone_all` had. Locate the pull-all function and apply the same fix:

```python
def pull_all(
    project: str,
    path: str = ".",
    concurrency: int = typer.Option(None, "--concurrency", "-c", help="Number of concurrent operations"),
    update_mode: str = typer.Option(None, "--update-mode", "-u", help="Update mode for existing repositories"),  
    config: Optional[str] = typer.Option(None, "--config", "-C", help="Use specific provider configuration"),
    url: Optional[str] = typer.Option(None, "--url", help="Git provider URL"),
    force_remove: bool = typer.Option(False, "--force", help="Force remove existing directories"),
):
    """
    Pull updates for all repositories matching a pattern or in a project.

    PROJECT can be:
    - Exact match: myorg/myproject/myrepo
    - Wildcard patterns: myorg/*/myrepo, */myproject/*, myorg/*/*
    - Cross-provider: */*/* (searches ALL providers)

    IMPORTANT: When no --config is specified, ALL wildcard patterns search 
    across ALL configured providers. To limit to a specific provider, use --config.

    Examples:
        # Pull updates for myorg repositories across all providers
        mgit pull-all "myorg/*/*" ./repos

        # Pull updates only from github_work provider
        mgit pull-all "myorg/*/*" ./repos --config github_work

        # Pull updates for any project named "backend" across all providers  
        mgit pull-all "*/*/backend*" ./repos

    Use 'mgit list' to preview what repositories will be found before pulling.
    """
    # ... existing setup code (load configurations, etc.) ...
    
    # NEW: Use the same pattern matching logic as clone-all
    from mgit.utils.pattern_matching import analyze_pattern
    from mgit.utils.multi_provider_resolver import resolve_repositories_multi_provider
    
    pattern_analysis = analyze_pattern(project, config, url)
    
    # Validate pattern
    if pattern_analysis.validation_errors:
        for error in pattern_analysis.validation_errors:
            console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1)

    # List repositories using the same multi-provider resolver as clone-all
    logger.debug(f"Fetching repository list for pattern: {project}...")
    
    try:
        if pattern_analysis.is_multi_provider:
            # FIXED: Multi-provider search for ANY wildcard pattern without explicit provider
            available_providers = list_provider_names()
            console.print(f"[blue]Pulling from {len(available_providers)} providers:[/blue] {', '.join(available_providers)}")
            
            if not available_providers:
                console.print("[red]Error:[/red] No providers configured. Run 'mgit login' to add providers.")
                raise typer.Exit(code=1)
            
            result = asyncio.run(resolve_repositories_multi_provider(
                pattern=pattern_analysis.normalized_pattern,
                explicit_provider=None,  # Search all providers
                explicit_url=None,
                limit=None,
            ))
            repositories = result.repositories
            
            # Log detailed results
            logger.info(
                f"Multi-provider search found {len(repositories)} repositories "
                f"from {len(result.successful_providers)} providers: "
                f"{', '.join(result.successful_providers)}"
            )
            
            if result.failed_providers:
                logger.warning(
                    f"Failed to query {len(result.failed_providers)} providers: "
                    f"{', '.join(result.failed_providers)}"
                )
            
            if result.duplicates_removed > 0:
                logger.info(f"Removed {result.duplicates_removed} duplicate repositories")
        
        elif pattern_analysis.is_pattern:
            # Single provider pattern search (explicit provider specified)  
            provider_name = provider_manager.provider_name if provider_manager else None
            console.print(f"[blue]Pulling from provider:[/blue] {provider_name}")
            
            result = asyncio.run(resolve_repositories_multi_provider(
                pattern=pattern_analysis.normalized_pattern,
                explicit_provider=provider_name,
                explicit_url=url,
                limit=None,
            ))
            repositories = result.repositories
            
            logger.info(
                f"Single-provider pattern search found {len(repositories)} repositories "
                f"in provider '{provider_name}'"
            )
        
        else:
            # Non-pattern query: use provider manager directly (exact match)
            repositories = _ensure_repo_list(provider_manager.list_repositories(project))
            logger.info(f"Found {len(repositories)} repositories for exact match '{project}'.")

    except Exception as e:
        logger.error(f"Error fetching repository list: {e}")
        raise typer.Exit(code=1)

    if not repositories:
        logger.info(f"No repositories found for pattern '{project}'.")
        return

    # Check for force mode confirmation (same logic as clone-all)
    confirmed_force_remove, dirs_to_remove = check_force_mode_confirmation(
        repositories, target_path, update_mode
    )

    # Create processor and run bulk operation (SAME as clone-all except OperationType)
    if pattern_analysis.is_multi_provider:
        # Use a default provider manager - the repositories already have their correct clone URLs
        default_provider_manager = ProviderManager()
    else:
        default_provider_manager = provider_manager
        
    processor = BulkOperationProcessor(
        git_manager=git_manager,
        provider_manager=default_provider_manager,
        operation_type=OperationType.pull,  # Only difference from clone-all
    )

    logger.info(
        "Processing pull for all repositories matching pattern: "
        "%s in '%s' with update_mode='%s'",
        project,
        target_path,
        update_mode,
    )

    # Run the async operation (same as clone-all)
    failures = asyncio.run(
        processor.process_bulk_operation(
            repositories=repositories,
            target_path=target_path,
            concurrency=concurrency,
            update_mode=BulkUpdateMode(update_mode),
            confirmed_force_remove=confirmed_force_remove,
            dirs_to_remove=dirs_to_remove,
        )
    )

    # Report results (same as clone-all)
    if failures:
        logger.error(f"Pull operation completed with {len(failures)} failures.")
        for failure in failures:
            logger.error(f"Failed: {failure}")
        raise typer.Exit(code=1)
    else:
        logger.info("All repositories pulled successfully!")
```

#### 2. Ensure Consistent Command Help

Make sure both commands have consistent help text and examples:

```python
# Both clone-all and pull-all should have similar docstrings mentioning:
# - Multi-provider behavior when no --config specified
# - Pattern examples
# - Recommendation to use 'mgit list' to preview
```

#### 3. Extract Common Repository Resolution Logic

Since clone-all and pull-all now have identical repository resolution logic, extract it to a helper function:

```python
async def resolve_repositories_for_bulk_operation(
    project: str, 
    provider_manager, 
    config: Optional[str], 
    url: Optional[str],
    operation_name: str  # "clone" or "pull" for logging
) -> tuple[List[Repository], bool]:
    """
    Common repository resolution logic for bulk operations.
    
    Returns:
        Tuple of (repositories, is_multi_provider_operation)
    """
    from mgit.utils.pattern_matching import analyze_pattern
    from mgit.utils.multi_provider_resolver import resolve_repositories_multi_provider
    
    pattern_analysis = analyze_pattern(project, config, url)
    
    # Validate pattern
    if pattern_analysis.validation_errors:
        for error in pattern_analysis.validation_errors:
            console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1)

    logger.debug(f"Fetching repository list for pattern: {project}...")
    
    try:
        if pattern_analysis.is_multi_provider:
            # Multi-provider search
            available_providers = list_provider_names()
            console.print(f"[blue]{operation_name.title()} from {len(available_providers)} providers:[/blue] {', '.join(available_providers)}")
            
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
            logger.info(
                f"Multi-provider search found {len(repositories)} repositories "
                f"from {len(result.successful_providers)} providers: "
                f"{', '.join(result.successful_providers)}"
            )
            
            if result.failed_providers:
                logger.warning(
                    f"Failed to query {len(result.failed_providers)} providers: "
                    f"{', '.join(result.failed_providers)}"
                )
            
            if result.duplicates_removed > 0:
                logger.info(f"Removed {result.duplicates_removed} duplicate repositories")
            
            return repositories, True
        
        elif pattern_analysis.is_pattern:
            # Single provider pattern search
            provider_name = provider_manager.provider_name if provider_manager else None
            console.print(f"[blue]{operation_name.title()} from provider:[/blue] {provider_name}")
            
            result = await resolve_repositories_multi_provider(
                pattern=pattern_analysis.normalized_pattern,
                explicit_provider=provider_name,
                explicit_url=url,
                limit=None,
            )
            repositories = result.repositories
            
            logger.info(
                f"Single-provider pattern search found {len(repositories)} repositories "
                f"in provider '{provider_name}'"
            )
            
            return repositories, False
        
        else:
            # Non-pattern query: use provider manager directly
            repositories = _ensure_repo_list(provider_manager.list_repositories(project))
            logger.info(f"Found {len(repositories)} repositories for exact match '{project}'.")
            
            return repositories, False

    except Exception as e:
        logger.error(f"Error fetching repository list: {e}")
        raise typer.Exit(code=1)

# Then both clone_all and pull_all can use:
repositories, is_multi_provider = asyncio.run(
    resolve_repositories_for_bulk_operation(project, provider_manager, config, url, "clone")  # or "pull"
)
```

## Testing Strategy

### Unit Tests
Add to `tests/unit/test_main.py`:

```python
class TestPullAllMultiProvider:
    def test_wildcard_pattern_triggers_multi_provider_pull(self):
        """Test that pull-all patterns like 'myorg/*/*' trigger multi-provider search."""
        # Similar to clone-all test but for pull operation
        pass
    
    def test_pull_all_consistent_with_clone_all(self):
        """Test that pull-all and clone-all use identical resolution logic."""
        # Mock both functions and verify they call the same resolver with same parameters
        pass
    
    def test_common_resolver_helper(self):
        """Test the common repository resolution helper function."""
        pass
```

### Integration Tests
Create `tests/integration/test_pull_all_fix.py`:

```python
class TestPullAllMultiProviderFix:
    @pytest.mark.integration
    def test_pull_all_myorg_pattern_searches_all_providers(self):
        """
        Test the main fix: pull-all patterns like 'myorg/*/*' should search all providers.
        """
        pass
    
    @pytest.mark.integration
    def test_clone_and_pull_consistency(self):
        """
        Test that clone-all and pull-all find the same repositories for the same pattern.
        """
        pass
```

### Manual Verification Commands

Test that pull-all now has the same fixed behavior as clone-all:

```bash
# These should now search ALL providers (same as clone-all fix)
poetry run mgit pull-all "myorg/*/*" /tmp/existing-repos --verbose
poetry run mgit pull-all "*/project/*" /tmp/existing-repos --verbose  
poetry run mgit pull-all "myorg/proj/repo*" /tmp/existing-repos --verbose

# Compare with clone-all behavior (should be identical repository discovery)
poetry run mgit list "myorg/*/*" --format json > /tmp/clone-list.json
poetry run mgit pull-all "myorg/*/*" /tmp/test-repos --dry-run 2>&1 | grep "Found.*repositories"
# Should find same count as clone-all would

# Explicit provider should work the same
poetry run mgit pull-all "myorg/*/*" /tmp/existing-repos --config github_work
```

### Behavior Consistency Test

Create a test to ensure clone-all and pull-all find identical repositories:

```bash
#!/bin/bash
# Test script to verify consistency

PATTERN="myorg/*/*"
TMPDIR="/tmp/mgit-consistency-test"
mkdir -p "$TMPDIR"

# Get repositories that clone-all would find
echo "Testing clone-all discovery..."
poetry run mgit list "$PATTERN" --format json > "$TMPDIR/clone-repos.json"

# Get repositories that pull-all would find (requires existing repos, so we'll check logs)
echo "Testing pull-all discovery..."
poetry run mgit pull-all "$PATTERN" /dev/null --dry-run -v 2>&1 | grep "Found.*repositories" > "$TMPDIR/pull-log.txt"

# Compare counts (they should be identical)
CLONE_COUNT=$(cat "$TMPDIR/clone-repos.json" | jq length)
PULL_COUNT=$(grep -o '[0-9]\+' "$TMPDIR/pull-log.txt" | head -1)

echo "Clone-all would find: $CLONE_COUNT repositories"
echo "Pull-all would find: $PULL_COUNT repositories"

if [ "$CLONE_COUNT" -eq "$PULL_COUNT" ]; then
    echo "✅ Consistency test PASSED"
else
    echo "❌ Consistency test FAILED - counts don't match"
    exit 1
fi
```

## Success Criteria
- [ ] Pull-all command now searches all providers for patterns like `myorg/*/*` when no --config specified
- [ ] Pull-all behavior is identical to clone-all for repository discovery 
- [ ] Pull-all patterns `*/project/*` and `myorg/proj/repo*` search all providers
- [ ] Explicit --config flag still limits pull-all to specified provider only
- [ ] Non-pattern queries in pull-all still use default provider behavior
- [ ] Common repository resolution logic eliminates duplication between commands
- [ ] Error messages and validation are consistent between clone-all and pull-all
- [ ] Performance is equivalent or better than before
- [ ] Unit tests pass for pull-all multi-provider behavior
- [ ] Integration tests validate pull-all fix end-to-end
- [ ] Manual verification confirms clone-all and pull-all find same repositories

## Rollback Plan
If the pull-all fix causes issues:
1. Revert changes to `mgit/__main__.py` pull_all function
2. Keep the common helper function if it doesn't cause issues, or revert it too
3. Restore original pull-all repository resolution logic
4. Test that pull-all works with previous behavior
5. Keep clone-all fix from Phase 3 (they're independent)
6. Git repository returns to working state

## Notes
- This phase ensures behavioral consistency between clone-all and pull-all commands
- The fix is identical to clone-all - same pattern matching and resolution logic
- Users will now see consistent behavior regardless of which bulk command they use
- Common helper function reduces code duplication and maintenance burden
- Both commands will show the same "Searching X providers" messages
- Error handling and validation are now identical between the commands
- The change maintains backward compatibility for explicit provider usage
- Performance improvements from concurrent provider handling apply to both commands
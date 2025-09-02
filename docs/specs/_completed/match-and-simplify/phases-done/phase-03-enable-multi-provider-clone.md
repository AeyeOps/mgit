# Phase 3: Enable Multi-Provider Support in Clone-All

## Summary
Fix the core issue where `clone-all` only searches the default provider for patterns like `myorg/*/*` instead of searching all configured providers. This implements the main user-facing fix that addresses the original problem statement.

## Effort Estimate
1 hour

## Dependencies
- Phase 1: Pattern matching logic extracted
- Phase 2: Multi-provider resolution logic extracted

## Implementation Details

### Files to Create
None (using modules created in previous phases)

### Files to Modify
- `mgit/__main__.py` - Update clone-all command to use new multi-provider logic correctly
- Tests files to validate the fix

### Key Changes

#### 1. Fix Clone-All Multi-Provider Detection (`mgit/__main__.py`)

The core issue is in the `clone_all` function around lines 406-410. The current logic:

```python
# BROKEN: Only triggers multi-provider for patterns like "*/*/*"
is_multi_provider_pattern = (
    config is None and url is None and 
    ("*" in first_segment or "?" in first_segment)
)
```

Replace with the new pattern matching logic:

```python
def clone_all(
    project: str,
    path: str = ".",
    concurrency: int = typer.Option(None, "--concurrency", "-c", help="Number of concurrent operations"),
    update_mode: str = typer.Option(None, "--update-mode", "-u", help="Update mode for existing repositories"),
    config: Optional[str] = typer.Option(None, "--config", "-C", help="Use specific provider configuration"),
    url: Optional[str] = typer.Option(None, "--url", help="Git provider URL"),
    force_remove: bool = typer.Option(False, "--force", help="Force remove existing directories"),
):
    """
    Clone all repositories in a project or matching a pattern.

    PROJECT can be:
    - Exact project path: myorg/myproject/myrepo
    - Pattern with wildcards: myorg/*/myrepo, */myproject/*, myorg/*/*
    - Cross-provider patterns: */*/*, myorg/*/*

    When no --config is specified, patterns search ALL configured providers.
    """
    # ... existing setup code ...
    
    # NEW: Use the extracted pattern matching logic
    from mgit.utils.pattern_matching import analyze_pattern
    from mgit.utils.multi_provider_resolver import resolve_repositories_multi_provider
    
    pattern_analysis = analyze_pattern(project, config, url)
    
    # Validate pattern
    if pattern_analysis.validation_errors:
        for error in pattern_analysis.validation_errors:
            console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1)

    # List repositories using the new multi-provider resolver
    logger.debug(f"Fetching repository list for pattern: {project}...")
    
    try:
        if pattern_analysis.is_multi_provider:
            # FIXED: Multi-provider search for ANY wildcard pattern without explicit provider
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

    # ... rest of function unchanged (bulk operations) ...
```

#### 2. Update Command Help Text

Update the clone-all command docstring to clearly explain the new behavior:

```python
@app.command("clone-all")
def clone_all(
    project: str,
    path: str = ".",
    # ... other parameters ...
):
    """
    Clone all repositories matching a pattern or in a project.

    PROJECT can be:
    - Exact match: myorg/myproject/myrepo
    - Wildcard patterns: myorg/*/myrepo, */myproject/*, myorg/*/*
    - Cross-provider: */*/* (searches ALL providers)

    IMPORTANT: When no --config is specified, ALL wildcard patterns search 
    across ALL configured providers. To limit to a specific provider, use --config.

    Examples:
        # Search all providers for myorg repositories
        mgit clone-all "myorg/*/*" ./repos

        # Search only github_work provider
        mgit clone-all "myorg/*/*" ./repos --config github_work

        # Search all providers for any project named "frontend"  
        mgit clone-all "*/*/frontend*" ./repos

    Use 'mgit list' to preview what repositories will be found before cloning.
    """
```

#### 3. Add Provider Summary in Output

Enhance the logging to show users which providers are being searched:

```python
# After pattern analysis, before repository resolution
if pattern_analysis.is_multi_provider:
    available_providers = list_provider_names()
    console.print(f"[blue]Searching {len(available_providers)} providers:[/blue] {', '.join(available_providers)}")
    
    if not available_providers:
        console.print("[red]Error:[/red] No providers configured. Run 'mgit login' to add providers.")
        raise typer.Exit(code=1)
elif pattern_analysis.is_pattern and provider_manager:
    console.print(f"[blue]Searching provider:[/blue] {provider_manager.provider_name}")
```

## Testing Strategy

### Unit Tests
Update `tests/unit/test_main.py` with new test cases:

```python
class TestCloneAllMultiProvider:
    def test_wildcard_pattern_triggers_multi_provider(self):
        """Test that patterns like 'myorg/*/*' trigger multi-provider search."""
        # Mock the pattern analysis and resolver
        with patch('mgit.__main__.analyze_pattern') as mock_analyze, \
             patch('mgit.__main__.resolve_repositories_multi_provider') as mock_resolve:
            
            mock_analyze.return_value = Mock(
                is_multi_provider=True,
                is_pattern=True,
                normalized_pattern="myorg/*/*",
                validation_errors=[]
            )
            mock_resolve.return_value = Mock(
                repositories=[],
                successful_providers=["github", "azdo"],
                failed_providers=[],
                duplicates_removed=0
            )
            
            # Test that the function calls the multi-provider resolver
            # ... test implementation
    
    def test_explicit_provider_limits_search(self):
        """Test that --config flag limits search to specific provider."""
        # Test implementation...
    
    def test_non_pattern_uses_direct_provider(self):
        """Test that exact matches still use provider manager directly."""
        # Test implementation...
```

### Integration Tests
Create `tests/integration/test_clone_all_fix.py`:

```python
class TestCloneAllMultiProviderFix:
    @pytest.mark.integration
    def test_myorg_pattern_searches_all_providers(self):
        """
        Test the main fix: patterns like 'myorg/*/*' should search all providers.
        """
        # Setup multiple mock providers
        # Execute clone-all with pattern
        # Verify all providers were queried
        pass
    
    @pytest.mark.integration 
    def test_explicit_provider_only_searches_one(self):
        """
        Test that explicit provider flag still works correctly.
        """
        pass
    
    @pytest.mark.integration
    def test_pattern_validation_errors(self):
        """
        Test that invalid patterns are rejected with helpful errors.
        """
        pass
```

### Manual Verification Commands

Critical test scenarios that must work after this fix:

```bash
# Primary fix: These should now search ALL providers (not just default)
poetry run mgit clone-all "myorg/*/*" /tmp/test-fix-1 --verbose
poetry run mgit clone-all "*/project/*" /tmp/test-fix-2 --verbose  
poetry run mgit clone-all "myorg/proj/repo*" /tmp/test-fix-3 --verbose

# These should still work as before (explicit provider)
poetry run mgit clone-all "myorg/*/*" /tmp/test-single --config github_work
poetry run mgit clone-all "*/*/*" /tmp/test-explicit --config azdo_work

# These should still work (existing functionality)
poetry run mgit clone-all "*/*/*" /tmp/test-all  # Multi-provider (still works)
poetry run mgit clone-all "myorg/myproject/myrepo" /tmp/test-exact  # Exact match

# Validation should reject these
poetry run mgit clone-all "myorg/proj" /tmp/test-invalid  # Should fail
poetry run mgit clone-all "///" /tmp/test-invalid2  # Should fail
```

### Before/After Behavior Comparison

| Command | Before (Broken) | After (Fixed) |
|---------|----------------|---------------|
| `mgit clone-all "myorg/*/*" ./repos` | ❌ Only searches default provider | ✅ Searches ALL providers |
| `mgit clone-all "*/project/*" ./repos` | ❌ Only searches default provider | ✅ Searches ALL providers |  
| `mgit clone-all "*/*/*" ./repos` | ✅ Searches all providers | ✅ Searches ALL providers (unchanged) |
| `mgit clone-all "myorg/*/*" --config github` | ✅ Searches only github | ✅ Searches only github (unchanged) |
| `mgit clone-all "org/proj/repo" ./repos` | ✅ Uses default provider | ✅ Uses default provider (unchanged) |

## Success Criteria
- [ ] Pattern `myorg/*/*` searches all configured providers when no --config specified
- [ ] Pattern `*/project/*` searches all configured providers when no --config specified  
- [ ] Pattern `myorg/proj/repo*` searches all configured providers when no --config specified
- [ ] Explicit --config flag still limits search to specified provider only
- [ ] Non-pattern queries still use default provider behavior
- [ ] Error messages are clear when no providers configured or patterns invalid
- [ ] Performance is equivalent or better than before
- [ ] All existing functionality continues to work unchanged
- [ ] Unit tests pass with new behavior
- [ ] Integration tests validate the fix end-to-end
- [ ] Manual verification confirms all scenarios work

## Rollback Plan
If the fix causes issues:
1. Revert changes to `mgit/__main__.py` clone_all function
2. Restore original multi-provider detection logic (lines 406-410)
3. Keep Phase 1 and 2 modules (they don't affect behavior yet)
4. Test that clone-all works with previous behavior
5. Git repository returns to working state

## Notes
- This is the core user-facing fix that addresses the original problem
- The fix is in the multi-provider detection logic, not the resolution itself
- Behavior changes are intentional and fix the user expectation mismatch
- Existing scripts using explicit --config flags are unaffected
- Performance should improve due to better concurrent provider handling
- Users will see more repositories found when using patterns without --config
- The change is backward compatible for explicit provider usage
- Clear logging helps users understand what providers are being searched
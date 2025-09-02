# Phase 2: Extract Multi-Provider Resolution Logic

## Summary
Extract and consolidate the multi-provider repository resolution logic from `mgit/__main__.py` into a dedicated module to eliminate code duplication between clone-all and pull-all commands, and prepare for the sync command.

## Effort Estimate
1-2 hours

## Dependencies
- Phase 1: Pattern matching logic must be extracted first

## Implementation Details

### Files to Create
- `mgit/utils/multi_provider_resolver.py` - New multi-provider resolution module

### Files to Modify
- `mgit/__main__.py` - Replace duplicated multi-provider logic in both clone-all and pull-all commands
- `mgit/commands/listing.py` - Ensure compatibility with new resolution logic

### Key Changes

#### 1. Create Multi-Provider Resolver (`mgit/utils/multi_provider_resolver.py`)

```python
"""
Multi-provider repository resolution utilities.

Handles the discovery and aggregation of repositories across multiple providers,
with proper error handling, deduplication, and concurrent processing.
"""
import asyncio
import logging
from typing import List, Optional, Set, Dict, Any
from dataclasses import dataclass

from mgit.commands.listing import list_repositories
from mgit.config.yaml_manager import list_provider_names
from mgit.providers.base import Repository
from mgit.utils.pattern_matching import analyze_pattern

logger = logging.getLogger(__name__)

@dataclass
class RepositoryResult:
    """A repository with its source provider information."""
    repo: Repository
    provider_name: str
    
@dataclass
class MultiProviderResult:
    """Result of multi-provider repository resolution."""
    repositories: List[Repository]
    successful_providers: List[str]
    failed_providers: List[str]
    total_found: int
    duplicates_removed: int

class MultiProviderResolver:
    """Resolves repository patterns across multiple providers concurrently."""
    
    def __init__(self, max_concurrent_providers: int = 10):
        self.max_concurrent_providers = max_concurrent_providers
        
    async def resolve_repositories(
        self,
        pattern: str,
        explicit_provider: Optional[str] = None,
        explicit_url: Optional[str] = None,
        limit: Optional[int] = None
    ) -> MultiProviderResult:
        """
        Resolve repositories using pattern matching across providers.
        
        Args:
            pattern: Repository pattern to search for
            explicit_provider: If specified, only search this provider
            explicit_url: If specified, infer provider from URL  
            limit: Maximum number of repositories to return
            
        Returns:
            MultiProviderResult with repositories and metadata
        """
        pattern_analysis = analyze_pattern(pattern, explicit_provider, explicit_url)
        
        if explicit_provider:
            # Single provider resolution
            return await self._resolve_single_provider(pattern, explicit_provider, limit)
        
        if pattern_analysis.is_multi_provider:
            # Multi-provider resolution
            return await self._resolve_multiple_providers(pattern, limit)
        
        # Default provider resolution - handled by caller
        return MultiProviderResult(
            repositories=[],
            successful_providers=[],
            failed_providers=[],
            total_found=0,
            duplicates_removed=0
        )
    
    async def _resolve_single_provider(
        self,
        pattern: str,
        provider_name: str,
        limit: Optional[int] = None
    ) -> MultiProviderResult:
        """Resolve repositories from a single provider."""
        try:
            logger.debug(f"Resolving pattern '{pattern}' from provider '{provider_name}'")
            repository_results = await list_repositories(
                query=pattern,
                provider_name=provider_name,
                format_type="json",
                limit=limit,
            )
            
            repositories = [res.repo for res in (repository_results or [])]
            
            return MultiProviderResult(
                repositories=repositories,
                successful_providers=[provider_name],
                failed_providers=[],
                total_found=len(repositories),
                duplicates_removed=0
            )
            
        except Exception as e:
            logger.error(f"Provider '{provider_name}' resolution failed: {e}")
            return MultiProviderResult(
                repositories=[],
                successful_providers=[],
                failed_providers=[provider_name],
                total_found=0,
                duplicates_removed=0
            )
    
    async def _resolve_multiple_providers(
        self,
        pattern: str,
        limit: Optional[int] = None
    ) -> MultiProviderResult:
        """Resolve repositories from all configured providers concurrently."""
        providers = list_provider_names()
        
        if not providers:
            logger.warning("No providers configured")
            return MultiProviderResult(
                repositories=[],
                successful_providers=[],
                failed_providers=[],
                total_found=0,
                duplicates_removed=0
            )
        
        logger.debug(f"Resolving pattern '{pattern}' across {len(providers)} providers: {providers}")
        
        # Create semaphore to limit concurrent provider queries
        semaphore = asyncio.Semaphore(self.max_concurrent_providers)
        
        # Execute provider queries concurrently
        tasks = [
            self._resolve_provider_with_semaphore(semaphore, provider_name, pattern, limit)
            for provider_name in providers
        ]
        
        provider_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        all_repositories: List[RepositoryResult] = []
        successful_providers: List[str] = []
        failed_providers: List[str] = []
        
        for i, result in enumerate(provider_results):
            provider_name = providers[i]
            
            if isinstance(result, Exception):
                logger.debug(f"Provider '{provider_name}' failed: {result}")
                failed_providers.append(provider_name)
            elif isinstance(result, list):
                all_repositories.extend(result)
                if result:  # Only count as successful if repos found
                    successful_providers.append(provider_name)
                else:
                    logger.debug(f"Provider '{provider_name}' returned no results")
            else:
                logger.debug(f"Provider '{provider_name}' returned unexpected result type")
                failed_providers.append(provider_name)
        
        # Deduplicate repositories
        deduplicated_repos, duplicates_count = self._deduplicate_repositories(all_repositories)
        
        # Apply limit after deduplication
        if limit and len(deduplicated_repos) > limit:
            deduplicated_repos = deduplicated_repos[:limit]
        
        logger.info(
            f"Multi-provider resolution complete: {len(deduplicated_repos)} unique repos "
            f"from {len(successful_providers)} providers "
            f"({duplicates_count} duplicates removed)"
        )
        
        return MultiProviderResult(
            repositories=deduplicated_repos,
            successful_providers=successful_providers,
            failed_providers=failed_providers,
            total_found=len(all_repositories),
            duplicates_removed=duplicates_count
        )
    
    async def _resolve_provider_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        provider_name: str,
        pattern: str,
        limit: Optional[int]
    ) -> List[RepositoryResult]:
        """Resolve repositories from a single provider with concurrency control."""
        async with semaphore:
            try:
                repository_results = await list_repositories(
                    query=pattern,
                    provider_name=provider_name,
                    format_type="json",
                    limit=limit,
                )
                
                return [
                    RepositoryResult(repo=res.repo, provider_name=provider_name)
                    for res in (repository_results or [])
                ]
                
            except Exception as e:
                logger.debug(f"Provider '{provider_name}' query failed: {e}")
                raise
    
    def _deduplicate_repositories(
        self,
        repo_results: List[RepositoryResult]
    ) -> tuple[List[Repository], int]:
        """
        Deduplicate repositories based on clone URL.
        
        When the same repository exists in multiple providers, prefer:
        1. Provider with explicit priority (if configured)  
        2. First provider found (stable ordering)
        
        Returns:
            Tuple of (deduplicated_repositories, duplicates_removed_count)
        """
        seen_urls: Set[str] = set()
        seen_names: Dict[str, RepositoryResult] = {}  # name -> first occurrence
        deduplicated: List[Repository] = []
        duplicates_count = 0
        
        for repo_result in repo_results:
            repo = repo_result.repo
            
            # Primary deduplication by clone URL (exact matches)
            if repo.clone_url in seen_urls:
                logger.debug(f"Duplicate repository by URL: {repo.clone_url}")
                duplicates_count += 1
                continue
            
            # Secondary deduplication by repository name (same org/repo in different providers)
            repo_key = f"{repo.organization}/{repo.name}"
            if repo_key in seen_names:
                # Same repo name in different providers
                existing = seen_names[repo_key]
                logger.debug(
                    f"Duplicate repository '{repo_key}': "
                    f"keeping {existing.provider_name}, skipping {repo_result.provider_name}"
                )
                duplicates_count += 1
                continue
            
            # This is a unique repository
            seen_urls.add(repo.clone_url)
            seen_names[repo_key] = repo_result
            deduplicated.append(repo)
        
        return deduplicated, duplicates_count

# Convenience functions for backward compatibility
async def resolve_repositories_multi_provider(
    pattern: str,
    explicit_provider: Optional[str] = None,
    explicit_url: Optional[str] = None,
    limit: Optional[int] = None
) -> MultiProviderResult:
    """
    Convenience function for multi-provider repository resolution.
    
    This function provides a simple interface for the most common use case.
    """
    resolver = MultiProviderResolver()
    return await resolver.resolve_repositories(pattern, explicit_provider, explicit_url, limit)
```

#### 2. Update Clone-All Command (`mgit/__main__.py`)

Replace the complex repository resolution logic in the clone-all command (lines ~415-460):

```python
# Import new resolver
from mgit.utils.multi_provider_resolver import resolve_repositories_multi_provider

# In clone_all function:
async def resolve_repositories_for_clone(project: str, provider_manager, config: Optional[str], url: Optional[str]):
    """Helper to resolve repositories using the new multi-provider resolver."""
    
    # Use the new resolver
    result = await resolve_repositories_multi_provider(
        pattern=project,
        explicit_provider=provider_manager.provider_name if provider_manager else None,
        explicit_url=url,
        limit=None
    )
    
    # Handle the case where no multi-provider resolution occurred (non-pattern)
    if not result.repositories and provider_manager:
        # Fall back to direct provider manager call for non-patterns
        pattern_analysis = analyze_pattern(project, config, url)
        if not pattern_analysis.is_pattern:
            repositories = _ensure_repo_list(provider_manager.list_repositories(project))
            return repositories, ["default"], []
    
    # Log results
    if result.successful_providers:
        logger.info(
            f"Found {len(result.repositories)} repositories from "
            f"{len(result.successful_providers)} providers: {', '.join(result.successful_providers)}"
        )
    
    if result.failed_providers:
        logger.warning(
            f"Failed to query {len(result.failed_providers)} providers: "
            f"{', '.join(result.failed_providers)}"
        )
    
    if result.duplicates_removed > 0:
        logger.info(f"Removed {result.duplicates_removed} duplicate repositories")
    
    return result.repositories, result.successful_providers, result.failed_providers

# In the main clone_all function:
def clone_all(
    # ... parameters
):
    # ... existing setup ...
    
    # Use new resolution logic
    try:
        repositories, successful_providers, failed_providers = asyncio.run(
            resolve_repositories_for_clone(project, provider_manager, config, url)
        )
    except Exception as e:
        logger.error(f"Error resolving repositories: {e}")
        raise typer.Exit(code=1)
    
    if not repositories:
        if failed_providers and not successful_providers:
            logger.error("All provider queries failed")
        else:
            logger.info(f"No repositories found for pattern '{project}'")
        return
    
    # ... rest of function unchanged ...
```

#### 3. Update Pull-All Command

Apply similar changes to the pull-all command to use the same resolver logic.

## Testing Strategy

### Unit Tests
Create `tests/unit/test_multi_provider_resolver.py`:

```python
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from mgit.utils.multi_provider_resolver import (
    MultiProviderResolver,
    resolve_repositories_multi_provider,
    RepositoryResult
)
from mgit.providers.base import Repository

class TestMultiProviderResolver:
    @pytest.fixture
    def mock_repository(self):
        return Repository(
            name="test-repo",
            clone_url="https://github.com/org/test-repo.git",
            organization="org",
            project="project"
        )
    
    def test_single_provider_resolution(self, mock_repository):
        """Test resolution from a single explicit provider."""
        # Test implementation...
    
    def test_multi_provider_resolution(self, mock_repository):
        """Test concurrent resolution across multiple providers."""
        # Test implementation...
    
    def test_deduplication_by_url(self):
        """Test that repositories with same URL are deduplicated."""
        # Test implementation...
    
    def test_deduplication_by_name(self):
        """Test that repositories with same org/name are deduplicated."""
        # Test implementation...
    
    def test_provider_failure_handling(self):
        """Test that individual provider failures don't stop resolution.""" 
        # Test implementation...
    
    @pytest.mark.asyncio
    async def test_concurrent_provider_queries(self):
        """Test that providers are queried concurrently with proper limiting."""
        # Test implementation...
```

### Integration Tests
Add to `tests/integration/test_multi_provider.py`:

```python
def test_clone_all_uses_multi_provider_resolver():
    """Test that clone-all command uses the new resolver."""
    pass

def test_pull_all_uses_multi_provider_resolver():
    """Test that pull-all command uses the new resolver.""" 
    pass

def test_resolver_deduplication_end_to_end():
    """Test deduplication works in real scenarios."""
    pass
```

### Manual Verification
```bash
# Test multi-provider resolution with logging
poetry run mgit clone-all "*/*/*" /tmp/test-all-providers --verbose

# Test single provider resolution
poetry run mgit clone-all "org/*/*" /tmp/test-single --config github_work --verbose

# Test pattern that should find duplicates
poetry run mgit clone-all "myorg/*/*" /tmp/test-duplicates --verbose
```

## Success Criteria
- [ ] Multi-provider resolution logic extracted to dedicated module
- [ ] Clone-all command uses new resolver without behavioral changes
- [ ] Pull-all command uses new resolver without behavioral changes  
- [ ] Repository deduplication works correctly (by URL and name)
- [ ] Provider failure handling is robust (partial failures don't stop resolution)
- [ ] Concurrent provider querying maintains performance
- [ ] Logging provides useful information about resolution process
- [ ] Unit tests cover all resolver scenarios with >90% coverage
- [ ] Integration tests validate end-to-end resolution behavior

## Rollback Plan
If issues arise:
1. Revert changes to `mgit/__main__.py` clone-all and pull-all functions
2. Remove new `mgit/utils/multi_provider_resolver.py` file
3. Restore original inline resolution logic in both commands
4. Test that both commands work as before
5. Git repository returns to working state

## Notes
- This phase focuses on code consolidation without changing user-visible behavior
- The key improvement is that both clone-all and pull-all will have identical multi-provider logic
- Performance should be equivalent or better due to proper concurrent processing
- Deduplication logic handles the common case where same repo exists in multiple providers
- Error handling is more robust - individual provider failures don't stop the entire operation
- Logging improvements provide better visibility into what providers are being queried
- The resolver is designed to be reusable for the upcoming sync command
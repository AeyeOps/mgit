# Git Provider Interface Documentation

## Overview

The mgit provider system allows support for multiple git hosting platforms through a common interface. All providers must implement the `GitProvider` abstract base class defined in `base.py`.

## Interface Components

### Core Data Classes

1. **Repository**: Represents a git repository
   - `name`: Repository name
   - `clone_url`: HTTPS clone URL
   - `ssh_url`: SSH clone URL (optional)
   - `is_disabled`: Whether the repo is disabled/archived
   - `is_private`: Repository visibility
   - `default_branch`: Default branch name
   - `size`: Size in KB (optional)
   - `metadata`: Provider-specific data

2. **Organization**: Top-level grouping (GitHub org, Azure DevOps org, etc.)
   - `name`: Organization identifier
   - `url`: Web URL
   - `provider`: Provider name
   - `metadata`: Provider-specific data

3. **Project**: Optional intermediate grouping (not all providers support this)
   - `name`: Project name
   - `organization`: Parent organization
   - `description`: Project description
   - `metadata`: Provider-specific data

### Required Methods

Every provider must implement these abstract methods:

1. **`_validate_config()`**: Validate provider configuration
2. **`authenticate()`**: Establish authentication with the provider
3. **`test_connection()`**: Verify connectivity and authentication
4. **`list_organizations()`**: List accessible organizations
5. **`list_projects(organization)`**: List projects (can return empty list)
6. **`list_repositories(organization, project, filters)`**: List/filter repositories
7. **`get_repository(organization, repository, project)`**: Get specific repository
8. **`get_authenticated_clone_url(repository)`**: Get clone URL with auth

### Optional Methods

Providers can override these methods for custom behavior:

- **`supports_projects()`**: Whether provider has project hierarchy (default: True)
- **`get_rate_limit_info()`**: Current API rate limit status
- **`get_provider_info()`**: Provider capabilities and configuration
- **`validate_repository_access()`**: Check user permissions
- **`normalize_repository_name()`**: Apply naming rules
- **`count_repositories()`**: Efficient repository counting
- **`close()`**: Cleanup resources

## Implementation Guide

### 1. Create Provider Class

```python
from typing import List, Optional, Dict, Any, AsyncIterator
from mgit.providers.base import GitProvider, Repository, Organization, Project, AuthMethod
from mgit.providers.exceptions import *

class MyProvider(GitProvider):
    PROVIDER_NAME = "myprovider"
    SUPPORTED_AUTH_METHODS = [AuthMethod.PAT, AuthMethod.OAUTH]
    DEFAULT_API_VERSION = "v1"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Initialize provider-specific attributes
```

### 2. Implement Configuration Validation

```python
def _validate_config(self) -> None:
    """Validate required configuration."""
    if 'pat' not in self.config and 'oauth_token' not in self.config:
        raise ConfigurationError("Authentication token required")
    
    # Validate other required fields
    if 'base_url' in self.config:
        # Validate URL format
        pass
```

### 3. Implement Authentication

```python
async def authenticate(self) -> bool:
    """Authenticate with the provider."""
    try:
        # Create API client
        self._client = MyProviderClient(
            base_url=self.config.get('base_url', 'https://api.myprovider.com'),
            token=self.config.get('pat')
        )
        
        # Test authentication
        await self._client.get_current_user()
        self._authenticated = True
        return True
        
    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {e}")
```

### 4. Implement Repository Listing

```python
async def list_repositories(
    self,
    organization: str,
    project: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None
) -> AsyncIterator[Repository]:
    """List repositories with pagination."""
    page = 1
    per_page = 100
    
    while True:
        # Fetch page of repositories
        response = await self._client.get_repositories(
            org=organization,
            project=project,
            page=page,
            per_page=per_page
        )
        
        # Convert to Repository objects
        for repo_data in response['repositories']:
            repo = Repository(
                name=repo_data['name'],
                clone_url=repo_data['clone_url'],
                ssh_url=repo_data.get('ssh_url'),
                is_private=repo_data.get('private', True),
                # ... other fields
            )
            
            # Apply filters if provided
            if self._matches_filters(repo, filters):
                yield repo
        
        # Check for more pages
        if len(response['repositories']) < per_page:
            break
        page += 1
```

### 5. Handle Errors Appropriately

```python
from mgit.providers.exceptions import (
    AuthenticationError,
    RateLimitError,
    RepositoryNotFoundError,
    APIError
)

async def get_repository(self, organization: str, repository: str, project: Optional[str] = None) -> Optional[Repository]:
    """Get a specific repository."""
    try:
        repo_data = await self._client.get_repository(organization, repository)
        return Repository(...)
        
    except NotFoundException:
        raise RepositoryNotFoundError(f"Repository {repository} not found")
    except RateLimitException:
        raise RateLimitError("API rate limit exceeded")
    except Exception as e:
        raise APIError(f"Failed to fetch repository: {e}")
```

## Best Practices

1. **Use Async/Await**: All API operations should be asynchronous
2. **Handle Pagination**: Use AsyncIterator for efficient memory usage with large result sets
3. **Proper Error Handling**: Convert provider-specific exceptions to common exception types
4. **Type Hints**: Use complete type annotations for all methods
5. **Documentation**: Provide comprehensive docstrings
6. **Rate Limiting**: Respect and handle API rate limits
7. **Authentication**: Securely handle and never log credentials
8. **Testing**: Create unit tests for all provider methods

## Adding a New Provider

1. Create `mgit/providers/myprovider.py`
2. Implement the `MyProvider` class following the interface
3. Register in `mgit/providers/registry.py`:
   ```python
   register_provider('myprovider', 'mgit.providers.myprovider:MyProvider')
   ```
4. Add provider-specific exceptions if needed
5. Create comprehensive tests in `tests/unit/test_providers.py`
6. Update documentation

## Testing Your Provider

```python
import asyncio
from mgit.providers.factory import ProviderFactory

async def test_provider():
    # Create provider instance
    provider = ProviderFactory.create('myprovider', {
        'pat': 'your-token',
        'base_url': 'https://api.myprovider.com'
    })
    
    # Test authentication
    assert await provider.authenticate()
    
    # Test listing organizations
    orgs = await provider.list_organizations()
    assert len(orgs) > 0
    
    # Test listing repositories
    repos = []
    async for repo in provider.list_repositories(orgs[0].name):
        repos.append(repo)
    assert len(repos) > 0
    
    # Cleanup
    await provider.close()

# Run the test
asyncio.run(test_provider())
```
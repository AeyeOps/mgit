# Multi-Provider Design for mgit

## Executive Summary

This document outlines the design for expanding mgit to support multiple Git providers (Azure DevOps, GitHub, and BitBucket Cloud) while maintaining backward compatibility and a consistent user experience.

## Provider Hierarchy Comparison

### Azure DevOps
- **Organization** (e.g., `https://dev.azure.com/myorg`)
- **Project** (e.g., `MyProject`)
- **Repository** (e.g., `my-repo`)
- Full path: `https://dev.azure.com/myorg/MyProject/_git/my-repo`

### GitHub
- **Organization/User** (e.g., `octocat` or `github`)
- **Repository** (projects don't exist as a separate level)
- Full path: `https://github.com/octocat/my-repo`
- Note: GitHub uses "Organizations" for group accounts and repository grouping is done via naming conventions or GitHub Projects (which are different from Azure DevOps projects)

### BitBucket Cloud
- **Workspace** (formerly "Team", e.g., `myworkspace`)
- **Project** (optional grouping, e.g., `PROJ`)
- **Repository** (e.g., `my-repo`)
- Full path: `https://bitbucket.org/myworkspace/my-repo`
- Note: Projects in BitBucket are optional and used for grouping repositories

## Proposed Architecture

### 1. Provider Abstraction Layer

Create a base abstract class that defines the interface for all providers:

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class Repository:
    """Provider-agnostic repository representation"""
    name: str
    clone_url: str
    ssh_url: Optional[str]
    is_disabled: bool = False
    default_branch: str = "main"
    provider: str = ""
    metadata: Dict[str, Any] = None

class GitProvider(ABC):
    """Abstract base class for git providers"""
    
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.auth_token = auth_token
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the authentication is valid"""
        pass
    
    @abstractmethod
    async def list_projects(self, organization: str) -> List[str]:
        """List all projects/groupings in an organization"""
        pass
    
    @abstractmethod
    async def list_repositories(self, organization: str, project: Optional[str] = None) -> List[Repository]:
        """List all repositories in a project or organization"""
        pass
    
    @abstractmethod
    def get_authenticated_clone_url(self, repo: Repository) -> str:
        """Get clone URL with embedded authentication"""
        pass
```

### 2. Provider Implementations

#### Azure DevOps Provider
```python
class AzureDevOpsProvider(GitProvider):
    """Azure DevOps implementation"""
    
    def __init__(self, organization_url: str, pat: str):
        super().__init__(organization_url, pat)
        # Initialize Azure DevOps SDK clients
        
    async def list_projects(self, organization: str) -> List[str]:
        # Use existing SDK logic to list projects
        
    async def list_repositories(self, organization: str, project: Optional[str] = None) -> List[Repository]:
        # Use existing SDK logic, convert to Repository objects
```

#### GitHub Provider
```python
class GitHubProvider(GitProvider):
    """GitHub implementation"""
    
    def __init__(self, token: str):
        super().__init__("https://api.github.com", token)
        # Initialize GitHub client (PyGithub or httpx)
        
    async def list_projects(self, organization: str) -> List[str]:
        # GitHub doesn't have projects in the same way
        # Could return repository prefixes or GitHub Projects
        return []
        
    async def list_repositories(self, organization: str, project: Optional[str] = None) -> List[Repository]:
        # List org repos, optionally filter by prefix if "project" is provided
```

#### BitBucket Provider
```python
class BitBucketProvider(GitProvider):
    """BitBucket Cloud implementation"""
    
    def __init__(self, username: str, app_password: str):
        super().__init__("https://api.bitbucket.org/2.0", app_password)
        self.username = username
        
    async def list_projects(self, workspace: str) -> List[str]:
        # List BitBucket projects in workspace
        
    async def list_repositories(self, workspace: str, project: Optional[str] = None) -> List[Repository]:
        # List repos, optionally filtered by project
```

### 3. Provider Factory

```python
class ProviderFactory:
    """Factory to create appropriate provider instances"""
    
    @staticmethod
    def create_provider(provider_type: str, **kwargs) -> GitProvider:
        if provider_type.lower() == "azuredevops":
            return AzureDevOpsProvider(
                organization_url=kwargs.get("organization_url"),
                pat=kwargs.get("pat")
            )
        elif provider_type.lower() == "github":
            return GitHubProvider(token=kwargs.get("token"))
        elif provider_type.lower() == "bitbucket":
            return BitBucketProvider(
                username=kwargs.get("username"),
                app_password=kwargs.get("app_password")
            )
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
```

### 4. Updated CLI Commands

The CLI commands would be updated to accept a provider parameter:

```python
@app.command()
def clone_all(
    organization: str = typer.Argument(..., help="Organization/Workspace name"),
    project: Optional[str] = typer.Argument(None, help="Project name (optional for GitHub)"),
    rel_path: str = typer.Argument(..., help="Relative path to clone into"),
    provider: str = typer.Option("azuredevops", "--provider", "-p", help="Git provider (azuredevops, github, bitbucket)"),
    # ... other existing options
):
    """Clone all repositories from a git provider"""
    
    # Get provider-specific configuration
    provider_config = get_provider_config(provider)
    
    # Create provider instance
    git_provider = ProviderFactory.create_provider(provider, **provider_config)
    
    # Use abstracted methods
    if not await git_provider.test_connection():
        logger.error(f"Failed to connect to {provider}")
        raise typer.Exit(1)
    
    repos = await git_provider.list_repositories(organization, project)
    # ... rest of the logic remains similar
```

### 5. Configuration Management

Update configuration to support multiple providers:

```ini
# ~/.config/mgit/config

[default]
provider = azuredevops
concurrency = 4
update_mode = skip

[azuredevops]
organization_url = https://dev.azure.com/myorg
pat = <pat-token>

[github]
token = <github-token>

[bitbucket]
username = myusername
app_password = <app-password>
```

### 6. Environment Variables

Support provider-specific environment variables:

```bash
# Azure DevOps (backward compatible)
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/myorg
AZURE_DEVOPS_EXT_PAT=<pat>

# GitHub
GITHUB_TOKEN=<token>

# BitBucket
BITBUCKET_USERNAME=<username>
BITBUCKET_APP_PASSWORD=<password>

# Default provider
MGIT_DEFAULT_PROVIDER=github
```

## Migration Strategy

1. **Phase 1**: Refactor existing code to use abstraction layer
   - Extract AzureDevOps-specific code into AzureDevOpsProvider
   - Maintain backward compatibility with existing commands

2. **Phase 2**: Implement GitHub provider
   - Add GitHub API integration
   - Handle the flat organization/repo structure

3. **Phase 3**: Implement BitBucket provider
   - Add BitBucket API integration
   - Handle workspace/project/repo hierarchy

4. **Phase 4**: Enhanced features
   - Cross-provider operations (e.g., migrate repos between providers)
   - Provider-specific features (e.g., GitHub Actions, BitBucket Pipelines)

## Backward Compatibility

To ensure existing users aren't affected:

1. Default provider remains Azure DevOps if not specified
2. Existing environment variables continue to work
3. Commands without `--provider` flag assume Azure DevOps
4. Configuration file format is extended, not replaced

## Implementation Considerations

### Authentication Methods
- **Azure DevOps**: Personal Access Token (PAT)
- **GitHub**: Personal Access Token or GitHub App token
- **BitBucket**: App passwords or OAuth

### API Rate Limits
- Implement rate limiting awareness
- Add retry logic with exponential backoff
- Consider pagination for large organizations

### Dependencies
- **Azure DevOps**: Keep existing `azure-devops` SDK
- **GitHub**: Add `PyGithub` or use `httpx` for REST API
- **BitBucket**: Use `atlassian-python-api` or `httpx`

### Error Handling
- Provider-specific error messages
- Graceful fallbacks for missing features
- Clear user guidance for provider-specific setup

## Common Operations Across Providers

All providers support:
1. Listing repositories
2. Cloning repositories with authentication
3. Repository metadata (name, disabled status, default branch)

Provider-specific features can be exposed through metadata or provider-specific commands.

## Example Usage

```bash
# Azure DevOps (default)
mgit clone-all MyProject ./repos

# GitHub
mgit clone-all octocat ./repos --provider github

# BitBucket with project
mgit clone-all myworkspace PROJ ./repos --provider bitbucket

# Pull all with specific provider
mgit pull-all --provider github ./repos

# Configure default provider
mgit config --provider github
```

## Testing Strategy

1. Unit tests for each provider implementation
2. Integration tests with mock APIs
3. End-to-end tests with real providers (in CI with secrets)
4. Provider compatibility matrix testing

## Security Considerations

1. Secure credential storage per provider
2. Token permission validation
3. Audit logging for operations
4. Credential rotation reminders

## Future Extensions

1. GitLab support
2. Self-hosted instances (GitHub Enterprise, BitBucket Server)
3. Repository filtering by attributes (language, size, activity)
4. Bulk operations (archive, transfer, settings)
5. Provider migration tools
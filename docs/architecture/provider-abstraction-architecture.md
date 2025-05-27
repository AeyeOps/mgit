# Provider Abstraction Architecture

## Overview

This document details the object-oriented architecture for implementing multi-provider support in mgit using an abstract base class and concrete provider implementations.

## Class Hierarchy

```
GitProvider (ABC)
├── AzureDevOpsProvider
├── GitHubProvider
└── BitBucketProvider
```

## Abstract Base Class Design

### Core GitProvider Abstract Class

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, AsyncIterator
from enum import Enum
import asyncio

# Common data structures
@dataclass
class Repository:
    """Provider-agnostic repository representation"""
    name: str
    clone_url: str
    ssh_url: Optional[str] = None
    is_disabled: bool = False
    is_private: bool = True
    default_branch: str = "main"
    size: Optional[int] = None  # Size in KB
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    provider: str = ""
    metadata: Dict[str, Any] = None  # Provider-specific data

@dataclass
class Organization:
    """Provider-agnostic organization/workspace representation"""
    name: str
    url: str
    provider: str
    metadata: Dict[str, Any] = None

@dataclass
class Project:
    """Project/grouping representation (may be None for GitHub)"""
    name: str
    organization: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = None

class AuthMethod(Enum):
    """Supported authentication methods"""
    PAT = "personal_access_token"
    OAUTH = "oauth"
    APP_PASSWORD = "app_password"
    SSH_KEY = "ssh_key"

class GitProvider(ABC):
    """Abstract base class for all git providers"""
    
    # Class attributes to be overridden
    PROVIDER_NAME: str = ""
    SUPPORTED_AUTH_METHODS: List[AuthMethod] = []
    DEFAULT_API_VERSION: str = ""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider with configuration
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self._validate_config()
        self._client = None
        self._authenticated = False
        
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider-specific configuration"""
        pass
        
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the provider
        
        Returns:
            bool: True if authentication successful
        """
        pass
        
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if the connection and authentication are valid
        
        Returns:
            bool: True if connection is valid
        """
        pass
        
    @abstractmethod
    async def list_organizations(self) -> List[Organization]:
        """
        List all accessible organizations/workspaces
        
        Returns:
            List of Organization objects
        """
        pass
        
    @abstractmethod
    async def list_projects(self, organization: str) -> List[Project]:
        """
        List all projects in an organization
        Note: May return empty list for providers without project concept
        
        Args:
            organization: Organization/workspace name
            
        Returns:
            List of Project objects
        """
        pass
        
    @abstractmethod
    async def list_repositories(
        self, 
        organization: str, 
        project: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Repository]:
        """
        List repositories with optional filtering
        
        Args:
            organization: Organization/workspace name
            project: Optional project name
            filters: Optional filters (language, archived, etc.)
            
        Yields:
            Repository objects
        """
        pass
        
    @abstractmethod
    async def get_repository(
        self, 
        organization: str, 
        repository: str,
        project: Optional[str] = None
    ) -> Optional[Repository]:
        """
        Get a specific repository
        
        Args:
            organization: Organization/workspace name
            repository: Repository name
            project: Optional project name
            
        Returns:
            Repository object or None if not found
        """
        pass
        
    @abstractmethod
    def get_authenticated_clone_url(self, repository: Repository) -> str:
        """
        Get clone URL with embedded authentication
        
        Args:
            repository: Repository object
            
        Returns:
            Authenticated clone URL
        """
        pass
        
    # Common utility methods (not abstract)
    async def count_repositories(
        self, 
        organization: str, 
        project: Optional[str] = None
    ) -> int:
        """Count total repositories"""
        count = 0
        async for _ in self.list_repositories(organization, project):
            count += 1
        return count
        
    def supports_projects(self) -> bool:
        """Check if provider supports project hierarchy"""
        return True  # Override in providers that don't
        
    def get_rate_limit_info(self) -> Optional[Dict[str, Any]]:
        """Get current rate limit information if available"""
        return None  # Override in providers with rate limits
        
    async def close(self) -> None:
        """Cleanup resources"""
        if self._client:
            # Close client connections if needed
            pass
```

## Concrete Provider Implementations

### AzureDevOpsProvider

```python
class AzureDevOpsProvider(GitProvider):
    """Azure DevOps implementation"""
    
    PROVIDER_NAME = "azuredevops"
    SUPPORTED_AUTH_METHODS = [AuthMethod.PAT]
    DEFAULT_API_VERSION = "7.0"
    
    def _validate_config(self) -> None:
        """Validate Azure DevOps configuration"""
        required = ["url", "pat"]
        for field in required:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")
                
        # Validate URL format
        url = self.config["url"]
        if not url.startswith(("https://", "http://")):
            self.config["url"] = f"https://{url}"
            
    async def authenticate(self) -> bool:
        """Authenticate using PAT"""
        from azure.devops.connection import Connection
        from msrest.authentication import BasicAuthentication
        
        try:
            credentials = BasicAuthentication('', self.config["pat"])
            self._client = Connection(
                base_url=self.config["url"], 
                creds=credentials
            )
            self._core_client = self._client.clients.get_core_client()
            self._git_client = self._client.clients.get_git_client()
            self._authenticated = True
            return True
        except Exception as e:
            self._authenticated = False
            return False
            
    async def test_connection(self) -> bool:
        """Test Azure DevOps connection"""
        if not self._authenticated:
            return False
            
        try:
            # Try to get projects to verify connection
            self._core_client.get_projects()
            return True
        except Exception:
            return False
            
    async def list_organizations(self) -> List[Organization]:
        """List organizations (single org for Azure DevOps)"""
        # Azure DevOps typically works with a single org at a time
        return [Organization(
            name=self._extract_org_name(self.config["url"]),
            url=self.config["url"],
            provider=self.PROVIDER_NAME
        )]
        
    async def list_projects(self, organization: str) -> List[Project]:
        """List all projects in the organization"""
        projects = []
        
        try:
            project_refs = self._core_client.get_projects()
            for proj in project_refs:
                projects.append(Project(
                    name=proj.name,
                    organization=organization,
                    description=proj.description,
                    metadata={"id": proj.id, "state": proj.state}
                ))
        except Exception as e:
            # Log error
            pass
            
        return projects
        
    async def list_repositories(
        self, 
        organization: str, 
        project: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Repository]:
        """List repositories in a project"""
        if not project:
            # Azure DevOps requires a project
            raise ValueError("Project is required for Azure DevOps")
            
        try:
            repos = self._git_client.get_repositories(project=project)
            
            for repo in repos:
                # Apply filters if provided
                if filters:
                    if filters.get("include_disabled", True) is False and repo.is_disabled:
                        continue
                        
                yield Repository(
                    name=repo.name,
                    clone_url=repo.remote_url,
                    ssh_url=repo.ssh_url,
                    is_disabled=repo.is_disabled,
                    is_private=True,  # Azure DevOps repos are private by default
                    default_branch=repo.default_branch or "main",
                    size=repo.size,
                    provider=self.PROVIDER_NAME,
                    metadata={
                        "id": repo.id,
                        "project": repo.project.name if repo.project else None
                    }
                )
        except Exception as e:
            # Log error
            pass
            
    async def get_repository(
        self, 
        organization: str, 
        repository: str,
        project: Optional[str] = None
    ) -> Optional[Repository]:
        """Get a specific repository"""
        if not project:
            raise ValueError("Project is required for Azure DevOps")
            
        try:
            repo = self._git_client.get_repository(
                repository_id=repository,
                project=project
            )
            
            return Repository(
                name=repo.name,
                clone_url=repo.remote_url,
                ssh_url=repo.ssh_url,
                is_disabled=repo.is_disabled,
                is_private=True,
                default_branch=repo.default_branch or "main",
                size=repo.size,
                provider=self.PROVIDER_NAME
            )
        except Exception:
            return None
            
    def get_authenticated_clone_url(self, repository: Repository) -> str:
        """Get Azure DevOps authenticated URL"""
        from urllib.parse import urlparse, urlunparse
        
        parsed = urlparse(repository.clone_url)
        # Azure DevOps format: https://pat@dev.azure.com/...
        netloc = f"{self.config['pat']}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
            
        return urlunparse(parsed._replace(netloc=netloc))
        
    def _extract_org_name(self, url: str) -> str:
        """Extract organization name from URL"""
        # https://dev.azure.com/myorg -> myorg
        from urllib.parse import urlparse
        parsed = urlparse(url)
        parts = parsed.path.strip('/').split('/')
        return parts[0] if parts else "default"
```

### GitHubProvider

```python
class GitHubProvider(GitProvider):
    """GitHub implementation"""
    
    PROVIDER_NAME = "github"
    SUPPORTED_AUTH_METHODS = [AuthMethod.PAT, AuthMethod.OAUTH]
    DEFAULT_API_VERSION = "v3"
    
    def _validate_config(self) -> None:
        """Validate GitHub configuration"""
        if "token" not in self.config and "oauth_token" not in self.config:
            raise ValueError("Either 'token' or 'oauth_token' required")
            
        # Set default API URL if not provided
        if "api_url" not in self.config:
            self.config["api_url"] = "https://api.github.com"
            
    async def authenticate(self) -> bool:
        """Authenticate with GitHub"""
        try:
            from github import Github
            
            token = self.config.get("token") or self.config.get("oauth_token")
            base_url = self.config.get("api_url", "https://api.github.com")
            
            self._client = Github(auth=token, base_url=base_url)
            self._authenticated = True
            return True
        except Exception:
            self._authenticated = False
            return False
            
    async def test_connection(self) -> bool:
        """Test GitHub connection"""
        if not self._authenticated:
            return False
            
        try:
            # Try to get authenticated user
            self._client.get_user()
            return True
        except Exception:
            return False
            
    def supports_projects(self) -> bool:
        """GitHub doesn't have traditional projects"""
        return False
        
    async def list_organizations(self) -> List[Organization]:
        """List accessible organizations"""
        orgs = []
        
        try:
            user = self._client.get_user()
            
            # Add user's personal account as an "organization"
            orgs.append(Organization(
                name=user.login,
                url=user.html_url,
                provider=self.PROVIDER_NAME,
                metadata={"type": "user"}
            ))
            
            # Add actual organizations
            for org in user.get_orgs():
                orgs.append(Organization(
                    name=org.login,
                    url=org.html_url,
                    provider=self.PROVIDER_NAME,
                    metadata={"type": "organization"}
                ))
        except Exception:
            pass
            
        return orgs
        
    async def list_projects(self, organization: str) -> List[Project]:
        """GitHub doesn't have projects in the same sense"""
        return []
        
    async def list_repositories(
        self, 
        organization: str, 
        project: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Repository]:
        """List GitHub repositories"""
        try:
            # Get org or user
            try:
                entity = self._client.get_organization(organization)
            except:
                entity = self._client.get_user(organization)
                
            repos = entity.get_repos()
            
            # Apply filters
            if filters:
                if "language" in filters:
                    repos = [r for r in repos if r.language == filters["language"]]
                if "archived" in filters:
                    repos = [r for r in repos if r.archived == filters["archived"]]
                if "topics" in filters:
                    topic_set = set(filters["topics"])
                    repos = [r for r in repos if topic_set.intersection(r.topics)]
                    
            for repo in repos:
                yield Repository(
                    name=repo.name,
                    clone_url=repo.clone_url,
                    ssh_url=repo.ssh_url,
                    is_disabled=repo.archived,
                    is_private=repo.private,
                    default_branch=repo.default_branch,
                    size=repo.size,
                    description=repo.description,
                    created_at=repo.created_at.isoformat() if repo.created_at else None,
                    updated_at=repo.updated_at.isoformat() if repo.updated_at else None,
                    provider=self.PROVIDER_NAME,
                    metadata={
                        "language": repo.language,
                        "topics": repo.topics,
                        "stars": repo.stargazers_count,
                        "forks": repo.forks_count
                    }
                )
        except Exception:
            pass
            
    async def get_repository(
        self, 
        organization: str, 
        repository: str,
        project: Optional[str] = None
    ) -> Optional[Repository]:
        """Get a specific GitHub repository"""
        try:
            repo = self._client.get_repo(f"{organization}/{repository}")
            
            return Repository(
                name=repo.name,
                clone_url=repo.clone_url,
                ssh_url=repo.ssh_url,
                is_disabled=repo.archived,
                is_private=repo.private,
                default_branch=repo.default_branch,
                size=repo.size,
                description=repo.description,
                provider=self.PROVIDER_NAME
            )
        except Exception:
            return None
            
    def get_authenticated_clone_url(self, repository: Repository) -> str:
        """Get GitHub authenticated URL"""
        from urllib.parse import urlparse, urlunparse
        
        token = self.config.get("token") or self.config.get("oauth_token")
        parsed = urlparse(repository.clone_url)
        
        # GitHub format: https://token@github.com/...
        netloc = f"{token}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
            
        return urlunparse(parsed._replace(netloc=netloc))
        
    def get_rate_limit_info(self) -> Optional[Dict[str, Any]]:
        """Get GitHub rate limit information"""
        try:
            rate_limit = self._client.get_rate_limit()
            return {
                "limit": rate_limit.core.limit,
                "remaining": rate_limit.core.remaining,
                "reset": rate_limit.core.reset.isoformat()
            }
        except Exception:
            return None
```

### BitBucketProvider

```python
class BitBucketProvider(GitProvider):
    """BitBucket Cloud implementation"""
    
    PROVIDER_NAME = "bitbucket"
    SUPPORTED_AUTH_METHODS = [AuthMethod.APP_PASSWORD, AuthMethod.OAUTH]
    DEFAULT_API_VERSION = "2.0"
    
    def _validate_config(self) -> None:
        """Validate BitBucket configuration"""
        required = ["username", "app_password"]
        for field in required:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")
                
        # Set default API URL
        if "api_url" not in self.config:
            self.config["api_url"] = "https://api.bitbucket.org/2.0"
            
    async def authenticate(self) -> bool:
        """Authenticate with BitBucket"""
        try:
            from atlassian import Bitbucket
            
            self._client = Bitbucket(
                url=self.config.get("api_url", "https://api.bitbucket.org"),
                username=self.config["username"],
                password=self.config["app_password"],
                cloud=True
            )
            self._authenticated = True
            return True
        except Exception:
            self._authenticated = False
            return False
            
    async def test_connection(self) -> bool:
        """Test BitBucket connection"""
        if not self._authenticated:
            return False
            
        try:
            # Try to get user info
            self._client.get_user()
            return True
        except Exception:
            return False
            
    async def list_organizations(self) -> List[Organization]:
        """List accessible workspaces"""
        orgs = []
        
        try:
            # Get workspaces user has access to
            workspaces = self._client.workspaces.each()
            
            for ws in workspaces:
                orgs.append(Organization(
                    name=ws["slug"],
                    url=ws["links"]["html"]["href"],
                    provider=self.PROVIDER_NAME,
                    metadata={"uuid": ws["uuid"]}
                ))
        except Exception:
            pass
            
        return orgs
        
    async def list_projects(self, organization: str) -> List[Project]:
        """List projects in a workspace"""
        projects = []
        
        try:
            # BitBucket projects API
            workspace_projects = self._client.workspaces.get(organization).projects.each()
            
            for proj in workspace_projects:
                projects.append(Project(
                    name=proj["key"],
                    organization=organization,
                    description=proj.get("description"),
                    metadata={
                        "uuid": proj["uuid"],
                        "is_private": proj.get("is_private", True)
                    }
                ))
        except Exception:
            pass
            
        return projects
        
    async def list_repositories(
        self, 
        organization: str, 
        project: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Repository]:
        """List BitBucket repositories"""
        try:
            # Get repositories
            if project:
                # Filter by project
                repos = self._client.workspaces.get(organization).repositories.each(
                    q=f'project.key="{project}"'
                )
            else:
                repos = self._client.workspaces.get(organization).repositories.each()
                
            for repo in repos:
                # Apply filters
                if filters:
                    if "language" in filters and repo.get("language") != filters["language"]:
                        continue
                        
                yield Repository(
                    name=repo["slug"],
                    clone_url=repo["links"]["clone"][0]["href"],  # HTTPS
                    ssh_url=repo["links"]["clone"][1]["href"] if len(repo["links"]["clone"]) > 1 else None,
                    is_disabled=False,  # BitBucket doesn't have disabled state
                    is_private=repo.get("is_private", True),
                    default_branch=repo.get("mainbranch", {}).get("name", "main"),
                    size=repo.get("size"),
                    description=repo.get("description"),
                    created_at=repo.get("created_on"),
                    updated_at=repo.get("updated_on"),
                    provider=self.PROVIDER_NAME,
                    metadata={
                        "uuid": repo["uuid"],
                        "language": repo.get("language"),
                        "project": repo.get("project", {}).get("key") if repo.get("project") else None
                    }
                )
        except Exception:
            pass
            
    async def get_repository(
        self, 
        organization: str, 
        repository: str,
        project: Optional[str] = None
    ) -> Optional[Repository]:
        """Get a specific BitBucket repository"""
        try:
            repo = self._client.workspaces.get(organization).repositories.get(repository)
            
            return Repository(
                name=repo["slug"],
                clone_url=repo["links"]["clone"][0]["href"],
                ssh_url=repo["links"]["clone"][1]["href"] if len(repo["links"]["clone"]) > 1 else None,
                is_disabled=False,
                is_private=repo.get("is_private", True),
                default_branch=repo.get("mainbranch", {}).get("name", "main"),
                size=repo.get("size"),
                description=repo.get("description"),
                provider=self.PROVIDER_NAME
            )
        except Exception:
            return None
            
    def get_authenticated_clone_url(self, repository: Repository) -> str:
        """Get BitBucket authenticated URL"""
        from urllib.parse import urlparse, urlunparse
        
        parsed = urlparse(repository.clone_url)
        
        # BitBucket format: https://username:app-password@bitbucket.org/...
        netloc = f"{self.config['username']}:{self.config['app_password']}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
            
        return urlunparse(parsed._replace(netloc=netloc))
```

## Provider Factory Pattern

```python
class ProviderFactory:
    """Factory for creating provider instances"""
    
    _providers = {
        "azuredevops": AzureDevOpsProvider,
        "github": GitHubProvider,
        "bitbucket": BitBucketProvider
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """Register a new provider type"""
        cls._providers[name.lower()] = provider_class
        
    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> GitProvider:
        """
        Create a provider instance
        
        Args:
            provider_type: Type of provider (azuredevops, github, bitbucket)
            config: Provider-specific configuration
            
        Returns:
            GitProvider instance
            
        Raises:
            ValueError: If provider type is unknown
        """
        provider_class = cls._providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(
                f"Unknown provider type: {provider_type}. "
                f"Available: {', '.join(cls._providers.keys())}"
            )
            
        return provider_class(config)
        
    @classmethod
    def list_providers(cls) -> List[str]:
        """List available provider types"""
        return list(cls._providers.keys())
```

## Usage Example

```python
async def main():
    # Load configuration
    config = load_yaml_config()
    
    # Create provider instance
    provider_type = config["settings"]["default_provider"]
    provider_config = config["providers"][provider_type]["organizations"]["default"]
    
    provider = ProviderFactory.create_provider(provider_type, provider_config)
    
    # Authenticate
    if not await provider.authenticate():
        print("Authentication failed")
        return
        
    # List repositories
    org = provider_config.get("organization", "default")
    project = provider_config.get("default_project")
    
    async for repo in provider.list_repositories(org, project):
        print(f"Found repository: {repo.name}")
        clone_url = provider.get_authenticated_clone_url(repo)
        # Clone repository...
        
    # Cleanup
    await provider.close()
```

## Extension Points

### Adding a New Provider

To add a new provider (e.g., GitLab):

1. Create a new class inheriting from `GitProvider`
2. Implement all abstract methods
3. Register with the factory

```python
class GitLabProvider(GitProvider):
    PROVIDER_NAME = "gitlab"
    # ... implementation ...

# Register the provider
ProviderFactory.register_provider("gitlab", GitLabProvider)
```

### Provider-Specific Features

Providers can add extra methods for unique features:

```python
class GitHubProvider(GitProvider):
    # ... base implementation ...
    
    async def get_actions_runs(self, organization: str, repository: str):
        """GitHub-specific: Get GitHub Actions runs"""
        # Implementation for GitHub Actions
        
    async def get_repository_topics(self, organization: str, repository: str) -> List[str]:
        """GitHub-specific: Get repository topics"""
        # Implementation for topics
```

## Error Handling

```python
class ProviderError(Exception):
    """Base exception for provider errors"""
    pass

class AuthenticationError(ProviderError):
    """Authentication failed"""
    pass

class RateLimitError(ProviderError):
    """Rate limit exceeded"""
    def __init__(self, message: str, reset_time: Optional[datetime] = None):
        super().__init__(message)
        self.reset_time = reset_time

class ProviderNotFoundError(ProviderError):
    """Provider type not found"""
    pass
```

## Testing Strategy

### Unit Tests
- Mock provider APIs
- Test each provider implementation
- Test factory pattern

### Integration Tests
- Test against real APIs (with test accounts)
- Test rate limit handling
- Test pagination

### Provider Compatibility Tests
- Ensure consistent behavior across providers
- Test common operations
- Verify data structure compatibility
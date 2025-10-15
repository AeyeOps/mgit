"""Azure DevOps provider implementation for mgit.

This module implements the Azure DevOps provider that extends the abstract
GitProvider base class to support Azure DevOps repositories.
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional
from urllib.parse import urlparse

from azure.devops.connection import Connection
from azure.devops.exceptions import AzureDevOpsAuthenticationError, ClientRequestError
from azure.devops.v7_1.core import CoreClient, TeamProjectReference
from azure.devops.v7_1.git import GitClient, GitRepository
from msrest.authentication import BasicAuthentication

from mgit.git.utils import embed_pat_in_url
from mgit.providers.base import (
    AuthMethod,
    GitProvider,
    Organization,
    Project,
    Repository,
)

logger = logging.getLogger(__name__)


class AzureDevOpsProvider(GitProvider):
    """Azure DevOps provider implementation."""

    PROVIDER_NAME = "azuredevops"
    SUPPORTED_AUTH_METHODS = [AuthMethod.PAT]
    DEFAULT_API_VERSION = "7.1"

    def __init__(self, config: Dict[str, Any]):
        """Initialize Azure DevOps provider.

        Args:
            config: Configuration dictionary with unified keys:
                - url: Azure DevOps organization URL
                - user: Username (not used for Azure DevOps PAT auth)
                - token: Personal Access Token
                - workspace: Optional workspace identifier
        """
        # Set instance attributes before calling super() which calls _validate_config
        # Fail-fast: require these fields to be present (no fallbacks)
        if "url" not in config:
            raise ValueError("Missing required field: url")
        if "token" not in config:
            raise ValueError("Missing required field: token")

        self.url = config["url"]
        self.user = config.get("user", "")  # Not used for PAT auth
        self.token = config["token"]

        # Ensure URL is properly formatted (fail-fast validation)
        if not self.url:
            raise ValueError("url cannot be empty")
        if not self.url.startswith(("http://", "https://")):
            self.url = f"https://{self.url}"

        # Azure DevOps SDK clients
        self.connection: Optional[Connection] = None
        self.core_client: Optional[CoreClient] = None
        self.git_client: Optional[GitClient] = None

        # Now call super() which will validate the config
        super().__init__(config)

    def _validate_config(self) -> None:
        """Validate provider-specific configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.url:
            raise ValueError("Azure DevOps organization URL is required")
        if not self.token:
            raise ValueError("Personal Access Token is required")

    async def authenticate(self) -> bool:
        """Authenticate with Azure DevOps.

        Returns:
            bool: True if authentication successful
        """
        if self._authenticated:
            return True

        try:
            # Initialize connection
            credentials = BasicAuthentication("", self.token)
            self.connection = Connection(base_url=self.url, creds=credentials)

            # Get clients
            self.core_client = self.connection.clients.get_core_client()
            self.git_client = self.connection.clients.get_git_client()

            # Test the connection by listing projects
            self.core_client.get_projects()

            self._authenticated = True
            logger.debug("Azure DevOps authentication successful for %s", self.url)
            return True

        except (AzureDevOpsAuthenticationError, ClientRequestError) as e:
            logger.error("Azure DevOps authentication failed: %s", e)
            self._authenticated = False
            return False
        except Exception as e:
            logger.error("Unexpected error during Azure DevOps authentication: %s", e)
            self._authenticated = False
            return False

    async def test_connection(self) -> bool:
        """Test if the connection and authentication are valid.

        Returns:
            bool: True if connection is valid
        """
        if not self._authenticated:
            return await self.authenticate()

        if not self.core_client:
            return False

        try:
            # A simple call to verify authentication and connection
            self.core_client.get_projects()
            logger.debug("Azure DevOps connection test successful.")
            return True
        except (AzureDevOpsAuthenticationError, ClientRequestError) as e:
            logger.error("Azure DevOps connection test failed: %s", e)
            self._authenticated = False
            return False
        except Exception as e:
            logger.error("Unexpected error during connection test: %s", e)
            self._authenticated = False
            return False

    async def list_organizations(self) -> List[Organization]:
        """List all accessible organizations.

        For Azure DevOps, this returns the current organization only,
        as the PAT is typically scoped to a single organization.

        Returns:
            List of Organization objects
        """
        if not await self.authenticate():
            return []

        # Parse organization name from URL
        parsed = urlparse(self.url)
        org_name = (
            parsed.path.strip("/").split("/")[0] if parsed.path else parsed.hostname
        )

        return [
            Organization(
                name=org_name,
                url=self.url,
                provider=self.PROVIDER_NAME,
                metadata={},
            )
        ]

    async def list_projects(self, organization: str) -> List[Project]:
        """List all projects in the organization.

        Args:
            organization: Organization name (not used, as connection is already org-scoped)

        Returns:
            List of Project objects
        """
        if not await self.authenticate():
            return []

        if not self.core_client:
            logger.error("Core client not initialized")
            return []

        try:
            # Get all projects
            projects_response = self.core_client.get_projects()
            projects = []

            for proj in projects_response:
                projects.append(
                    Project(
                        name=proj.name,
                        organization=organization,
                        description=proj.description,
                        metadata={
                            "id": proj.id,
                            "state": proj.state,
                            "revision": proj.revision,
                            "visibility": proj.visibility,
                            "last_update_time": (
                                str(proj.last_update_time)
                                if proj.last_update_time
                                else None
                            ),
                        },
                    )
                )

            logger.debug("Found %d projects in organization", len(projects))
            return projects

        except Exception as e:
            logger.error("Error listing projects: %s", e)
            return []

    async def list_repositories(
        self,
        organization: str,
        project: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Repository]:
        """List repositories with optional filtering.

        Args:
            organization: Organization name (not used, connection is org-scoped)
            project: Project name to list repos from
            filters: Optional filters (not yet implemented for Azure DevOps)

        Yields:
            Repository objects
        """
        if not await self.authenticate():
            return

        if not self.git_client:
            logger.error("Git client not initialized")
            return

        if not project:
            logger.error("Project name is required for Azure DevOps")
            return

        try:
            # Get project details first
            project_details = await self._get_project(project)
            if not project_details:
                logger.error("Project '%s' not found", project)
                return

            # List repositories in the project
            repos: List[GitRepository] = self.git_client.get_repositories(
                project=project_details.id
            )

            for repo in repos:
                # Convert SDK GitRepository to our Repository model
                repository = Repository(
                    name=repo.name,
                    clone_url=repo.remote_url,
                    ssh_url=repo.ssh_url,
                    is_disabled=repo.is_disabled,
                    is_private=True,  # Azure DevOps repos are typically private
                    default_branch=repo.default_branch or "main",
                    size=repo.size,  # Size is in bytes, our model expects KB
                    description=None,  # Not available in GitRepository
                    created_at=None,  # Not available
                    updated_at=None,  # Not available
                    provider=self.PROVIDER_NAME,
                    metadata={
                        "id": repo.id,
                        "project_id": repo.project.id if repo.project else None,
                        "web_url": repo.web_url,
                        "is_fork": repo.is_fork if hasattr(repo, "is_fork") else False,
                    },
                )
                yield repository

        except Exception as e:
            logger.error("Error listing repositories: %s", e)

    async def get_repository(
        self, organization: str, repository: str, project: Optional[str] = None
    ) -> Optional[Repository]:
        """Get a specific repository.

        Args:
            organization: Organization name (not used, connection is org-scoped)
            repository: Repository name
            project: Project name (required for Azure DevOps)

        Returns:
            Repository object or None if not found
        """
        if not await self.authenticate():
            return None

        if not self.git_client:
            logger.error("Git client not initialized")
            return None

        if not project:
            logger.error("Project name is required for Azure DevOps")
            return None

        try:
            # Get project details first
            project_details = await self._get_project(project)
            if not project_details:
                logger.error("Project '%s' not found", project)
                return None

            # Get the specific repository
            repo = self.git_client.get_repository(
                project=project_details.id, repository_id=repository
            )

            if repo:
                return Repository(
                    name=repo.name,
                    clone_url=repo.remote_url,
                    ssh_url=repo.ssh_url,
                    is_disabled=repo.is_disabled,
                    is_private=True,
                    default_branch=repo.default_branch or "main",
                    size=repo.size,
                    description=None,
                    created_at=None,
                    updated_at=None,
                    provider=self.PROVIDER_NAME,
                    metadata={
                        "id": repo.id,
                        "project_id": repo.project.id if repo.project else None,
                        "web_url": repo.web_url,
                        "is_fork": repo.is_fork if hasattr(repo, "is_fork") else False,
                    },
                )

        except Exception as e:
            logger.error("Error getting repository '%s': %s", repository, e)

        return None

    def get_authenticated_clone_url(self, repository: Repository) -> str:
        """Get clone URL with embedded authentication.

        Args:
            repository: Repository object

        Returns:
            Authenticated clone URL
        """
        return embed_pat_in_url(repository.clone_url, self.token)

    async def _get_project(
        self, project_name_or_id: str
    ) -> Optional[TeamProjectReference]:
        """Get project details by name or ID.

        Args:
            project_name_or_id: Project name or ID

        Returns:
            TeamProjectReference or None if not found
        """
        if not self.core_client:
            return None

        try:
            return self.core_client.get_project(project_name_or_id)
        except Exception as e:
            logger.error("Failed to get project '%s': %s", project_name_or_id, e)
            return None

    def supports_projects(self) -> bool:
        """Azure DevOps supports project hierarchy.

        Returns:
            bool: True
        """
        return True

    async def close(self) -> None:
        """Cleanup resources."""
        # Azure DevOps SDK doesn't require explicit cleanup
        self._authenticated = False
        self.connection = None
        self.core_client = None
        self.git_client = None

"""Azure DevOps Manager - Legacy implementation.

This module contains the AzDevOpsManager class that was previously in __main__.py.
It will be refactored in future sprints to align with the new provider architecture.
"""

import logging
from typing import Optional

# Azure DevOps SDK imports
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.git import GitClient
from azure.devops.v7_1.core import CoreClient, TeamProjectReference
from azure.devops.exceptions import ClientRequestError, AzureDevOpsAuthenticationError

# Import from mgit modules
from mgit.config.manager import get_config_value

logger = logging.getLogger(__name__)


class AzDevOpsManager:
    def __init__(self, organization_url: Optional[str] = None, pat: Optional[str] = None):
        # Get organization URL and PAT, prioritizing arguments, then config/env
        self.ado_org = organization_url or get_config_value("AZURE_DEVOPS_ORG_URL")
        self.ado_pat = pat or get_config_value("AZURE_DEVOPS_EXT_PAT")

        # Ensure the URL is properly formatted
        if self.ado_org and not self.ado_org.startswith(("http://", "https://")):
            self.ado_org = f"https://{self.ado_org}"

        self.connection: Optional[Connection] = None
        self.core_client: Optional[CoreClient] = None
        self.git_client: Optional[GitClient] = None

        if not self.ado_org or not self.ado_pat:
            logger.debug("Organization URL or PAT not provided. Cannot initialize SDK connection.")
            # Allow initialization but connection will fail later if needed
            return

        try:
            # Initialize connection
            credentials = BasicAuthentication('', self.ado_pat)
            self.connection = Connection(base_url=self.ado_org, creds=credentials)

            # Get clients
            self.core_client = self.connection.clients.get_core_client()
            self.git_client = self.connection.clients.get_git_client()
            logger.debug("Azure DevOps SDK connection and clients initialized for %s", self.ado_org)
        except Exception as e:
            logger.error("Failed to initialize Azure DevOps SDK connection: %s", e)
            # Set clients to None to indicate failure
            self.connection = None
            self.core_client = None
            self.git_client = None
            # Don't raise here, let commands handle the lack of connection

    def test_connection(self) -> bool:
        """Tests the SDK connection by trying to list projects."""
        if not self.core_client:
            logger.error("Cannot test connection: SDK client not initialized.")
            return False
        try:
            # A simple call to verify authentication and connection
            self.core_client.get_projects()
            logger.debug("SDK connection test successful.")
            return True
        except (AzureDevOpsAuthenticationError, ClientRequestError) as e:
            logger.error("SDK connection test failed: %s", e)
            return False
        except Exception as e:
            logger.error("Unexpected error during SDK connection test: %s", e)
            return False

    def get_project(self, project_name_or_id: str) -> Optional[TeamProjectReference]:
        """Get project details by name or ID."""
        if not self.core_client:
            logger.error("Cannot get project: SDK client not initialized.")
            return None
        try:
            return self.core_client.get_project(project_name_or_id)
        except Exception as e:
            logger.error(f"Failed to get project '{project_name_or_id}': {e}")
            return None

    # Removed check_az_cli_installed and ensure_ado_ext_installed
    # Removed is_logged_into_az_devops and login_to_az_devops (handled by __init__ and test_connection)
    # Removed configure_az_devops (handled by SDK client initialization)
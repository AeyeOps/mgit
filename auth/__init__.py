"""
Authentication and credential management for mgit.

This module provides secure storage and retrieval of credentials
for various git providers (Azure DevOps, GitHub, BitBucket).
"""

from mgit.auth.manager import CredentialManager
from mgit.auth.models import Credential, Provider

__all__ = ["CredentialManager", "Credential", "Provider"]
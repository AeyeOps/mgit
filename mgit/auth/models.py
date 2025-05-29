"""
Data models for credential management.

This module defines the structures used to represent credentials
and providers in the mgit authentication system.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class Provider(str, Enum):
    """Supported git providers."""
    AZURE_DEVOPS = "azure_devops"
    GITHUB = "github"
    BITBUCKET = "bitbucket"
    GITLAB = "gitlab"  # For future expansion
    GENERIC = "generic"  # For generic git credentials

    @classmethod
    def from_url(cls, url: str) -> "Provider":
        """Determine provider from URL."""
        url = url.lower()
        if "dev.azure.com" in url or "visualstudio.com" in url:
            return cls.AZURE_DEVOPS
        elif "github.com" in url:
            return cls.GITHUB
        elif "bitbucket.org" in url:
            return cls.BITBUCKET
        elif "gitlab.com" in url:
            return cls.GITLAB
        else:
            return cls.GENERIC


@dataclass
class Credential:
    """
    Represents a stored credential.
    
    Attributes:
        provider: The git provider (e.g., azure_devops, github)
        name: A unique name for this credential
        username: Username (optional, some providers only need token)
        token: The authentication token/password
        url: Associated URL (optional)
        created_at: When the credential was created
        updated_at: When the credential was last updated
        metadata: Additional provider-specific metadata
    """
    provider: Provider
    name: str
    token: str
    username: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "provider": self.provider.value,
            "name": self.name,
            "username": self.username,
            "token": self.token,
            "url": self.url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Credential":
        """Create from dictionary."""
        # Handle datetime conversion
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        
        return cls(
            provider=Provider(data["provider"]),
            name=data["name"],
            username=data.get("username"),
            token=data["token"],
            url=data.get("url"),
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get("metadata", {})
        )
    
    def mask_token(self) -> str:
        """Return a masked version of the token for display."""
        if not self.token:
            return ""
        if len(self.token) <= 8:
            return "*" * len(self.token)
        return self.token[:4] + "*" * (len(self.token) - 8) + self.token[-4:]
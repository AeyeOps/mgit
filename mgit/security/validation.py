"""Input validation and sanitization for mgit security.

This module provides comprehensive input validation to prevent various
security vulnerabilities including path traversal, injection attacks,
and malformed input handling.
"""

import os
import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse, quote, unquote

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Comprehensive input validation and sanitization."""

    # Dangerous path patterns
    DANGEROUS_PATH_PATTERNS = [
        r"\.\./",  # Parent directory traversal
        r"\.\.\\",  # Windows parent directory traversal
        r"/\.\.",  # Parent directory at start
        r"\\\.\.",  # Windows parent directory at start
        r"~/",  # Home directory expansion
        r"\$\{",  # Variable expansion
        # Removed URL encoding pattern - too restrictive for legitimate URLs
        r'[<>"|*]',  # Windows forbidden characters (removed : and ? which are valid in URLs)
    ]

    # Allowed repository name patterns
    REPO_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")

    # Organization/workspace name pattern
    ORG_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")

    # Project name pattern
    PROJECT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._\s-]+$")

    # URL scheme whitelist
    ALLOWED_URL_SCHEMES = {"http", "https", "git", "ssh"}

    # Maximum input lengths
    MAX_LENGTHS = {
        "url": 2048,
        "path": 4096,
        "repo_name": 255,
        "org_name": 255,
        "project_name": 255,
        "branch_name": 255,
        "description": 1000,
    }

    def __init__(self):
        """Initialize security validator."""
        self.dangerous_patterns = [
            re.compile(pattern) for pattern in self.DANGEROUS_PATH_PATTERNS
        ]

    def validate_url(self, url: str, schemes: Optional[List[str]] = None) -> bool:
        """Validate URL format and scheme.

        Args:
            url: URL to validate
            schemes: Allowed schemes (defaults to ALLOWED_URL_SCHEMES)

        Returns:
            True if URL is valid and safe
        """
        if not url or not isinstance(url, str):
            return False

        # Check length
        if len(url) > self.MAX_LENGTHS["url"]:
            logger.warning(
                f"URL exceeds maximum length: {len(url)} > {self.MAX_LENGTHS['url']}"
            )
            return False

        try:
            parsed = urlparse(url)

            # Check scheme
            allowed_schemes = schemes or self.ALLOWED_URL_SCHEMES
            if parsed.scheme.lower() not in allowed_schemes:
                logger.warning(f"Invalid URL scheme: {parsed.scheme}")
                return False

            # Check for hostname
            if not parsed.netloc:
                logger.warning("URL missing hostname")
                return False

            # Check for suspicious patterns
            if any(pattern.search(url) for pattern in self.dangerous_patterns):
                logger.warning("URL contains dangerous patterns")
                return False

            return True

        except Exception as e:
            logger.warning(f"URL validation error: {e}")
            return False

    def validate_path(self, path: Union[str, Path], must_exist: bool = False) -> bool:
        """Validate file system path.

        Args:
            path: Path to validate
            must_exist: Whether path must exist

        Returns:
            True if path is valid and safe
        """
        if not path:
            return False

        path_str = str(path)

        # Check length
        if len(path_str) > self.MAX_LENGTHS["path"]:
            logger.warning(
                f"Path exceeds maximum length: {len(path_str)} > {self.MAX_LENGTHS['path']}"
            )
            return False

        # Check for dangerous patterns
        if any(pattern.search(path_str) for pattern in self.dangerous_patterns):
            logger.warning(f"Path contains dangerous patterns: {path_str}")
            return False

        # Convert to Path object for further validation
        try:
            path_obj = Path(path_str).resolve()

            # Check if path exists when required
            if must_exist and not path_obj.exists():
                logger.warning(f"Required path does not exist: {path_obj}")
                return False

            # Check if path is within allowed directories (if specified)
            # This is a placeholder for more sophisticated access control

            return True

        except (OSError, ValueError) as e:
            logger.warning(f"Path validation error: {e}")
            return False

    def validate_repository_name(self, name: str) -> bool:
        """Validate repository name.

        Args:
            name: Repository name to validate

        Returns:
            True if name is valid
        """
        if not name or not isinstance(name, str):
            return False

        # Check length
        if len(name) > self.MAX_LENGTHS["repo_name"]:
            logger.warning(
                f"Repository name too long: {len(name)} > {self.MAX_LENGTHS['repo_name']}"
            )
            return False

        # Check pattern
        if not self.REPO_NAME_PATTERN.match(name):
            logger.warning(f"Invalid repository name format: {name}")
            return False

        # Additional checks
        if name.startswith(".") or name.endswith("."):
            logger.warning(f"Repository name cannot start or end with dot: {name}")
            return False

        if name in ("", ".", "..", "CON", "PRN", "AUX", "NUL"):
            logger.warning(f"Reserved repository name: {name}")
            return False

        return True

    def validate_organization_name(self, name: str) -> bool:
        """Validate organization/workspace name.

        Args:
            name: Organization name to validate

        Returns:
            True if name is valid
        """
        if not name or not isinstance(name, str):
            return False

        # Check length
        if len(name) > self.MAX_LENGTHS["org_name"]:
            logger.warning(
                f"Organization name too long: {len(name)} > {self.MAX_LENGTHS['org_name']}"
            )
            return False

        # Check pattern
        if not self.ORG_NAME_PATTERN.match(name):
            logger.warning(f"Invalid organization name format: {name}")
            return False

        return True

    def validate_project_name(self, name: str) -> bool:
        """Validate project name.

        Args:
            name: Project name to validate

        Returns:
            True if name is valid
        """
        if not name or not isinstance(name, str):
            return False

        # Check length
        if len(name) > self.MAX_LENGTHS["project_name"]:
            logger.warning(
                f"Project name too long: {len(name)} > {self.MAX_LENGTHS['project_name']}"
            )
            return False

        # Check pattern (allows spaces for project names)
        if not self.PROJECT_NAME_PATTERN.match(name):
            logger.warning(f"Invalid project name format: {name}")
            return False

        return True

    def sanitize_input(self, value: Any, input_type: str = "string") -> Any:
        """Sanitize input value based on type.

        Args:
            value: Value to sanitize
            input_type: Type of input for specific sanitization

        Returns:
            Sanitized value
        """
        if value is None:
            return None

        if input_type == "path":
            return self.sanitize_path(str(value))
        elif input_type == "url":
            return self.sanitize_url(str(value))
        elif input_type == "repo_name":
            return self.sanitize_repository_name(str(value))
        elif input_type == "string":
            return self.sanitize_string(str(value))
        else:
            return str(value)

    def sanitize_string(self, value: str) -> str:
        """Basic string sanitization.

        Args:
            value: String to sanitize

        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)

        # Remove null bytes
        value = value.replace("\x00", "")

        # Normalize whitespace
        value = " ".join(value.split())

        # Remove control characters except newlines and tabs
        value = "".join(char for char in value if ord(char) >= 32 or char in "\n\t")

        return value.strip()

    def sanitize_path(self, path: str) -> str:
        """Sanitize file system path.

        Args:
            path: Path to sanitize

        Returns:
            Sanitized path
        """
        if not isinstance(path, str):
            return str(path)

        # Remove dangerous sequences
        sanitized = path
        for pattern in self.dangerous_patterns:
            sanitized = pattern.sub("", sanitized)

        # Normalize path separators
        sanitized = sanitized.replace("\\", "/")

        # Remove multiple consecutive separators
        sanitized = re.sub(r"/+", "/", sanitized)

        # Remove leading/trailing separators if not root
        if len(sanitized) > 1:
            sanitized = sanitized.strip("/")

        return sanitized

    def sanitize_url(self, url: str) -> str:
        """Sanitize URL.

        Args:
            url: URL to sanitize

        Returns:
            Sanitized URL
        """
        if not isinstance(url, str):
            return str(url)

        try:
            # Parse and reconstruct URL to normalize it
            parsed = urlparse(url)

            # Ensure scheme is lowercase
            scheme = parsed.scheme.lower() if parsed.scheme else ""

            # Ensure netloc is present and normalized
            netloc = parsed.netloc.lower() if parsed.netloc else ""

            # Sanitize path component
            path = self.sanitize_path(parsed.path) if parsed.path else ""

            # Keep query and fragment as-is (they will be URL encoded)
            query = parsed.query or ""
            fragment = parsed.fragment or ""

            # Reconstruct URL
            from urllib.parse import urlunparse

            return urlunparse((scheme, netloc, path, parsed.params, query, fragment))

        except Exception as e:
            logger.warning(f"URL sanitization error: {e}")
            return url

    def sanitize_repository_name(self, name: str) -> str:
        """Sanitize repository name.

        Args:
            name: Repository name to sanitize

        Returns:
            Sanitized repository name
        """
        if not isinstance(name, str):
            return str(name)

        # Keep only allowed characters
        sanitized = re.sub(r"[^a-zA-Z0-9._-]", "", name)

        # Remove leading/trailing dots or dashes
        sanitized = sanitized.strip(".-")

        # Ensure not empty
        if not sanitized:
            return "unnamed-repo"

        return sanitized


# Global validator instance
_validator = SecurityValidator()


def validate_input(value: Any, input_type: str = "string", **kwargs) -> bool:
    """Validate input using global validator.

    Args:
        value: Value to validate
        input_type: Type of validation to perform
        **kwargs: Additional validation parameters

    Returns:
        True if input is valid
    """
    if input_type == "url":
        return _validator.validate_url(value, kwargs.get("schemes"))
    elif input_type == "path":
        return _validator.validate_path(value, kwargs.get("must_exist", False))
    elif input_type == "repo_name":
        return _validator.validate_repository_name(value)
    elif input_type == "org_name":
        return _validator.validate_organization_name(value)
    elif input_type == "project_name":
        return _validator.validate_project_name(value)
    else:
        # Basic validation for any input
        return value is not None and isinstance(value, str) and len(str(value)) > 0


def sanitize_path(path: Union[str, Path]) -> str:
    """Sanitize file system path."""
    return _validator.sanitize_path(str(path))


def sanitize_url(url: str) -> str:
    """Sanitize URL."""
    return _validator.sanitize_url(url)


def sanitize_repository_name(name: str) -> str:
    """Sanitize repository name."""
    return _validator.sanitize_repository_name(name)


def is_safe_path(
    path: Union[str, Path], base_path: Optional[Union[str, Path]] = None
) -> bool:
    """Check if path is safe and within allowed boundaries.

    Args:
        path: Path to check
        base_path: Base path that the target path should be within

    Returns:
        True if path is safe
    """
    try:
        path_obj = Path(path).resolve()

        # Check basic validation
        if not _validator.validate_path(path_obj):
            return False

        # Check if within base path if specified
        if base_path:
            base_obj = Path(base_path).resolve()
            try:
                path_obj.relative_to(base_obj)
            except ValueError:
                logger.warning(f"Path {path_obj} is outside base path {base_obj}")
                return False

        return True

    except Exception as e:
        logger.warning(f"Path safety check failed: {e}")
        return False


def validate_git_url(url: str) -> bool:
    """Validate Git repository URL.

    Args:
        url: Git URL to validate

    Returns:
        True if URL is a valid Git URL
    """
    if not url or not isinstance(url, str):
        return False

    # Allow git://, https://, http://, ssh:// schemes
    git_schemes = ["git", "https", "http", "ssh"]

    # Check basic URL validation
    if not _validator.validate_url(url, git_schemes):
        return False

    # Additional Git-specific validation
    parsed = urlparse(url)

    # Check for common Git hosting patterns
    git_hosts = [
        "github.com",
        "gitlab.com",
        "bitbucket.org",
        "dev.azure.com",
        "ssh.dev.azure.com",
        "vs-ssh.visualstudio.com",
    ]

    # If hostname is recognized, do additional validation
    if any(host in parsed.netloc.lower() for host in git_hosts):
        # GitHub/GitLab/BitBucket URLs should end with .git or be in specific format
        if (
            "github.com" in parsed.netloc.lower()
            or "gitlab.com" in parsed.netloc.lower()
        ):
            # Should be in format: /owner/repo or /owner/repo.git
            path_parts = [p for p in parsed.path.split("/") if p]
            if len(path_parts) < 2:
                logger.warning(f"Invalid Git URL path format: {parsed.path}")
                return False

    return True

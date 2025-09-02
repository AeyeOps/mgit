"""Query parser for mgit list command.

Handles query patterns like:
- "myorg/*/pay*" - repos ending in "pay" across all projects in myorg
- "myorg/MyProject/*" - all repos in specific org/project
- "*/*/mobile*" - mobile repos across all orgs
"""

import fnmatch
from dataclasses import dataclass
from typing import Optional


@dataclass
class QueryPattern:
    """Parsed query pattern with organization, project, and repository patterns."""

    org_pattern: str
    project_pattern: str
    repo_pattern: str
    provider_type: Optional[str] = None

    @property
    def has_org_filter(self) -> bool:
        """Check if organization is filtered (not wildcard)."""
        return self.org_pattern != "*"

    @property
    def has_project_filter(self) -> bool:
        """Check if project is filtered, considering provider type."""
        if self.provider_type in ("github", "bitbucket"):
            return False
        return self.project_pattern != "*"

    @property
    def has_repo_filter(self) -> bool:
        """Check if repository is filtered (not wildcard)."""
        return self.repo_pattern != "*"


def parse_query(query: str, provider_type: Optional[str] = None) -> QueryPattern:
    """Parse query string into pattern components.

    Args:
        query: Query pattern like "org/project/repo" with wildcards
        provider_type: Type of provider to tailor parsing (e.g., 'github')

    Returns:
        QueryPattern with parsed segments
    """
    segments = query.split("/")

    org_pattern = segments[0] if segments else "*"

    # Provider-specific parsing
    if provider_type in ("github", "bitbucket"):
        # GitHub/BitBucket: org/repo (repo can have slashes)
        project_pattern = "*"
        repo_pattern = "/".join(segments[1:]) if len(segments) > 1 else "*"
    else:
        # Default (Azure DevOps): org/project/repo
        project_pattern = segments[1] if len(segments) > 1 else "*"
        repo_pattern = segments[2] if len(segments) > 2 else "*"

    # Pad with wildcards if needed for providers that need 3 segments
    if provider_type not in ("github", "bitbucket"):
        while len(segments) < 3:
            segments.append("*")
        org_pattern, project_pattern, repo_pattern = (
            segments[0],
            segments[1],
            segments[2],
        )

    return QueryPattern(
        org_pattern=org_pattern or "*",
        project_pattern=project_pattern or "*",
        repo_pattern=repo_pattern or "*",
        provider_type=provider_type,
    )


def matches_pattern(text: str, pattern: str, case_sensitive: bool = False) -> bool:
    """Check if text matches a glob pattern.

    Args:
        text: Text to match against
        pattern: Glob pattern (* and ? wildcards supported)
        case_sensitive: Whether matching should be case sensitive

    Returns:
        True if text matches pattern

    Examples:
        >>> matches_pattern("payment-api", "pay*")
        True
        >>> matches_pattern("PaymentAPI", "*api*")
        True
        >>> matches_pattern("user-service", "pay*")
        False
        >>> matches_pattern("myorg.visualstudio.com", "myorg")
        True
    """
    if not case_sensitive:
        text = text.lower()
        pattern = pattern.lower()

    # First try exact pattern match
    if fnmatch.fnmatch(text, pattern):
        return True

    # If pattern doesn't contain wildcards, try prefix matching for user-friendliness
    # This allows "myorg" to match "myorg.visualstudio.com"
    if "*" not in pattern and "?" not in pattern:
        return fnmatch.fnmatch(text, pattern + "*")

    return False


def validate_query(query: str) -> Optional[str]:
    """Validate query syntax and return error message if invalid.

    Args:
        query: Query string to validate

    Returns:
        Error message if invalid, None if valid
    """
    if not query or not query.strip():
        return "Query cannot be empty"

    # Check for invalid characters (basic validation)
    invalid_chars = set(query) - set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789*?/-_."
    )
    if invalid_chars:
        return f"Invalid characters in query: {', '.join(sorted(invalid_chars))}"

    # Check segment count (max 3 for org/project/repo)
    segments = query.split("/")
    if len(segments) > 3:
        return "Query can have at most 3 segments (org/project/repo)"

    return None

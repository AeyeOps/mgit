"""Git utility functions."""

import logging
import os
import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote, urlparse

logger = logging.getLogger(__name__)


def embed_pat_in_url(url: str, pat: str) -> str:
    """
    Embed a Personal Access Token (PAT) into a git URL.

    Args:
        url: The original git URL.
        pat: The Personal Access Token.

    Returns:
        The URL with the PAT embedded.
    """
    if "@" in url:
        # URL already has some form of authentication
        return url
    if url.startswith("https://"):
        # Add PAT to HTTPS URL
        return url.replace("https://", f"https://PersonalAccessToken:{pat}@")
    return url  # Return original URL if not HTTPS


def get_git_remote_url(repo_path: Path) -> Optional[str]:
    """
    Get the remote URL of a git repository.

    Args:
        repo_path: Path to the git repository.

    Returns:
        The remote URL or None if not found.
    """
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        return None

    config_path = git_dir / "config"
    if not config_path.exists():
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        for line in f:
            if "url =" in line:
                return line.split("=")[1].strip()
    return None


def sanitize_repo_name(name: str) -> str:
    """
    Sanitize a repository name to be used as a valid directory name.
    This function replaces slashes and other invalid characters with hyphens.
    """
    # Replace slashes and whitespace with hyphens
    name = re.sub(r"[\s/\\]+", "-", name)
    # Remove invalid characters for directory names
    name = re.sub(r'[<>:"|?*]', "", name)
    # Replace multiple hyphens with a single one
    name = re.sub(r"-+", "-", name)
    # Remove leading/trailing hyphens and dots
    name = name.strip("-. ")
    # Handle Windows reserved names
    reserved_names = [
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    ]
    if name.upper() in reserved_names:
        name += "_"
    return name


def is_git_repository(path: Path) -> bool:
    """Check if a path is a git repository."""
    return (path / ".git").is_dir()


def normalize_path(path_str: str) -> Path:
    """Normalize a path string, expanding user and environment variables."""
    return Path(os.path.expanduser(os.path.expandvars(path_str)))


def validate_url(url: str) -> bool:
    """Validate if a string is a valid-looking URL."""
    if not url:
        return False
    return url.startswith(("http://", "https://"))


def sanitize_path_segment(segment: str) -> str:
    """
    Sanitize a single path segment to be filesystem-safe while preserving spaces.
    
    Args:
        segment: Path segment to sanitize
        
    Returns:
        Sanitized path segment safe for filesystem use
    """
    if not segment:
        return ""
    
    # Remove invalid characters for directory names but preserve spaces
    segment = re.sub(r'[<>:"|?*]', "", segment)
    # Replace forward/back slashes with hyphens  
    segment = re.sub(r"[/\\]+", "-", segment)
    # Replace multiple hyphens with single hyphen
    segment = re.sub(r"-+", "-", segment)
    # Remove leading/trailing hyphens, dots, and spaces
    segment = segment.strip("-. ")
    
    # Handle Windows reserved names
    reserved_names = [
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    ]
    if segment.upper() in reserved_names:
        segment += "_"
    
    return segment


def build_repo_path(clone_url: str) -> Path:
    """
    Build hierarchical repository path from Git URL.
    
    Always creates a 4-level hierarchical structure: host/org/project/repo
    Handles URL encoding/decoding and provider-specific patterns.
    Throws ValueError if URL cannot be parsed into the required structure.
    
    Supported providers:
    - Azure DevOps: Extracts org/project/repo from various URL formats
    - GitHub: Uses owner as org, "repos" as project placeholder
    - BitBucket: Handles workspace/project/repo or workspace/repo patterns
    
    Args:
        clone_url: Git repository URL (HTTPS or SSH format)
        
    Returns:
        Path object with exactly 4 levels: host/org/project/repo
        
    Raises:
        ValueError: If URL cannot be parsed or doesn't contain required components
    """
    if not clone_url or not isinstance(clone_url, str):
        raise ValueError("clone_url must be a non-empty string")
    
    clone_url = clone_url.strip()
    if not clone_url:
        raise ValueError("clone_url cannot be empty or whitespace")
    
    # Handle SSH vs HTTPS URL formats
    if clone_url.startswith("git@"):
        host, org, project, repo = _parse_ssh_url(clone_url)
    elif clone_url.startswith(("http://", "https://")):
        host, org, project, repo = _parse_https_url(clone_url)
    else:
        raise ValueError(f"Unsupported URL format. Must start with 'git@', 'http://', or 'https://': {clone_url}")
    
    # Validate all components are present and non-empty
    if not all([host, org, project, repo]):
        raise ValueError(f"Failed to extract all required components (host/org/project/repo) from URL: {clone_url}")
    
    # Sanitize each component for filesystem safety
    safe_host = sanitize_path_segment(host)
    safe_org = sanitize_path_segment(org)
    safe_project = sanitize_path_segment(project)
    safe_repo = sanitize_path_segment(repo)
    
    # Validate sanitized components are still non-empty
    if not all([safe_host, safe_org, safe_project, safe_repo]):
        raise ValueError(f"One or more path components became empty after sanitization: {clone_url}")
    
    return Path(safe_host, safe_org, safe_project, safe_repo)


def _parse_ssh_url(clone_url: str) -> tuple[str, str, str, str]:
    """Parse SSH format Git URL (git@host:path)."""
    # Extract host and path from SSH format
    ssh_pattern = r"^git@([^:]+):(.+)$"
    match = re.match(ssh_pattern, clone_url)
    if not match:
        raise ValueError(f"Invalid SSH URL format: {clone_url}")
    
    host = match.group(1)
    path = match.group(2)
    
    if not host or not path:
        raise ValueError(f"Invalid SSH URL - missing host or path: {clone_url}")
    
    # Remove .git suffix if present
    if path.endswith(".git"):
        path = path[:-4]
    
    return _parse_repository_path(host, path, clone_url)


def _parse_https_url(clone_url: str) -> tuple[str, str, str, str]:
    """Parse HTTPS format Git URL."""
    try:
        parsed = urlparse(clone_url)
        
        if not parsed.hostname:
            raise ValueError(f"No hostname found in URL: {clone_url}")
        
        if not parsed.path or parsed.path == "/":
            raise ValueError(f"No path found in URL: {clone_url}")
        
        host = parsed.hostname
        # URL decode the path and remove leading/trailing slashes
        path = unquote(parsed.path.strip("/"))
        
        if not path:
            raise ValueError(f"Empty path after URL decoding: {clone_url}")
        
        return _parse_repository_path(host, path, clone_url)
        
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to parse HTTPS URL: {clone_url} - {str(e)}")


def _parse_repository_path(host: str, path: str, original_url: str) -> tuple[str, str, str, str]:
    """Parse repository path based on Git provider patterns."""
    # Split path into segments and filter out empty ones
    segments = [seg.strip() for seg in path.split("/") if seg.strip()]
    
    if not segments:
        raise ValueError(f"No valid path segments found: {original_url}")
    
    # Normalize host for provider detection
    host_lower = host.lower()
    
    # Azure DevOps patterns
    if "dev.azure.com" in host_lower or "visualstudio.com" in host_lower:
        return _parse_azure_devops_path(host, segments, original_url)
    
    # GitHub patterns
    elif "github.com" in host_lower:
        return _parse_github_path(host, segments, original_url)
    
    # BitBucket patterns
    elif "bitbucket.org" in host_lower:
        return _parse_bitbucket_path(host, segments, original_url)
    
    # Generic Git provider - assume owner/repo pattern with placeholder project
    else:
        return _parse_generic_path(host, segments, original_url)


def _parse_azure_devops_path(host: str, segments: List[str], original_url: str) -> tuple[str, str, str, str]:
    """Parse Azure DevOps repository path patterns."""
    # Remove common Azure DevOps path elements
    filtered_segments = []
    for segment in segments:
        if segment not in ["DefaultCollection", "_git"]:
            filtered_segments.append(segment)
    
    if len(filtered_segments) < 2:
        raise ValueError(f"Azure DevOps URL must have at least project/repo: {original_url}")
    
    if len(filtered_segments) == 2:
        # Legacy format: project/repo (missing org)
        # Extract org from hostname if possible, otherwise use host as org
        if "dev.azure.com" in host.lower():
            # Modern format should have org in path, this shouldn't happen
            raise ValueError(f"Modern Azure DevOps URL missing organization: {original_url}")
        else:
            # Legacy visualstudio.com format: use hostname base as org
            org = host.split('.')[0]  # e.g., "pdidev" from "pdidev.visualstudio.com"
            project = filtered_segments[0]
            repo = filtered_segments[1]
    elif len(filtered_segments) >= 3:
        # Standard format: org/project/repo
        org = filtered_segments[0]
        project = filtered_segments[1]
        repo = filtered_segments[2]
    else:
        raise ValueError(f"Invalid Azure DevOps URL structure: {original_url}")
    
    return host, org, project, repo


def _parse_github_path(host: str, segments: List[str], original_url: str) -> tuple[str, str, str, str]:
    """Parse GitHub repository path patterns."""
    if len(segments) < 2:
        raise ValueError(f"GitHub URL must have at least owner/repo: {original_url}")
    
    # GitHub structure: owner/repo (no natural project level)
    org = segments[0]  # owner
    repo = segments[1]  # repository name
    
    # Remove .git suffix if present
    if repo.endswith(".git"):
        repo = repo[:-4]
    
    # Use "repos" as project placeholder for consistent 4-level structure
    project = "repos"
    
    return host, org, project, repo


def _parse_bitbucket_path(host: str, segments: List[str], original_url: str) -> tuple[str, str, str, str]:
    """Parse BitBucket repository path patterns."""
    if len(segments) < 2:
        raise ValueError(f"BitBucket URL must have at least workspace/repo: {original_url}")
    
    # Remove .git suffix from last segment if present
    if segments[-1].endswith(".git"):
        segments[-1] = segments[-1][:-4]
    
    if len(segments) == 2:
        # BitBucket structure: workspace/repo (no project)
        workspace = segments[0]
        repo = segments[1]
        project = "repos"  # Use placeholder for consistent structure
    elif len(segments) >= 3:
        # BitBucket structure: workspace/project/repo
        workspace = segments[0]
        project = segments[1]
        repo = segments[2]
    else:
        raise ValueError(f"Invalid BitBucket URL structure: {original_url}")
    
    return host, workspace, project, repo


def _parse_generic_path(host: str, segments: List[str], original_url: str) -> tuple[str, str, str, str]:
    """Parse generic Git provider path (assumes owner/repo pattern)."""
    if len(segments) < 2:
        raise ValueError(f"Generic Git URL must have at least owner/repo: {original_url}")
    
    # Generic structure: owner/repo
    org = segments[0]
    repo = segments[1]
    
    # Remove .git suffix if present
    if repo.endswith(".git"):
        repo = repo[:-4]
    
    # Use "repos" as project placeholder
    project = "repos"
    
    return host, org, project, repo

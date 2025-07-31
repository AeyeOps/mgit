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
    
    Decodes percent-encoded characters and retains hierarchical structure
    as ``host/org/project/repo``.
    
    For Azure DevOps: host/org/project/repo (skips DefaultCollection)
    For GitHub: host/owner/repo  
    For BitBucket: host/workspace/project/repo or host/workspace/repo
    
    Args:
        clone_url: Git repository URL (HTTPS or SSH)
        
    Returns:
        Path object with hierarchical structure.
        Falls back to sanitized repo name if parsing fails.
    """
    try:
        from urllib.parse import urlparse, unquote
        
        # Parse the URL
        parsed = urlparse(clone_url)
        host = parsed.hostname or "unknown-host"
        path = unquote(parsed.path.lstrip("/"))
        
        if not path:
            # Fallback to sanitized repo name if no path
            return Path(sanitize_repo_name(clone_url))
        
        # Split path into segments
        segments = [seg for seg in path.split("/") if seg]
        
        # Remove 'DefaultCollection' for older Azure DevOps URLs
        if segments and segments[0] == "DefaultCollection":
            segments = segments[1:]
        
        # Handle different Git URL patterns
        if segments and segments[-1] == "_git" and len(segments) > 1:
            # Azure DevOps: remove "_git" suffix, last segment is repo
            segments = segments[:-1]
        elif segments and segments[-1].endswith(".git"):
            # Remove .git suffix from repository name
            segments[-1] = segments[-1][:-4]
        
        # Sanitize each path segment
        safe_segments = [sanitize_path_segment(seg) for seg in segments if seg]
        
        if not safe_segments:
            # Fallback if no valid segments
            return Path(sanitize_repo_name(clone_url))
            
        return Path(sanitize_path_segment(host), *safe_segments)
        
    except Exception as e:
        # Fallback to existing logic if URL parsing fails
        logger.debug(f"Failed to build hierarchical path for {clone_url}: {e}")
        return Path(sanitize_repo_name(clone_url))

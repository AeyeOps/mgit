"""Git utility functions."""

import re
from pathlib import Path
from typing import Optional


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
    name = re.sub(r"[/\\s]+", "-", name)
    # Remove invalid characters for directory names
    name = re.sub(r'[<>:"|?*]', "", name)
    # Replace multiple hyphens with a single one
    name = re.sub(r"-+", "-", name)
    # Remove leading/trailing hyphens and dots
    name = name.strip("-. ")
    # Handle Windows reserved names
    reserved_names = [
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4",
        "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]
    if name.upper() in reserved_names:
        name += "_"
    return name


def is_git_repository(path: Path) -> bool:
    """Check if a path is a git repository."""
    return (path / ".git").is_dir()

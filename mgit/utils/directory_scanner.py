"""
Directory scanning utilities for repository discovery.

Provides functions to find Git repositories in directory structures
for use by various mgit commands and discovery modules.
"""

import logging
from pathlib import Path

from mgit.git.utils import is_git_repository

logger = logging.getLogger(__name__)


def find_repositories_in_directory(
    root_path: Path, recursive: bool = True, max_depth: int = None
) -> list[Path]:
    """
    Find all Git repositories in a directory structure.

    Args:
        root_path: Root directory to start searching from
        recursive: Whether to search recursively in subdirectories
        max_depth: Maximum depth to search (None for unlimited)

    Returns:
        List of Paths to Git repository directories
    """
    if not root_path.exists():
        logger.warning(f"Root path does not exist: {root_path}")
        return []

    if not root_path.is_dir():
        logger.warning(f"Root path is not a directory: {root_path}")
        return []

    repositories = []

    # Check if the root path itself is a repository
    if is_git_repository(root_path):
        repositories.append(root_path)

    if recursive:
        # Recursively find all .git directories
        pattern = "**/.git" if max_depth is None else f"{'*/' * max_depth}.git"

        try:
            for git_dir in root_path.glob(pattern):
                if git_dir.is_dir():
                    parent_repo = git_dir.parent
                    if parent_repo not in repositories:
                        repositories.append(parent_repo)
        except ValueError:
            # Handle invalid glob patterns (e.g., max_depth too large)
            logger.warning(
                f"Invalid search pattern for max_depth={max_depth}, falling back to recursive search"
            )
            for git_dir in root_path.rglob(".git"):
                if git_dir.is_dir():
                    parent_repo = git_dir.parent
                    if parent_repo not in repositories:
                        repositories.append(parent_repo)
    else:
        # Only check immediate subdirectories
        for item in root_path.iterdir():
            if item.is_dir() and is_git_repository(item) and item not in repositories:
                repositories.append(item)

    logger.debug(f"Found {len(repositories)} repositories in {root_path}")
    return repositories


def find_repositories_by_pattern(
    root_path: Path,
    name_pattern: str = None,
    organization_pattern: str = None,
    recursive: bool = True,
) -> list[Path]:
    """
    Find repositories matching specific patterns.

    Args:
        root_path: Root directory to search
        name_pattern: Pattern to match repository names (fnmatch style)
        organization_pattern: Pattern to match organization names (directory names)
        recursive: Whether to search recursively

    Returns:
        List of Paths to matching repositories
    """
    import fnmatch

    all_repos = find_repositories_in_directory(root_path, recursive)

    if not name_pattern and not organization_pattern:
        return all_repos

    filtered_repos = []

    for repo_path in all_repos:
        repo_name = repo_path.name

        # Check repository name pattern
        if name_pattern and not fnmatch.fnmatch(repo_name, name_pattern):
            continue

        # Check organization pattern (parent directory name)
        if organization_pattern:
            org_name = repo_path.parent.name
            if not fnmatch.fnmatch(org_name, organization_pattern):
                continue

        filtered_repos.append(repo_path)

    logger.debug(
        f"Filtered {len(all_repos)} repositories to {len(filtered_repos)} matching pattern"
    )
    return filtered_repos

"""Git module for mgit CLI tool."""

from mgit.git.manager import GitManager
from mgit.git.utils import (
    build_repo_path,
    embed_pat_in_url,
    get_repo_components,
    sanitize_path_segment,
    sanitize_repo_name,
)

__all__ = [
    "GitManager",
    "embed_pat_in_url",
    "sanitize_repo_name",
    "build_repo_path",
    "sanitize_path_segment",
    "get_repo_components",
]

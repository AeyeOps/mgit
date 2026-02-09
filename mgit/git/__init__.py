"""Git module for mgit CLI tool."""

from mgit.git.manager import GitManager, sanitize_url
from mgit.git.utils import (
    build_repo_path,
    embed_pat_in_url,
    extract_repo_name,
    get_repo_components,
    resolve_local_repo_path,
    sanitize_path_segment,
    sanitize_repo_name,
)

__all__ = [
    "GitManager",
    "build_repo_path",
    "embed_pat_in_url",
    "extract_repo_name",
    "get_repo_components",
    "resolve_local_repo_path",
    "sanitize_path_segment",
    "sanitize_repo_name",
    "sanitize_url",
]

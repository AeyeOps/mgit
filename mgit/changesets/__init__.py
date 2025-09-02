"""
Changeset persistence package for mgit.

Provides functionality for storing and retrieving repository change information
with reliable YAML-based persistence and data integrity validation.
"""

from .models import FileChange, CommitInfo, RepositoryChangeset, ChangesetCollection

from .storage import (
    ChangesetStorage,
    ChangesetStorageError,
    ChangesetValidationError,
    save_repository_changeset,
    load_repository_changeset,
)

__all__ = [
    "FileChange",
    "CommitInfo",
    "RepositoryChangeset",
    "ChangesetCollection",
    "ChangesetStorage",
    "ChangesetStorageError",
    "ChangesetValidationError",
    "save_repository_changeset",
    "load_repository_changeset",
]

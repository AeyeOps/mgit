"""
YAML-based changeset persistence engine.

Provides reliable storage and retrieval of repository changesets with
proper error handling, atomic operations, and data integrity validation.
"""

import logging
import shutil
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from mgit.changesets.models import (
    ChangesetCollection,
    CommitInfo,
    FileChange,
    RepositoryChangeset,
)

logger = logging.getLogger(__name__)


class ChangesetStorageError(Exception):
    """Base exception for changeset storage operations."""

    pass


class ChangesetValidationError(ChangesetStorageError):
    """Raised when changeset data validation fails."""

    pass


class ChangesetStorage:
    """
    YAML-based storage engine for repository changesets.

    Provides atomic operations, data validation, and automatic backup
    for reliable changeset persistence.
    """

    def __init__(self, storage_dir: Path = None):
        """
        Initialize changeset storage.

        Args:
            storage_dir: Directory to store changeset files.
                        Defaults to ~/.config/mgit/changesets/
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".config" / "mgit" / "changesets"

        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Set secure permissions on storage directory
        self.storage_dir.chmod(0o700)

        logger.debug(f"Changeset storage initialized at: {self.storage_dir}")

    def save_changeset_collection(
        self, collection: ChangesetCollection, collection_name: str | None = None
    ) -> Path:
        """
        Save a changeset collection to YAML file with atomic operation.

        Args:
            collection: ChangesetCollection to save
            collection_name: Optional custom name for the collection file

        Returns:
            Path to the saved file

        Raises:
            ChangesetStorageError: If save operation fails
        """
        try:
            # Determine filename
            if collection_name:
                filename = f"{collection_name}.yaml"
            else:
                # Use collection name or generate from timestamp
                safe_name = self._sanitize_filename(collection.name)
                filename = f"{safe_name}.yaml"

            file_path = self.storage_dir / filename
            temp_path = self.storage_dir / f"{filename}.tmp"
            backup_path = self.storage_dir / f"{filename}.backup"

            # Validate collection before saving
            self._validate_changeset_collection(collection)

            # Convert to dictionary for YAML serialization
            collection_dict = self._collection_to_dict(collection)

            # Atomic write: write to temp file first
            with temp_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(
                    collection_dict,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    indent=2,
                )

            # Create backup of existing file if it exists
            if file_path.exists():
                shutil.copy2(file_path, backup_path)

            # Atomic rename - this should be atomic on most filesystems
            temp_path.rename(file_path)

            # Clean up backup after successful write
            if backup_path.exists():
                backup_path.unlink()

            logger.info(f"Saved changeset collection to: {file_path}")
            return file_path

        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()

            logger.error(f"Failed to save changeset collection: {e}")
            raise ChangesetStorageError(f"Save operation failed: {e}") from e

    def load_changeset_collection(
        self, collection_name: str
    ) -> ChangesetCollection | None:
        """
        Load a changeset collection from YAML file.

        Args:
            collection_name: Name of the collection to load

        Returns:
            ChangesetCollection if found, None otherwise

        Raises:
            ChangesetStorageError: If load operation fails
        """
        try:
            safe_name = self._sanitize_filename(collection_name)
            file_path = self.storage_dir / f"{safe_name}.yaml"

            if not file_path.exists():
                logger.debug(f"Changeset collection not found: {collection_name}")
                return None

            with file_path.open("r", encoding="utf-8") as f:
                collection_dict = yaml.safe_load(f)

            if not collection_dict:
                logger.warning(f"Empty changeset collection: {collection_name}")
                return None

            # Convert dictionary back to ChangesetCollection
            collection = self._dict_to_collection(collection_dict)

            # Validate loaded data
            self._validate_changeset_collection(collection)

            logger.debug(f"Loaded changeset collection: {collection_name}")
            return collection

        except Exception as e:
            logger.error(f"Failed to load changeset collection {collection_name}: {e}")
            raise ChangesetStorageError(f"Load operation failed: {e}") from e

    def list_changeset_collections(self) -> list[str]:
        """
        List available changeset collection names.

        Returns:
            List of collection names (without .yaml extension)
        """
        try:
            collection_files = self.storage_dir.glob("*.yaml")
            collection_names = [f.stem for f in collection_files if f.is_file()]
            return sorted(collection_names)

        except Exception as e:
            logger.error(f"Failed to list changeset collections: {e}")
            return []

    def delete_changeset_collection(self, collection_name: str) -> bool:
        """
        Delete a changeset collection file.

        Args:
            collection_name: Name of collection to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            ChangesetStorageError: If delete operation fails
        """
        try:
            safe_name = self._sanitize_filename(collection_name)
            file_path = self.storage_dir / f"{safe_name}.yaml"

            if not file_path.exists():
                return False

            # Create backup before deletion
            backup_path = self.storage_dir / f"{safe_name}.deleted.backup"
            shutil.copy2(file_path, backup_path)

            # Delete the file
            file_path.unlink()

            logger.info(f"Deleted changeset collection: {collection_name}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to delete changeset collection {collection_name}: {e}"
            )
            raise ChangesetStorageError(f"Delete operation failed: {e}") from e

    def get_collection_metadata(self, collection_name: str) -> dict[str, Any] | None:
        """
        Get metadata for a collection without loading full data.

        Args:
            collection_name: Name of collection

        Returns:
            Dictionary with metadata or None if not found
        """
        try:
            safe_name = self._sanitize_filename(collection_name)
            file_path = self.storage_dir / f"{safe_name}.yaml"

            if not file_path.exists():
                return None

            # Load just the top level to get metadata
            with file_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                return None

            return {
                "name": data.get("name"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "repository_count": len(data.get("repositories", {})),
                "file_size_bytes": file_path.stat().st_size,
                "file_modified": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat(),
            }

        except Exception as e:
            logger.debug(
                f"Failed to get collection metadata for {collection_name}: {e}"
            )
            return None

    @contextmanager
    def atomic_update(self, collection_name: str):
        """
        Context manager for atomic collection updates.

        Usage:
            with storage.atomic_update("my-collection") as collection:
                collection.add_repository(new_changeset)
                # Changes are automatically saved on successful exit
        """
        collection = self.load_changeset_collection(collection_name)
        if collection is None:
            collection = ChangesetCollection(
                name=collection_name,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )

        try:
            yield collection
            # Save changes if no exception occurred
            self.save_changeset_collection(collection, collection_name)

        except Exception as e:
            logger.error(f"Atomic update failed for {collection_name}: {e}")
            raise

    def _collection_to_dict(self, collection: ChangesetCollection) -> dict[str, Any]:
        """Convert ChangesetCollection to dictionary for YAML serialization."""
        collection_dict = asdict(collection)

        # Convert repository changesets
        repositories_dict = {}
        for repo_key, changeset in collection.repositories.items():
            repositories_dict[repo_key] = asdict(changeset)

        collection_dict["repositories"] = repositories_dict
        return collection_dict

    def _dict_to_collection(self, data: dict[str, Any]) -> ChangesetCollection:
        """Convert dictionary from YAML to ChangesetCollection."""
        repositories = {}

        # Convert repositories dictionary back to objects
        for repo_key, repo_data in data.get("repositories", {}).items():
            # Convert file changes
            uncommitted_files = [
                FileChange(**file_data)
                for file_data in repo_data.get("uncommitted_files", [])
            ]

            # Convert commit info
            recent_commits = [
                CommitInfo(**commit_data)
                for commit_data in repo_data.get("recent_commits", [])
            ]

            # Create repository changeset
            repo_data["uncommitted_files"] = uncommitted_files
            repo_data["recent_commits"] = recent_commits

            repositories[repo_key] = RepositoryChangeset(**repo_data)

        # Create collection
        collection_data = data.copy()
        collection_data["repositories"] = repositories

        return ChangesetCollection(**collection_data)

    def _validate_changeset_collection(self, collection: ChangesetCollection) -> None:
        """
        Validate changeset collection data integrity.

        Raises:
            ChangesetValidationError: If validation fails
        """
        try:
            if not collection.name:
                raise ChangesetValidationError("Collection name cannot be empty")

            if not collection.created_at:
                raise ChangesetValidationError("Collection created_at cannot be empty")

            # Validate each repository changeset
            for repo_key, changeset in collection.repositories.items():
                if not changeset.repository_path:
                    raise ChangesetValidationError(
                        f"Repository path empty for key: {repo_key}"
                    )

                if changeset.repository_key != repo_key:
                    raise ChangesetValidationError(
                        f"Repository key mismatch: {repo_key}"
                    )

                # Validate file changes
                for file_change in changeset.uncommitted_files:
                    if not file_change.filename:
                        raise ChangesetValidationError(
                            "File change filename cannot be empty"
                        )

                # Validate commits
                for commit in changeset.recent_commits:
                    if not commit.hash:
                        raise ChangesetValidationError("Commit hash cannot be empty")

        except Exception as e:
            raise ChangesetValidationError(f"Validation failed: {e}") from e

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize collection name for safe filename usage."""
        # Replace unsafe characters with underscores
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        sanitized = "".join(c if c in safe_chars else "_" for c in name)

        # Ensure it's not empty and not too long
        if not sanitized:
            sanitized = "unnamed"

        if len(sanitized) > 100:
            sanitized = sanitized[:100]

        return sanitized


# Convenience functions for common operations
def save_repository_changeset(
    changeset: RepositoryChangeset,
    collection_name: str = "default",
    storage_dir: Path | None = None,
) -> None:
    """
    Convenience function to save a single repository changeset.

    Args:
        changeset: Repository changeset to save
        collection_name: Name of collection to save to
        storage_dir: Optional custom storage directory
    """
    storage = ChangesetStorage(storage_dir)

    with storage.atomic_update(collection_name) as collection:
        collection.add_repository(changeset)


def load_repository_changeset(
    repository_path: str,
    collection_name: str = "default",
    storage_dir: Path | None = None,
) -> RepositoryChangeset | None:
    """
    Convenience function to load a single repository changeset.

    Args:
        repository_path: Path to repository
        collection_name: Name of collection to load from
        storage_dir: Optional custom storage directory

    Returns:
        RepositoryChangeset if found, None otherwise
    """
    storage = ChangesetStorage(storage_dir)
    collection = storage.load_changeset_collection(collection_name)

    if collection:
        return collection.get_repository(repository_path)

    return None

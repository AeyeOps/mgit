"""
Data models for changeset persistence and change tracking.

Provides structured data models for storing repository change information
with proper serialization support and data integrity validation.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Forward reference for EmbeddedContent (imported at end to avoid circular imports)
EmbeddedContent = Any


@dataclass
class FileChange:
    """Represents a single file change within a repository."""

    filename: str
    change_type: str  # added, modified, deleted, renamed, untracked
    index_status: str
    worktree_status: str
    size_bytes: int | None = None
    content_hash: str | None = None  # SHA-256 of file content
    embedded_content: EmbeddedContent | None = None  # Smart content embedding

    def __post_init__(self):
        """Validate change type after initialization."""
        valid_types = {
            "added",
            "modified",
            "deleted",
            "renamed",
            "copied",
            "untracked",
            "unknown",
        }
        if self.change_type not in valid_types:
            raise ValueError(f"Invalid change_type: {self.change_type}")

    @property
    def has_content(self) -> bool:
        """Check if file change has embedded content."""
        return (
            self.embedded_content is not None
            and self.embedded_content.content is not None
        )

    @property
    def content_strategy(self) -> str | None:
        """Get the content embedding strategy used."""
        return self.embedded_content.strategy.value if self.embedded_content else None


@dataclass
class CommitInfo:
    """Represents commit information."""

    hash: str
    author_name: str
    author_email: str
    date: str
    message: str

    def __post_init__(self):
        """Validate commit hash format."""
        if not self.hash or len(self.hash) < 7:
            raise ValueError(f"Invalid commit hash: {self.hash}")


@dataclass
class RepositoryChangeset:
    """Complete changeset information for a single repository."""

    repository_path: str
    repository_name: str
    timestamp: str
    has_uncommitted_changes: bool
    current_branch: str | None
    git_status: str  # clean, dirty, error
    uncommitted_files: list[FileChange] = field(default_factory=list)
    recent_commits: list[CommitInfo] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    content_embedding_stats: dict[str, Any] | None = (
        None  # Content embedding statistics
    )

    @property
    def repository_key(self) -> str:
        """Generate a unique key for this repository based on its path."""
        return hashlib.sha256(self.repository_path.encode("utf-8")).hexdigest()[:16]

    @property
    def is_clean(self) -> bool:
        """Check if repository is in clean state."""
        return self.git_status == "clean" and not self.has_uncommitted_changes

    @property
    def change_summary(self) -> dict[str, int]:
        """Generate summary of changes by type."""
        summary = {}
        for file_change in self.uncommitted_files:
            change_type = file_change.change_type
            summary[change_type] = summary.get(change_type, 0) + 1
        return summary

    @property
    def files_with_content(self) -> int:
        """Count files with embedded content."""
        return sum(1 for f in self.uncommitted_files if f.has_content)

    @property
    def content_strategies_used(self) -> dict[str, int]:
        """Get count of content strategies used."""
        strategies = {}
        for file_change in self.uncommitted_files:
            if file_change.embedded_content:
                strategy = file_change.embedded_content.strategy.value
                strategies[strategy] = strategies.get(strategy, 0) + 1
        return strategies

    @property
    def total_embedded_content_size(self) -> int:
        """Get total size of embedded content in bytes."""
        total_size = 0
        for file_change in self.uncommitted_files:
            if file_change.embedded_content and file_change.embedded_content.content:
                total_size += len(
                    file_change.embedded_content.content.encode(
                        "utf-8", errors="ignore"
                    )
                )
        return total_size


@dataclass
class ChangesetCollection:
    """Collection of repository changesets with metadata."""

    name: str
    created_at: str
    updated_at: str
    repositories: dict[str, RepositoryChangeset] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_repository(self, changeset: RepositoryChangeset) -> None:
        """Add or update a repository changeset."""
        self.repositories[changeset.repository_key] = changeset
        self.updated_at = datetime.now().isoformat()

    def get_repository(self, repo_path: str) -> RepositoryChangeset | None:
        """Get changeset for a specific repository path."""
        repo_key = hashlib.sha256(repo_path.encode("utf-8")).hexdigest()[:16]
        return self.repositories.get(repo_key)

    def remove_repository(self, repo_path: str) -> bool:
        """Remove a repository from the collection."""
        repo_key = hashlib.sha256(repo_path.encode("utf-8")).hexdigest()[:16]
        if repo_key in self.repositories:
            del self.repositories[repo_key]
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    @property
    def repository_count(self) -> int:
        """Get total number of repositories in collection."""
        return len(self.repositories)

    @property
    def dirty_repository_count(self) -> int:
        """Get number of repositories with uncommitted changes."""
        return sum(1 for repo in self.repositories.values() if not repo.is_clean)

    @property
    def error_repository_count(self) -> int:
        """Get number of repositories with errors."""
        return sum(
            1 for repo in self.repositories.values() if repo.git_status == "error"
        )


# Import EmbeddedContent after class definitions to avoid circular imports
try:
    from mgit.content.embedding import EmbeddedContent
except ImportError:
    # Fallback if content embedding is not available
    EmbeddedContent = Any

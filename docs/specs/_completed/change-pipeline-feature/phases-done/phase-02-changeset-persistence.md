# Phase 2: Changeset Persistence

## Summary
Implement persistent changeset storage using YAML-based state tracking to enable incremental diff operations, change history, and resumable batch processing with proper error recovery.

## Effort Estimate
4-5 hours

## Dependencies
- Phase 1: Basic change detection must be implemented first

## Implementation Details

### Files to Create
- `mgit/changesets/storage.py` - YAML-based changeset persistence engine
- `mgit/changesets/models.py` - Data models for changesets and change tracking
- `mgit/changesets/__init__.py` - Package initialization

### Files to Modify
- `mgit/commands/diff.py` - Add changeset persistence integration
- `mgit/__main__.py` - Add changeset-related command options

### Key Changes

#### 1. Create Changeset Data Models (`mgit/changesets/models.py`)

```python
"""
Data models for changeset persistence and change tracking.

Provides structured data models for storing repository change information
with proper serialization support and data integrity validation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from pathlib import Path
import hashlib

@dataclass
class FileChange:
    """Represents a single file change within a repository."""
    filename: str
    change_type: str  # added, modified, deleted, renamed, untracked
    index_status: str
    worktree_status: str
    size_bytes: Optional[int] = None
    content_hash: Optional[str] = None  # SHA-256 of file content
    
    def __post_init__(self):
        """Validate change type after initialization."""
        valid_types = {'added', 'modified', 'deleted', 'renamed', 'copied', 'untracked', 'unknown'}
        if self.change_type not in valid_types:
            raise ValueError(f"Invalid change_type: {self.change_type}")

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
    current_branch: Optional[str]
    git_status: str  # clean, dirty, error
    uncommitted_files: List[FileChange] = field(default_factory=list)
    recent_commits: List[CommitInfo] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def repository_key(self) -> str:
        """Generate a unique key for this repository based on its path."""
        return hashlib.sha256(self.repository_path.encode('utf-8')).hexdigest()[:16]
    
    @property
    def is_clean(self) -> bool:
        """Check if repository is in clean state."""
        return self.git_status == "clean" and not self.has_uncommitted_changes
    
    @property 
    def change_summary(self) -> Dict[str, int]:
        """Generate summary of changes by type."""
        summary = {}
        for file_change in self.uncommitted_files:
            change_type = file_change.change_type
            summary[change_type] = summary.get(change_type, 0) + 1
        return summary

@dataclass
class ChangesetCollection:
    """Collection of repository changesets with metadata."""
    name: str
    created_at: str
    updated_at: str
    repositories: Dict[str, RepositoryChangeset] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_repository(self, changeset: RepositoryChangeset) -> None:
        """Add or update a repository changeset."""
        self.repositories[changeset.repository_key] = changeset
        self.updated_at = datetime.now().isoformat()
    
    def get_repository(self, repo_path: str) -> Optional[RepositoryChangeset]:
        """Get changeset for a specific repository path."""
        repo_key = hashlib.sha256(repo_path.encode('utf-8')).hexdigest()[:16]
        return self.repositories.get(repo_key)
    
    def remove_repository(self, repo_path: str) -> bool:
        """Remove a repository from the collection."""
        repo_key = hashlib.sha256(repo_path.encode('utf-8')).hexdigest()[:16]
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
        return sum(1 for repo in self.repositories.values() if repo.git_status == "error")
```

#### 2. Create Changeset Storage Engine (`mgit/changesets/storage.py`)

```python
"""
YAML-based changeset persistence engine.

Provides reliable storage and retrieval of repository changesets with
proper error handling, atomic operations, and data integrity validation.
"""

import logging
import yaml
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import asdict, fields
from contextlib import contextmanager

from mgit.changesets.models import ChangesetCollection, RepositoryChangeset, FileChange, CommitInfo

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
            storage_dir = Path.home() / '.config' / 'mgit' / 'changesets'
        
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Set secure permissions on storage directory
        self.storage_dir.chmod(0o700)
        
        logger.debug(f"Changeset storage initialized at: {self.storage_dir}")
    
    def save_changeset_collection(
        self, 
        collection: ChangesetCollection,
        collection_name: Optional[str] = None
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
            with temp_path.open('w', encoding='utf-8') as f:
                yaml.safe_dump(
                    collection_dict,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    indent=2
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
    
    def load_changeset_collection(self, collection_name: str) -> Optional[ChangesetCollection]:
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
            
            with file_path.open('r', encoding='utf-8') as f:
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
    
    def list_changeset_collections(self) -> List[str]:
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
            logger.error(f"Failed to delete changeset collection {collection_name}: {e}")
            raise ChangesetStorageError(f"Delete operation failed: {e}") from e
    
    def get_collection_metadata(self, collection_name: str) -> Optional[Dict[str, Any]]:
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
            with file_path.open('r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return None
            
            return {
                'name': data.get('name'),
                'created_at': data.get('created_at'),
                'updated_at': data.get('updated_at'),
                'repository_count': len(data.get('repositories', {})),
                'file_size_bytes': file_path.stat().st_size,
                'file_modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }
            
        except Exception as e:
            logger.debug(f"Failed to get collection metadata for {collection_name}: {e}")
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
                updated_at=datetime.now().isoformat()
            )
        
        try:
            yield collection
            # Save changes if no exception occurred
            self.save_changeset_collection(collection, collection_name)
            
        except Exception as e:
            logger.error(f"Atomic update failed for {collection_name}: {e}")
            raise
    
    def _collection_to_dict(self, collection: ChangesetCollection) -> Dict[str, Any]:
        """Convert ChangesetCollection to dictionary for YAML serialization."""
        collection_dict = asdict(collection)
        
        # Convert repository changesets
        repositories_dict = {}
        for repo_key, changeset in collection.repositories.items():
            repositories_dict[repo_key] = asdict(changeset)
        
        collection_dict['repositories'] = repositories_dict
        return collection_dict
    
    def _dict_to_collection(self, data: Dict[str, Any]) -> ChangesetCollection:
        """Convert dictionary from YAML to ChangesetCollection."""
        repositories = {}
        
        # Convert repositories dictionary back to objects
        for repo_key, repo_data in data.get('repositories', {}).items():
            # Convert file changes
            uncommitted_files = [
                FileChange(**file_data) 
                for file_data in repo_data.get('uncommitted_files', [])
            ]
            
            # Convert commit info
            recent_commits = [
                CommitInfo(**commit_data)
                for commit_data in repo_data.get('recent_commits', [])
            ]
            
            # Create repository changeset
            repo_data['uncommitted_files'] = uncommitted_files
            repo_data['recent_commits'] = recent_commits
            
            repositories[repo_key] = RepositoryChangeset(**repo_data)
        
        # Create collection
        collection_data = data.copy()
        collection_data['repositories'] = repositories
        
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
                    raise ChangesetValidationError(f"Repository path empty for key: {repo_key}")
                
                if changeset.repository_key != repo_key:
                    raise ChangesetValidationError(f"Repository key mismatch: {repo_key}")
                
                # Validate file changes
                for file_change in changeset.uncommitted_files:
                    if not file_change.filename:
                        raise ChangesetValidationError("File change filename cannot be empty")
                
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
        sanitized = ''.join(c if c in safe_chars else '_' for c in name)
        
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
    storage_dir: Optional[Path] = None
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
    storage_dir: Optional[Path] = None
) -> Optional[RepositoryChangeset]:
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
```

#### 3. Create Package Initialization (`mgit/changesets/__init__.py`)

```python
"""
Changeset persistence package for mgit.

Provides functionality for storing and retrieving repository change information
with reliable YAML-based persistence and data integrity validation.
"""

from .models import (
    FileChange,
    CommitInfo, 
    RepositoryChangeset,
    ChangesetCollection
)

from .storage import (
    ChangesetStorage,
    ChangesetStorageError,
    ChangesetValidationError,
    save_repository_changeset,
    load_repository_changeset
)

__all__ = [
    'FileChange',
    'CommitInfo',
    'RepositoryChangeset', 
    'ChangesetCollection',
    'ChangesetStorage',
    'ChangesetStorageError',
    'ChangesetValidationError',
    'save_repository_changeset',
    'load_repository_changeset'
]
```

#### 4. Update Diff Command with Persistence (`mgit/commands/diff.py`)

Add changeset persistence integration to the existing diff command:

```python
# Add these imports at the top
from mgit.changesets.models import RepositoryChangeset, FileChange, CommitInfo
from mgit.changesets.storage import ChangesetStorage, save_repository_changeset

# Update the execute_diff_command function to include persistence options
def execute_diff_command(
    path: Path,
    output: Optional[Path],
    recursive: bool,
    concurrency: int,
    verbose: bool,
    save_changeset: bool = False,
    changeset_name: str = "default",
    incremental: bool = False
) -> None:
    """
    Execute the diff command with optional changeset persistence.
    
    Args:
        path: Path to repository or directory to scan
        output: Optional output file path  
        recursive: Whether to scan recursively for repositories
        concurrency: Number of concurrent operations
        verbose: Whether to enable verbose output
        save_changeset: Whether to save changesets to persistent storage
        changeset_name: Name of changeset collection to use
        incremental: Whether to only report changes since last save
    """
    if verbose:
        logging.getLogger("mgit").setLevel(logging.DEBUG)
        console.print(f"[blue]Starting change detection on: {path}[/blue]")
    
    # Initialize changeset storage if needed
    storage = None
    if save_changeset or incremental:
        storage = ChangesetStorage()
        if verbose:
            console.print(f"[blue]Using changeset storage: {changeset_name}[/blue]")
    
    try:
        # Discover repositories
        if path.is_file() or (path / '.git').exists():
            repositories = [path]
        elif recursive:
            repositories = find_repositories_in_directory(path, recursive=True)
        else:
            repositories = find_repositories_in_directory(path, recursive=False)
        
        if not repositories:
            console.print("[yellow]No repositories found in the specified path.[/yellow]")
            return
        
        if verbose:
            console.print(f"[blue]Found {len(repositories)} repositories to analyze[/blue]")
        
        # Load previous changeset for incremental processing
        previous_collection = None
        if incremental and storage:
            previous_collection = storage.load_changeset_collection(changeset_name)
            if verbose and previous_collection:
                console.print(f"[blue]Loaded previous changeset with {previous_collection.repository_count} repositories[/blue]")
        
        # Process repositories
        processor = DiffProcessor(concurrency=concurrency)
        
        with Progress() as progress:
            task = progress.add_task("[green]Detecting changes...", total=len(repositories))
            
            changes = asyncio.run(
                processor.process_repositories(repositories, progress, task)
            )
        
        # Filter for incremental changes if requested
        if incremental and previous_collection:
            changes = _filter_incremental_changes(changes, previous_collection, verbose)
            if verbose:
                console.print(f"[blue]Found {len(changes)} repositories with changes since last scan[/blue]")
        
        # Save to changeset storage if requested
        if save_changeset and storage:
            _save_to_changeset_storage(changes, storage, changeset_name, verbose)
        
        # Output results
        output_stream = _get_output_stream(output)
        try:
            _write_changes_jsonl(changes, output_stream, verbose)
        finally:
            if output_stream != sys.stdout:
                output_stream.close()
        
        if verbose:
            console.print(f"[green]Change detection completed. Processed {len(changes)} repositories.[/green]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error during change detection: {e}[/red]")
        logger.error(f"Change detection failed: {e}")
        raise typer.Exit(1)

def _convert_to_repository_changeset(change: RepositoryChange) -> RepositoryChangeset:
    """Convert RepositoryChange to RepositoryChangeset for storage."""
    
    # Convert file changes
    file_changes = []
    for file_data in change.uncommitted_files:
        file_changes.append(FileChange(
            filename=file_data['filename'],
            change_type=file_data['change_type'],
            index_status=file_data['index_status'],
            worktree_status=file_data['worktree_status']
        ))
    
    # Convert commit info
    commits = []
    for commit_data in change.recent_commits:
        commits.append(CommitInfo(
            hash=commit_data['hash'],
            author_name=commit_data['author_name'],
            author_email=commit_data['author_email'],
            date=commit_data['date'],
            message=commit_data['message']
        ))
    
    return RepositoryChangeset(
        repository_path=change.repository_path,
        repository_name=change.repository_name,
        timestamp=change.timestamp,
        has_uncommitted_changes=change.has_uncommitted_changes,
        current_branch=change.current_branch,
        git_status=change.git_status,
        uncommitted_files=file_changes,
        recent_commits=commits,
        error=change.error
    )

def _save_to_changeset_storage(
    changes: List[RepositoryChange],
    storage: ChangesetStorage,
    collection_name: str,
    verbose: bool
) -> None:
    """Save repository changes to persistent storage."""
    try:
        with storage.atomic_update(collection_name) as collection:
            for change in changes:
                changeset = _convert_to_repository_changeset(change)
                collection.add_repository(changeset)
        
        if verbose:
            console.print(f"[green]Saved {len(changes)} changesets to collection: {collection_name}[/green]")
            
    except Exception as e:
        logger.error(f"Failed to save changesets: {e}")
        if verbose:
            console.print(f"[red]Failed to save changesets: {e}[/red]")

def _filter_incremental_changes(
    current_changes: List[RepositoryChange],
    previous_collection: ChangesetCollection,
    verbose: bool
) -> List[RepositoryChange]:
    """Filter changes to only include repositories with differences since last scan."""
    incremental_changes = []
    
    for change in current_changes:
        previous_changeset = previous_collection.get_repository(change.repository_path)
        
        if previous_changeset is None:
            # New repository - include it
            incremental_changes.append(change)
            if verbose:
                console.print(f"[yellow]New repository: {change.repository_name}[/yellow]")
            continue
        
        # Check if there are meaningful differences
        if _has_meaningful_changes(change, previous_changeset):
            incremental_changes.append(change)
            if verbose:
                console.print(f"[yellow]Changed repository: {change.repository_name}[/yellow]")
    
    return incremental_changes

def _has_meaningful_changes(
    current: RepositoryChange,
    previous: RepositoryChangeset
) -> bool:
    """Check if current changeset has meaningful differences from previous."""
    
    # Different git status
    if current.git_status != previous.git_status:
        return True
    
    # Different uncommitted changes status
    if current.has_uncommitted_changes != previous.has_uncommitted_changes:
        return True
    
    # Different branch
    if current.current_branch != previous.current_branch:
        return True
    
    # Different number of uncommitted files
    if len(current.uncommitted_files) != len(previous.uncommitted_files):
        return True
    
    # Different recent commits (check latest commit hash)
    current_latest = current.recent_commits[0]['hash'] if current.recent_commits else None
    previous_latest = previous.recent_commits[0].hash if previous.recent_commits else None
    
    if current_latest != previous_latest:
        return True
    
    return False
```

#### 5. Update Main CLI to Support Changeset Options (`mgit/__main__.py`)

Update the diff command registration to include persistence options:

```python
@app.command(name="diff")
def diff_command(
    path: Path = typer.Argument(
        ".",
        help="Path to repository or directory containing repositories.",
        exists=True,
        resolve_path=True,
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o", 
        help="Output file for change data (JSONL format). If not specified, prints to stdout.",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="Recursively scan directories for repositories.",
    ),
    concurrency: int = typer.Option(
        5,
        "--concurrency", 
        "-c",
        help="Number of concurrent repository operations.",
        min=1,
        max=50,
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    save_changeset: bool = typer.Option(
        False,
        "--save-changeset",
        "-s",
        help="Save changesets to persistent storage for incremental processing.",
    ),
    changeset_name: str = typer.Option(
        "default",
        "--changeset-name",
        "-n",
        help="Name of changeset collection to use for storage.",
    ),
    incremental: bool = typer.Option(
        False,
        "--incremental",
        "-i", 
        help="Only report changes since last saved changeset.",
    ),
) -> None:
    """
    Detect changes in Git repositories with optional persistent storage.
    
    This command can save changesets for incremental processing, allowing
    you to track only new changes since the last scan.
    
    Examples:
      mgit diff . --save-changeset --changeset-name=daily-scan
      mgit diff . --incremental --changeset-name=daily-scan  
      mgit diff /repos --recursive --save-changeset --incremental
    """
    from mgit.commands.diff import execute_diff_command
    execute_diff_command(path, output, recursive, concurrency, verbose, save_changeset, changeset_name, incremental)
```

## Testing Strategy

### Unit Tests
Create `tests/unit/test_changeset_storage.py`:

```python
import pytest
import tempfile
import yaml
from pathlib import Path
from datetime import datetime

from mgit.changesets.storage import ChangesetStorage, ChangesetStorageError
from mgit.changesets.models import ChangesetCollection, RepositoryChangeset, FileChange, CommitInfo

class TestChangesetStorage:
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield ChangesetStorage(Path(temp_dir))
    
    @pytest.fixture
    def sample_collection(self):
        """Create sample changeset collection."""
        collection = ChangesetCollection(
            name="test-collection",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        changeset = RepositoryChangeset(
            repository_path="/test/repo",
            repository_name="test-repo", 
            timestamp=datetime.now().isoformat(),
            has_uncommitted_changes=True,
            current_branch="main",
            git_status="dirty",
            uncommitted_files=[
                FileChange(
                    filename="test.py",
                    change_type="modified",
                    index_status="M",
                    worktree_status=" "
                )
            ],
            recent_commits=[
                CommitInfo(
                    hash="abc123",
                    author_name="Test Author",
                    author_email="test@example.com", 
                    date="2024-01-01T12:00:00+00:00",
                    message="Test commit"
                )
            ]
        )
        
        collection.add_repository(changeset)
        return collection
    
    def test_save_and_load_collection(self, temp_storage, sample_collection):
        """Test saving and loading a changeset collection."""
        # Save collection
        saved_path = temp_storage.save_changeset_collection(sample_collection, "test")
        assert saved_path.exists()
        
        # Load collection
        loaded_collection = temp_storage.load_changeset_collection("test")
        assert loaded_collection is not None
        assert loaded_collection.name == sample_collection.name
        assert loaded_collection.repository_count == sample_collection.repository_count
    
    def test_atomic_update_context_manager(self, temp_storage):
        """Test atomic update context manager."""
        with temp_storage.atomic_update("atomic-test") as collection:
            changeset = RepositoryChangeset(
                repository_path="/test/atomic",
                repository_name="atomic-repo",
                timestamp=datetime.now().isoformat(),
                has_uncommitted_changes=False,
                current_branch="main",
                git_status="clean"
            )
            collection.add_repository(changeset)
        
        # Verify changes were saved
        loaded = temp_storage.load_changeset_collection("atomic-test") 
        assert loaded is not None
        assert loaded.repository_count == 1
    
    def test_list_collections(self, temp_storage, sample_collection):
        """Test listing available collections."""
        # Initially empty
        collections = temp_storage.list_changeset_collections()
        assert len(collections) == 0
        
        # Save some collections
        temp_storage.save_changeset_collection(sample_collection, "collection1")
        temp_storage.save_changeset_collection(sample_collection, "collection2")
        
        collections = temp_storage.list_changeset_collections()
        assert len(collections) == 2
        assert "collection1" in collections
        assert "collection2" in collections
    
    def test_delete_collection(self, temp_storage, sample_collection):
        """Test deleting a collection."""
        # Save collection
        temp_storage.save_changeset_collection(sample_collection, "to-delete")
        assert temp_storage.load_changeset_collection("to-delete") is not None
        
        # Delete collection
        result = temp_storage.delete_changeset_collection("to-delete")
        assert result is True
        
        # Verify it's gone
        assert temp_storage.load_changeset_collection("to-delete") is None
    
    def test_get_collection_metadata(self, temp_storage, sample_collection):
        """Test getting collection metadata."""
        temp_storage.save_changeset_collection(sample_collection, "metadata-test")
        
        metadata = temp_storage.get_collection_metadata("metadata-test")
        assert metadata is not None
        assert metadata['name'] == sample_collection.name
        assert metadata['repository_count'] == sample_collection.repository_count
        assert 'file_size_bytes' in metadata
        assert 'file_modified' in metadata

class TestChangesetModels:
    def test_repository_changeset_key_generation(self):
        """Test repository key generation."""
        changeset = RepositoryChangeset(
            repository_path="/unique/path/repo",
            repository_name="repo",
            timestamp=datetime.now().isoformat(),
            has_uncommitted_changes=False,
            current_branch="main",
            git_status="clean"
        )
        
        key1 = changeset.repository_key
        
        # Same path should generate same key
        changeset2 = RepositoryChangeset(
            repository_path="/unique/path/repo",
            repository_name="different-name", 
            timestamp=datetime.now().isoformat(),
            has_uncommitted_changes=True,
            current_branch="develop",
            git_status="dirty"
        )
        
        key2 = changeset2.repository_key
        assert key1 == key2
    
    def test_collection_repository_management(self):
        """Test adding/removing repositories from collection."""
        collection = ChangesetCollection(
            name="test",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        changeset = RepositoryChangeset(
            repository_path="/test/repo",
            repository_name="repo",
            timestamp=datetime.now().isoformat(), 
            has_uncommitted_changes=False,
            current_branch="main",
            git_status="clean"
        )
        
        # Add repository
        collection.add_repository(changeset)
        assert collection.repository_count == 1
        
        # Retrieve repository
        retrieved = collection.get_repository("/test/repo")
        assert retrieved is not None
        assert retrieved.repository_path == changeset.repository_path
        
        # Remove repository  
        removed = collection.remove_repository("/test/repo")
        assert removed is True
        assert collection.repository_count == 0
```

### Integration Tests
Add to `tests/integration/test_diff_persistence.py`:

```python
def test_diff_command_with_changeset_save():
    """Test diff command with changeset persistence."""
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        result = runner.invoke(app, [
            "diff",
            ".",
            "--save-changeset",
            "--changeset-name", "integration-test",
            "--verbose"
        ])
        
        assert result.exit_code == 0
        assert "Saved" in result.output

def test_diff_command_incremental_mode():
    """Test diff command incremental mode."""
    # Test implementation for incremental processing
    pass

def test_diff_command_changeset_storage_error_handling():
    """Test error handling when changeset storage fails."""
    # Test implementation for storage error scenarios
    pass
```

### Manual Verification Commands
```bash
# Test basic changeset saving
poetry run mgit diff . --save-changeset --changeset-name=test-save --verbose

# Test incremental mode (run twice to see difference)
poetry run mgit diff . --save-changeset --changeset-name=incremental-test --verbose
poetry run mgit diff . --incremental --changeset-name=incremental-test --verbose

# Test changeset storage directory creation
ls ~/.config/mgit/changesets/

# Test YAML format validation
cat ~/.config/mgit/changesets/test-save.yaml | head -20

# Test error recovery with invalid YAML
echo "invalid: yaml: content" > ~/.config/mgit/changesets/broken.yaml
poetry run mgit diff . --incremental --changeset-name=broken --verbose
```

## Success Criteria
- [ ] `mgit/changesets/` package created with storage, models, and init modules
- [ ] ChangesetStorage provides atomic YAML-based persistence with proper error handling  
- [ ] RepositoryChangeset and related models support data integrity validation
- [ ] Diff command accepts `--save-changeset`, `--changeset-name`, `--incremental` options
- [ ] Incremental mode correctly filters changes since last save
- [ ] Storage directory created with secure permissions (700)
- [ ] Atomic operations prevent data corruption during save failures
- [ ] YAML format is human-readable and validates correctly
- [ ] Unit tests achieve >90% coverage for new changeset functionality
- [ ] Integration tests verify end-to-end persistence behavior
- [ ] Manual verification commands execute successfully
- [ ] Error handling gracefully manages storage failures without data loss

## Rollback Plan
If issues arise:
1. Remove `--save-changeset`, `--changeset-name`, `--incremental` options from diff command in `__main__.py`
2. Revert changes to `mgit/commands/diff.py` (remove persistence integration)
3. Delete entire `mgit/changesets/` directory and package
4. Run `poetry run pytest` to ensure no regressions
5. Test that basic diff command still works without persistence options
6. Clean up any created changeset storage directories

## Notes  
- YAML format chosen for human-readability and editability over binary formats
- Atomic operations prevent data corruption during concurrent access or failures
- Repository keys use SHA-256 hash of path for consistent identification across renames
- Incremental mode compares meaningful changes (branch, commits, files) not just timestamps
- Storage directory uses secure permissions to protect potentially sensitive repository information
- Error handling ensures partial failures don't corrupt entire changeset collections
- Validation prevents invalid data from being persisted to storage
- Context manager pattern ensures reliable cleanup and atomic updates
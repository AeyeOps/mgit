# Phase 1: Basic Change Detection

## Summary
Implement basic change detection functionality by adding a new `diff` command that can detect file changes in repositories and output structured change information in JSONL format for further processing.

## Effort Estimate
3-4 hours

## Dependencies
None - This is the foundation phase

## Implementation Details

### Files to Create
- `mgit/commands/diff.py` - New diff command implementation

### Files to Modify  
- `mgit/__main__.py` - Add diff command registration at line 1290
- `mgit/git/manager.py` - Extend with diff_files() method

### Key Changes

#### 1. Add Diff Command Registration (`mgit/__main__.py`)

Insert at line 1290 (before status command):

```python
# -----------------------------------------------------------------------------
# diff Command  
# -----------------------------------------------------------------------------
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
) -> None:
    """
    Detect changes in Git repositories and output structured change information.
    
    This command scans repositories for uncommitted changes, recent commits,
    and repository metadata, outputting the results in JSONL format for
    further processing or analysis.
    
    Examples:
      mgit diff /path/to/repos --output changes.jsonl --recursive
      mgit diff . --verbose  
      mgit diff /single/repo --concurrency 1
    """
    from mgit.commands.diff import execute_diff_command
    execute_diff_command(path, output, recursive, concurrency, verbose)
```

#### 2. Create Diff Command Implementation (`mgit/commands/diff.py`)

```python
"""
Change detection command implementation.

Provides functionality to detect and report changes in Git repositories,
outputting structured data in JSONL format for pipeline processing.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, TextIO
from dataclasses import dataclass, asdict
from datetime import datetime

import typer
from rich.console import Console
from rich.progress import Progress, TaskID

from mgit.git.manager import GitManager
from mgit.utils.directory_scanner import find_repositories_in_directory

logger = logging.getLogger(__name__)
console = Console()

@dataclass
class RepositoryChange:
    """Represents change information for a single repository."""
    repository_path: str
    repository_name: str
    timestamp: str
    has_uncommitted_changes: bool
    uncommitted_files: List[Dict[str, Any]]
    recent_commits: List[Dict[str, Any]]
    current_branch: Optional[str]
    git_status: str
    error: Optional[str] = None

class DiffProcessor:
    """Processes repositories to detect and collect change information."""
    
    def __init__(self, concurrency: int = 5):
        self.git_manager = GitManager()
        self.concurrency = concurrency
        
    async def process_repositories(
        self, 
        repositories: List[Path], 
        progress: Optional[Progress] = None,
        task_id: Optional[TaskID] = None
    ) -> List[RepositoryChange]:
        """
        Process multiple repositories concurrently to detect changes.
        
        Args:
            repositories: List of repository paths to process
            progress: Optional progress bar instance
            task_id: Optional progress task ID
            
        Returns:
            List of RepositoryChange objects with detected changes
        """
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async def process_single_repo(repo_path: Path) -> RepositoryChange:
            async with semaphore:
                try:
                    change_data = await self._detect_repository_changes(repo_path)
                    if progress and task_id:
                        progress.advance(task_id)
                    return change_data
                except Exception as e:
                    logger.error(f"Error processing repository {repo_path}: {e}")
                    if progress and task_id:
                        progress.advance(task_id)
                    return RepositoryChange(
                        repository_path=str(repo_path),
                        repository_name=repo_path.name,
                        timestamp=datetime.now().isoformat(),
                        has_uncommitted_changes=False,
                        uncommitted_files=[],
                        recent_commits=[],
                        current_branch=None,
                        git_status="error",
                        error=str(e)
                    )
        
        tasks = [process_single_repo(repo) for repo in repositories]
        return await asyncio.gather(*tasks)
    
    async def _detect_repository_changes(self, repo_path: Path) -> RepositoryChange:
        """
        Detect changes in a single repository.
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            RepositoryChange object with detected change information
        """
        timestamp = datetime.now().isoformat()
        
        try:
            # Get basic repository information
            current_branch = await self.git_manager.get_current_branch(repo_path)
            
            # Get diff information using the new diff_files method
            diff_info = await self.git_manager.diff_files(repo_path)
            
            # Parse uncommitted files from git status
            uncommitted_files = []
            has_changes = diff_info.get('has_changes', False)
            
            if has_changes:
                # Convert git status output to structured format
                status_output = diff_info.get('status_output', '')
                uncommitted_files = self._parse_git_status(status_output)
            
            # Get recent commits (last 5)
            recent_commits = await self._get_recent_commits(repo_path, limit=5)
            
            return RepositoryChange(
                repository_path=str(repo_path),
                repository_name=repo_path.name,
                timestamp=timestamp,
                has_uncommitted_changes=has_changes,
                uncommitted_files=uncommitted_files,
                recent_commits=recent_commits,
                current_branch=current_branch,
                git_status="clean" if not has_changes else "dirty",
                error=None
            )
            
        except Exception as e:
            logger.debug(f"Repository {repo_path} change detection failed: {e}")
            return RepositoryChange(
                repository_path=str(repo_path),
                repository_name=repo_path.name,
                timestamp=timestamp,
                has_uncommitted_changes=False,
                uncommitted_files=[],
                recent_commits=[],
                current_branch=None,
                git_status="error",
                error=str(e)
            )
    
    def _parse_git_status(self, status_output: str) -> List[Dict[str, Any]]:
        """
        Parse git status output into structured file change information.
        
        Args:
            status_output: Raw git status --porcelain output
            
        Returns:
            List of file change dictionaries
        """
        files = []
        for line in status_output.strip().split('\n'):
            if not line:
                continue
                
            # Git status --porcelain format: XY filename
            if len(line) >= 3:
                index_status = line[0]
                worktree_status = line[1] 
                filename = line[3:]  # Skip the space
                
                files.append({
                    'filename': filename,
                    'index_status': index_status,
                    'worktree_status': worktree_status,
                    'change_type': self._interpret_git_status_codes(index_status, worktree_status)
                })
        
        return files
    
    def _interpret_git_status_codes(self, index: str, worktree: str) -> str:
        """Interpret git status codes into human-readable change types."""
        if index == 'A':
            return 'added'
        elif index == 'M':
            return 'modified'
        elif index == 'D':
            return 'deleted'
        elif index == 'R':
            return 'renamed'
        elif index == 'C':
            return 'copied'
        elif worktree == 'M':
            return 'modified'
        elif worktree == 'D':
            return 'deleted'
        elif index == '?' and worktree == '?':
            return 'untracked'
        else:
            return 'unknown'
    
    async def _get_recent_commits(self, repo_path: Path, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent commit information from the repository.
        
        Args:
            repo_path: Path to repository
            limit: Maximum number of commits to return
            
        Returns:
            List of commit information dictionaries
        """
        try:
            # Get recent commits using git log
            commits_info = await self.git_manager.get_recent_commits(repo_path, limit)
            return commits_info
        except Exception as e:
            logger.debug(f"Could not get recent commits for {repo_path}: {e}")
            return []

def execute_diff_command(
    path: Path,
    output: Optional[Path],
    recursive: bool,
    concurrency: int,
    verbose: bool
) -> None:
    """
    Execute the diff command with the provided parameters.
    
    Args:
        path: Path to repository or directory to scan
        output: Optional output file path  
        recursive: Whether to scan recursively for repositories
        concurrency: Number of concurrent operations
        verbose: Whether to enable verbose output
    """
    if verbose:
        logging.getLogger("mgit").setLevel(logging.DEBUG)
        console.print(f"[blue]Starting change detection on: {path}[/blue]")
    
    try:
        # Discover repositories
        if path.is_file() or (path / '.git').exists():
            # Single repository
            repositories = [path]
        elif recursive:
            # Recursive directory scan
            repositories = find_repositories_in_directory(path, recursive=True)
        else:
            # Single directory scan  
            repositories = find_repositories_in_directory(path, recursive=False)
        
        if not repositories:
            console.print("[yellow]No repositories found in the specified path.[/yellow]")
            return
        
        if verbose:
            console.print(f"[blue]Found {len(repositories)} repositories to analyze[/blue]")
        
        # Process repositories
        processor = DiffProcessor(concurrency=concurrency)
        
        with Progress() as progress:
            task = progress.add_task("[green]Detecting changes...", total=len(repositories))
            
            # Run async processing
            changes = asyncio.run(
                processor.process_repositories(repositories, progress, task)
            )
        
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

def _get_output_stream(output: Optional[Path]) -> TextIO:
    """Get the appropriate output stream for results."""
    if output:
        # Ensure output directory exists
        output.parent.mkdir(parents=True, exist_ok=True)
        return output.open('w', encoding='utf-8')
    else:
        return sys.stdout

def _write_changes_jsonl(changes: List[RepositoryChange], stream: TextIO, verbose: bool) -> None:
    """
    Write change data to output stream in JSONL format.
    
    Args:
        changes: List of repository changes to write
        stream: Output stream to write to
        verbose: Whether to log verbose information
    """
    written_count = 0
    error_count = 0
    
    for change in changes:
        try:
            # Convert dataclass to dict for JSON serialization
            change_dict = asdict(change)
            
            # Write as single line JSON
            json_line = json.dumps(change_dict, ensure_ascii=False, separators=(',', ':'))
            stream.write(json_line + '\n')
            stream.flush()
            
            written_count += 1
            
            if verbose and change.error:
                console.print(f"[yellow]Warning - {change.repository_name}: {change.error}[/yellow]")
                
        except Exception as e:
            error_count += 1
            logger.error(f"Error writing change data for {change.repository_path}: {e}")
    
    if verbose:
        console.print(f"[blue]Wrote {written_count} change records, {error_count} errors[/blue]")
```

#### 3. Extend Git Manager (`mgit/git/manager.py`)

Add these methods to the GitManager class:

```python
    async def diff_files(self, repo_dir: Path) -> Dict[str, Any]:
        """
        Get diff information for a repository including git status.
        
        Args:
            repo_dir: Path to the repository
            
        Returns:
            Dictionary with diff information including:
            - has_changes: bool indicating if there are uncommitted changes
            - status_output: raw git status --porcelain output
            - diff_output: raw git diff output (optional)
        """
        try:
            # Check for uncommitted changes using git status
            status_cmd = [self.GIT_EXECUTABLE, "status", "--porcelain"]
            status_result = await self._run_subprocess(
                status_cmd, 
                cwd=repo_dir, 
                capture_output=True
            )
            
            status_output = status_result.stdout.strip()
            has_changes = len(status_output) > 0
            
            return {
                'has_changes': has_changes,
                'status_output': status_output,
            }
            
        except subprocess.CalledProcessError as e:
            logger.debug(f"Git status failed in {repo_dir}: {e}")
            raise
        except Exception as e:
            logger.debug(f"Diff files operation failed in {repo_dir}: {e}")
            raise

    async def get_current_branch(self, repo_dir: Path) -> Optional[str]:
        """
        Get the current branch name for the repository.
        
        Args:
            repo_dir: Path to the repository
            
        Returns:
            Current branch name or None if detached HEAD or error
        """
        try:
            cmd = [self.GIT_EXECUTABLE, "branch", "--show-current"]
            result = await self._run_subprocess(
                cmd, 
                cwd=repo_dir, 
                capture_output=True
            )
            
            branch_name = result.stdout.strip()
            return branch_name if branch_name else None
            
        except subprocess.CalledProcessError:
            logger.debug(f"Could not get current branch for {repo_dir}")
            return None
        except Exception as e:
            logger.debug(f"Get current branch failed in {repo_dir}: {e}")
            return None

    async def get_recent_commits(self, repo_dir: Path, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent commit information from the repository.
        
        Args:
            repo_dir: Path to repository
            limit: Maximum number of commits to return
            
        Returns:
            List of commit information dictionaries
        """
        try:
            # Use git log with custom format for structured output
            format_str = "--format=%H|%an|%ae|%ai|%s"
            cmd = [
                self.GIT_EXECUTABLE, 
                "log", 
                f"-{limit}", 
                format_str,
                "--no-merges"
            ]
            
            result = await self._run_subprocess(
                cmd, 
                cwd=repo_dir, 
                capture_output=True
            )
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 4)
                    if len(parts) == 5:
                        commits.append({
                            'hash': parts[0],
                            'author_name': parts[1],
                            'author_email': parts[2],
                            'date': parts[3],
                            'message': parts[4]
                        })
            
            return commits
            
        except subprocess.CalledProcessError as e:
            logger.debug(f"Git log failed in {repo_dir}: {e}")
            return []
        except Exception as e:
            logger.debug(f"Get recent commits failed in {repo_dir}: {e}")
            return []
```

Also need to update the `_run_subprocess` method to support capturing output:

```python
    async def _run_subprocess(
        self, 
        cmd: list, 
        cwd: Path, 
        capture_output: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Run a subprocess command with proper error handling.
        
        Args:
            cmd: Command and arguments to run
            cwd: Working directory for the command
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            CompletedProcess result if capture_output=True
        """
        try:
            if capture_output:
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result
            else:
                # Original behavior for non-capturing calls
                subprocess.run(cmd, cwd=cwd, check=True)
                return None
                
        except subprocess.CalledProcessError as e:
            # Log the error with context
            cmd_str = ' '.join(cmd)
            logger.error(f"Command '{cmd_str}' failed in {cwd}: {e}")
            if capture_output and e.stdout:
                logger.debug(f"stdout: {e.stdout}")
            if capture_output and e.stderr:
                logger.debug(f"stderr: {e.stderr}")
            raise
        except Exception as e:
            cmd_str = ' '.join(cmd)
            logger.error(f"Unexpected error running '{cmd_str}' in {cwd}: {e}")
            raise
```

## Testing Strategy

### Unit Tests
Create `tests/unit/test_diff_command.py`:

```python
import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from mgit.commands.diff import DiffProcessor, RepositoryChange, _parse_git_status
from mgit.git.manager import GitManager

class TestDiffProcessor:
    @pytest.fixture
    def diff_processor(self):
        return DiffProcessor(concurrency=2)
    
    @pytest.fixture
    def mock_git_manager(self):
        mock = Mock(spec=GitManager)
        mock.get_current_branch = AsyncMock(return_value="main")
        mock.diff_files = AsyncMock(return_value={
            'has_changes': True,
            'status_output': 'M  test.py\n?? new_file.txt'
        })
        mock.get_recent_commits = AsyncMock(return_value=[
            {
                'hash': 'abc123',
                'author_name': 'Test Author', 
                'author_email': 'test@example.com',
                'date': '2024-01-01T12:00:00+00:00',
                'message': 'Test commit'
            }
        ])
        return mock
    
    @pytest.mark.asyncio
    async def test_detect_repository_changes_success(self, diff_processor, mock_git_manager):
        """Test successful change detection for a repository."""
        diff_processor.git_manager = mock_git_manager
        
        repo_path = Path("/test/repo")
        
        with patch('mgit.commands.diff.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T10:00:00"
            
            result = await diff_processor._detect_repository_changes(repo_path)
        
        assert result.repository_path == str(repo_path)
        assert result.repository_name == "repo"
        assert result.has_uncommitted_changes is True
        assert len(result.uncommitted_files) == 2
        assert result.current_branch == "main"
        assert result.git_status == "dirty"
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_detect_repository_changes_error(self, diff_processor, mock_git_manager):
        """Test change detection when git operations fail."""
        mock_git_manager.get_current_branch.side_effect = Exception("Git error")
        diff_processor.git_manager = mock_git_manager
        
        repo_path = Path("/test/repo")
        
        result = await diff_processor._detect_repository_changes(repo_path)
        
        assert result.error is not None
        assert result.git_status == "error"
        assert result.has_uncommitted_changes is False
    
    def test_parse_git_status_various_changes(self, diff_processor):
        """Test parsing various git status output formats."""
        status_output = """M  modified_file.py
A  added_file.py
D  deleted_file.py
?? untracked_file.py
R  old_name.py -> new_name.py"""
        
        files = diff_processor._parse_git_status(status_output)
        
        assert len(files) == 5
        assert files[0]['change_type'] == 'modified'
        assert files[1]['change_type'] == 'added'
        assert files[2]['change_type'] == 'deleted'
        assert files[3]['change_type'] == 'untracked'
        assert files[4]['change_type'] == 'renamed'
    
    @pytest.mark.asyncio
    async def test_process_repositories_concurrent(self, diff_processor):
        """Test concurrent processing of multiple repositories."""
        repos = [Path("/test/repo1"), Path("/test/repo2"), Path("/test/repo3")]
        
        # Mock the _detect_repository_changes method
        async def mock_detect_changes(repo_path):
            return RepositoryChange(
                repository_path=str(repo_path),
                repository_name=repo_path.name,
                timestamp=datetime.now().isoformat(),
                has_uncommitted_changes=False,
                uncommitted_files=[],
                recent_commits=[],
                current_branch="main",
                git_status="clean"
            )
        
        diff_processor._detect_repository_changes = mock_detect_changes
        
        results = await diff_processor.process_repositories(repos)
        
        assert len(results) == 3
        assert all(isinstance(r, RepositoryChange) for r in results)

class TestGitManagerDiffMethods:
    @pytest.fixture
    def git_manager(self):
        return GitManager()
    
    @pytest.mark.asyncio
    async def test_diff_files_with_changes(self, git_manager):
        """Test diff_files method when repository has changes."""
        mock_result = Mock()
        mock_result.stdout = "M  test.py\n?? new_file.txt\n"
        
        with patch.object(git_manager, '_run_subprocess', return_value=mock_result):
            result = await git_manager.diff_files(Path("/test/repo"))
        
        assert result['has_changes'] is True
        assert "M  test.py" in result['status_output']
        assert "?? new_file.txt" in result['status_output']
    
    @pytest.mark.asyncio  
    async def test_diff_files_clean_repo(self, git_manager):
        """Test diff_files method when repository is clean."""
        mock_result = Mock()
        mock_result.stdout = ""
        
        with patch.object(git_manager, '_run_subprocess', return_value=mock_result):
            result = await git_manager.diff_files(Path("/test/repo"))
        
        assert result['has_changes'] is False
        assert result['status_output'] == ""
    
    @pytest.mark.asyncio
    async def test_get_current_branch_success(self, git_manager):
        """Test successful current branch detection.""" 
        mock_result = Mock()
        mock_result.stdout = "main\n"
        
        with patch.object(git_manager, '_run_subprocess', return_value=mock_result):
            branch = await git_manager.get_current_branch(Path("/test/repo"))
        
        assert branch == "main"
    
    @pytest.mark.asyncio
    async def test_get_recent_commits_success(self, git_manager):
        """Test successful recent commits retrieval."""
        mock_result = Mock()
        mock_result.stdout = "abc123|John Doe|john@example.com|2024-01-01 12:00:00 +0000|Initial commit\ndef456|Jane Smith|jane@example.com|2024-01-02 14:30:00 +0000|Add feature\n"
        
        with patch.object(git_manager, '_run_subprocess', return_value=mock_result):
            commits = await git_manager.get_recent_commits(Path("/test/repo"), limit=2)
        
        assert len(commits) == 2
        assert commits[0]['hash'] == 'abc123'
        assert commits[0]['author_name'] == 'John Doe'
        assert commits[0]['message'] == 'Initial commit'
        assert commits[1]['hash'] == 'def456'
        assert commits[1]['author_name'] == 'Jane Smith'
```

### Integration Tests
Add to `tests/integration/test_diff_integration.py`:

```python
import pytest
import tempfile
import json
from pathlib import Path
from typer.testing import CliRunner

from mgit.__main__ import app

@pytest.fixture
def temp_repo_with_changes():
    """Create a temporary git repository with some changes."""
    # Implementation details for creating test repo with changes
    pass

def test_diff_command_basic_execution(temp_repo_with_changes):
    """Test basic diff command execution."""
    runner = CliRunner()
    
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.jsonl', delete=False) as f:
        output_path = f.name
    
    try:
        result = runner.invoke(app, [
            "diff", 
            str(temp_repo_with_changes),
            "--output", output_path,
            "--verbose"
        ])
        
        assert result.exit_code == 0
        
        # Verify JSONL output
        with open(output_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) > 0
            
            # Parse first line as JSON
            change_data = json.loads(lines[0])
            assert 'repository_path' in change_data
            assert 'timestamp' in change_data
            assert 'git_status' in change_data
            
    finally:
        Path(output_path).unlink()

def test_diff_command_recursive_scan():
    """Test diff command with recursive directory scanning."""
    # Test implementation
    pass

def test_diff_command_stdout_output():
    """Test diff command output to stdout.""" 
    # Test implementation
    pass
```

### Manual Verification Commands
```bash
# Test basic diff on current repository
poetry run mgit diff . --verbose

# Test diff with output file
poetry run mgit diff . --output /tmp/changes.jsonl --verbose

# Test diff on directory with multiple repositories  
poetry run mgit diff /path/to/repos --recursive --output /tmp/all_changes.jsonl

# Test concurrent processing
poetry run mgit diff /path/to/repos --concurrency 10 --verbose

# Verify JSONL output format
cat /tmp/changes.jsonl | head -1 | python -m json.tool
```

## Success Criteria
- [ ] Diff command properly registered in CLI at line 1290 in `__main__.py`
- [ ] `mgit/commands/diff.py` implements complete change detection functionality
- [ ] GitManager extended with `diff_files()`, `get_current_branch()`, `get_recent_commits()` methods
- [ ] Command accepts all specified parameters (path, output, recursive, concurrency, verbose)
- [ ] Outputs valid JSONL format with repository change information
- [ ] Concurrent processing works correctly with configurable limits
- [ ] Error handling prevents crashes on repository access failures
- [ ] Unit tests achieve >85% code coverage for new functionality
- [ ] Integration tests verify end-to-end command execution
- [ ] Manual verification commands all execute successfully

## Rollback Plan
If issues arise:
1. Remove diff command registration from `mgit/__main__.py` line 1290
2. Delete `mgit/commands/diff.py` file
3. Revert changes to `mgit/git/manager.py` (remove new methods)
4. Run `poetry run pytest` to ensure no regressions
5. Verify existing commands still work correctly

## Notes
- This phase establishes the foundation for all future change detection features
- JSONL output format enables easy processing by subsequent pipeline stages  
- Error handling ensures individual repository failures don't stop batch processing
- Concurrent processing provides good performance for large repository sets
- The diff functionality focuses on git-native change detection without external dependencies
- Repository discovery reuses existing directory scanning utilities
- Output format is designed to be machine-readable while remaining human-debuggable
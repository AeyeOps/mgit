# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Critical Lessons from Past Failures

### 1. Event Loop Management 
**Failure**: Reusing provider sessions across async operations caused "attached to a different event loop" errors
**Solution**: Always create fresh sessions with `_ensure_session()` for each operation
**Guard Rail**: Never cache provider instances; create new ones for each command

### 2. Configuration Field Names
**Failure**: Inconsistent field names across providers (token vs pat, org_url vs organization_url)
**Solution**: Implemented automatic field mapping in YAML manager
**Guard Rail**: Always check provider-specific field names in existing configs before assuming

### 3. BitBucket Authentication
**Failure**: Used email instead of username, causing authentication failures
**Solution**: BitBucket requires username (not email) + app password (not regular password)
**Guard Rail**: Each provider has unique auth requirements - verify in provider docs

### 4. Documentation for Public Release
**Failure**: README had broken URLs, wrong version numbers, invalid config examples
**Solution**: Line-by-line verification against actual code implementation
**Guard Rail**: Before any public release, verify EVERY claim with code evidence

### 5. Provider Logic Leakage
**Failure**: Provider-specific code in CLI layer made maintenance difficult
**Solution**: Strict abstraction - all provider logic must stay in providers/ directory
**Guard Rail**: CLI should only use provider interface, never provider-specific details

### 6. DDD Over-Engineering (2025-06-09)
**Failure**: 4-layer DDD refactoring created async/sync impedance mismatch, breaking all operations
**Root Cause**: Sync port interfaces (`ProviderOperations`) over async infrastructure
**Symptoms**: `'async for' requires an object with __aiter__ method, got list` errors
**Solution**: Either make all interfaces async or use simpler architecture
**Guard Rails**: 
- Architecture must match runtime reality (async system = async interfaces)
- Test basic operations immediately after refactoring
- Feature parity before celebrating line count reduction
- Consider if DDD is appropriate for simple CLI tools

## Commands

### Development Workflow
```bash
# Install dependencies
poetry install --with dev

# Run the application
poetry run mgit --help
poetry run mgit --version

# Run tests
poetry run pytest tests/ -v                    # All tests
poetry run pytest tests/unit/ -v               # Unit tests only
poetry run pytest tests/integration/ -v        # Integration tests only
poetry run pytest tests/unit/test_git.py::TestGitOperations::test_git_clone_success -v  # Single test

# Code quality
poetry run poe lint                  # Ruff linting
poetry run poe format                # Black formatting
poetry run poe format-check          # Check formatting without changes
poetry run mypy mgit/                # Type checking (294 errors, non-blocking)

# Build executables
poetry run poe build-linux           # Linux binary
poetry run poe build-windows         # Windows binary
poetry run poe build-all             # All platforms

# Security checks
poetry run bandit -r mgit/ -f txt    # Security analysis
poetry run pip-audit                 # Dependency vulnerabilities

# Version management
poetry run poe version-sync          # Sync version across files
poetry run poe bump-patch            # Bump patch version
```

### Common mgit Commands
```bash
# Provider setup
poetry run mgit login --provider github --name my_github
poetry run mgit login --provider azuredevops --name work_ado
poetry run mgit login --provider bitbucket --name team_bb

# Repository operations
poetry run mgit list "myorg/*/*"                           # Find repos
poetry run mgit clone-all "myorg/*/*" ./repos              # Clone repos
poetry run mgit pull-all "myproject" ./repos               # Update repos
poetry run mgit status ./repos                              # Check status

# Configuration
poetry run mgit config --list                               # List providers
poetry run mgit config --show work_ado                      # Show provider config
poetry run mgit config --set-default personal_gh            # Set default

# Monitoring
poetry run mgit monitoring server --port 8080               # Start server
poetry run mgit monitoring health --detailed                # Health check
```

## High-Level Architecture

### Core Design Principles
1. **Provider Abstraction**: All Git providers (Azure DevOps, GitHub, BitBucket) implement a common `GitProvider` interface
2. **Async-First**: All network operations use async/await for concurrent execution
3. **Configuration Hierarchy**: Environment variables > Config file > Defaults
4. **Security by Default**: Automatic credential masking, secure file permissions, input validation

### Key Architectural Components

#### Provider System (`mgit/providers/`)
- **Base Provider** (`base.py`): Abstract interface all providers must implement
- **Provider Factory** (`factory.py`): Creates provider instances based on URLs/config
- **Provider Registry** (`registry.py`): Manages available providers
- **Provider Manager** (`manager_v2.py`): Orchestrates multi-provider operations

Each provider handles its specific API:
- **Azure DevOps**: Organization → Project → Repository hierarchy
- **GitHub**: Organization/User → Repository (flat structure)
- **BitBucket**: Workspace → Repository (optional projects)

#### Configuration System (`mgit/config/`)
- **YAML Manager** (`yaml_manager.py`): Handles config file operations
- Configuration stored in `~/.config/mgit/config.yaml`
- Automatic field mapping for backwards compatibility (e.g., `token` → `pat`)
- Provider configurations are namespaced

#### Security Layer (`mgit/security/`)
- **Credentials** (`credentials.py`): Token encryption/decryption
- **Validation** (`validation.py`): Input sanitization
- **Monitoring** (`monitor.py`): Security event tracking
- **Logging** (`logging.py`): Automatic credential masking in logs

#### Git Operations (`mgit/git/`)
- **Git Manager** (`manager.py`): Handles clone/pull operations
- **Git Utils** (`utils.py`): Helper functions for Git operations
- Uses subprocess for Git commands with proper error handling

#### CLI Layer (`mgit/__main__.py`)
- Built with Typer for modern CLI experience
- Commands organized in `commands/` directory
- Rich console for formatted output
- Progress bars for long operations

### Critical Implementation Details

#### Event Loop Management
The application carefully manages async event loops to prevent conflicts:
- `_ensure_session()` creates new sessions for each operation
- Provider instances are not reused across event loops
- Sync/async boundary handled by `AsyncExecutor`

#### Provider Authentication
Each provider has specific authentication requirements:
- **Azure DevOps**: PAT with Code (Read/Write) and Project (Read) scopes
- **GitHub**: PAT with repo and read:org scopes
- **BitBucket**: App Password (not regular password) with repository access

#### Configuration Migration
The system migrated from JSON to YAML configuration:
- Automatic migration on first use
- Field mapping for backwards compatibility
- Provider-specific field names preserved

#### Rate Limiting
Default concurrency limits per provider:
- Azure DevOps: 4 concurrent operations
- GitHub: 10 concurrent operations  
- BitBucket: 5 concurrent operations

### Import Hierarchy
To avoid circular imports:
```
constants.py → No imports from mgit modules
utils/* → Can import from constants
config/* → Can import from constants, utils  
providers/base.py → Can import from constants, exceptions
providers/* → Can import from base, constants, exceptions
security/* → Can import from config, constants
monitoring/* → Can import from config, constants, security
git/* → Can import from utils, constants
commands/* → Can import from all modules
__main__.py → Can import from all modules
```

## Testing Strategy

### Test Organization
- **Unit Tests** (`tests/unit/`): Test individual components in isolation
- **Integration Tests** (`tests/integration/`): Test command execution
- Mock external API calls to avoid network dependencies
- Use pytest fixtures for common setup (`tests/conftest.py`)

### Current Test Coverage
- Overall: 22% (working to improve)
- 84 tests passing, 5 skipped
- Key areas well-tested: Git operations, provider abstractions, utils

## Common Development Patterns

### Adding a New Provider
1. Create class in `providers/` inheriting from `GitProvider`
2. Implement required methods: `authenticate()`, `list_repositories()`, etc.
3. Register in `providers/registry.py`
4. Add provider-specific config handling
5. Update documentation and tests

### Adding a New Command
1. Create module in `commands/`
2. Define command function with Typer decorators
3. Import and register in `__main__.py`
4. Add integration tests

### Error Handling Pattern
```python
try:
    # Operation
except ProviderAuthenticationError:
    console.print("[red]Authentication failed[/red]")
    raise typer.Exit(1)
except NetworkError as e:
    console.print(f"[red]Network error: {e}[/red]")
    raise typer.Exit(1)
```

## Known Issues and Gotchas

1. **MyPy Errors**: 294 type annotation errors (non-blocking in CI)
2. **Safety Tool**: Deprecated, use pip-audit instead
3. **BitBucket Authentication**: Must use username (not email) with app password
4. **Windows Builds**: WSL cannot access Windows Python for cross-compilation
5. **Async Complexity**: Event loop management requires careful handling

## Testing Before Changes

### Critical Test Points
1. **After Provider Changes**: Test authentication and list operations
   ```bash
   poetry run mgit list "org/*/*" --limit 5
   ```

2. **After Config Changes**: Verify field mapping works
   ```bash
   poetry run mgit config --show provider_name
   ```

3. **After Async Changes**: Run concurrent operations
   ```bash
   poetry run mgit clone-all "org/*/*" ./test --concurrency 10
   ```

4. **After Documentation Updates**: Verify all commands and examples
   ```bash
   # Test every command example in README
   # Verify version numbers match across files
   ```

## Version Information
- Current Version: 0.3.1
- Python Support: 3.9, 3.10, 3.11, 3.12
- Version synchronized across: `pyproject.toml`, `mgit/constants.py`, CLI output
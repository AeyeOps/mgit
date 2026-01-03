# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
```bash
# Install dependencies
uv sync

# Run the application
uv run mgit --help
uv run mgit --version

# Local sync (walk current directory or a path)
mgit sync
mgit sync ./workspace

# Remote sync (explicit pattern)
mgit sync --filter "myorg/*/*" ./repos

# Run tests
uv run python scripts/make_test.py                    # All tests
uv run python scripts/make_test.py tests/unit/ -v     # Unit tests only
uv run python scripts/make_test.py -m unit            # By marker

# Code quality
uv run python scripts/make_lint.py                    # Ruff linting
uv run python scripts/make_format.py                  # Ruff formatting
uv run python scripts/make_format.py --check          # Check only
uv run pyright mgit/                                  # Type checking
```

### Build
```bash
# Linux binary
uv run python scripts/make_build.py --target linux

# Linux binary + install to /opt/bin/mgit
uv run python scripts/make_build.py --target linux --install

# Windows (from WSL)
uv run python scripts/make_build.py --target windows

# Both platforms
uv run python scripts/make_build.py --target all

# Clean build artifacts
uv run python scripts/make_clean.py

# Test standalone binary (uses /opt/bin/mgit)
uv run python scripts/test_binary.py
uv run python scripts/test_binary.py --verbose
uv run python scripts/test_binary.py --binary /path/to/mgit
```

### Version Management
```bash
uv run python scripts/make_version.py --bump patch    # 0.7.2 -> 0.7.3
uv run python scripts/make_version.py --bump minor    # 0.7.2 -> 0.8.0
uv run python scripts/make_version.py --bump major    # 0.7.2 -> 1.0.0
```

## Architecture

### Provider Abstraction Layer
All Git providers implement a common interface in `mgit/providers/`:

```
providers/
├── base.py         # Abstract GitProvider class, Repository/Organization/Project dataclasses
├── github.py       # GitHub implementation
├── azdevops.py     # Azure DevOps implementation
├── bitbucket.py    # BitBucket implementation
├── manager.py      # ProviderManager orchestrates multi-provider operations
├── factory.py      # Creates provider instances from config
└── registry.py     # Provider registration system
```

**Key pattern**: Each provider implements `authenticate()`, `list_repositories()`, `get_repository()` etc. CLI never contains provider-specific logic.

### Configuration System
YAML-based configuration in `mgit/config/yaml_manager.py`:
- Config stored at `~/.config/mgit/config.yaml`
- Automatic field mapping for backwards compatibility (`token` → `pat`)
- Provider configs are namespaced by name

### Command Layer
Commands in `mgit/commands/`:
- `sync.py` - Clone/pull repositories (main command)
- `listing.py` - List repositories matching patterns
- `status.py` - Check repository status
- `diff.py` / `diff_remote.py` - Change detection
- `bulk_operations.py` - Shared bulk operation logic

### Query Pattern System
Pattern format: `organization/project/repository`
- Azure DevOps uses all three parts
- GitHub/BitBucket ignore project part (`org/*/repo` works)
- Wildcards (`*`) work in any position

### Async Architecture
All network operations are async:
- `_ensure_session()` creates fresh sessions per operation (prevents event loop conflicts)
- Provider instances are not reused across event loops
- `AsyncExecutor` in `mgit/utils/async_executor.py` handles sync/async boundary

## Import Hierarchy
To avoid circular imports:
```
constants.py → No mgit imports
utils/* → constants only
config/* → constants, utils
providers/base.py → constants, exceptions
providers/* → base, constants, exceptions
security/* → config, constants
git/* → utils, constants
commands/* → all modules
__main__.py → all modules
```

## Provider Authentication Requirements
- **Azure DevOps**: PAT with Code (Read/Write) + Project (Read) scopes. URL: `https://dev.azure.com/orgname`
- **GitHub**: PAT (`ghp_...`) with `repo`, `read:org`, `read:user` scopes
- **BitBucket**: Username (not email) + App Password (not regular password)

## Test Markers
```python
@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.requires_network
@pytest.mark.asyncio
```

## Entry Point
`mgit/__main__.py` defines the Typer CLI app. Entry point for packaging: `mgit.__main__:entrypoint`

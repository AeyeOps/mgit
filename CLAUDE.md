# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
Use `make` targets instead of invoking scripts directly, because this keeps the Makefile validated and consistent with CI.

```bash
# Validation (format + lint + type check + bandit)
make validate                     # All checks
make validate ARGS="--fix"        # Auto-fix, then check

# Tests
make test                         # All tests (including e2e)
make test ARGS="tests/unit/ -v"   # Unit tests only
```

### Release Process
Avoid editing `pyproject.toml` version manually or pushing a version bump without running `make validate` first, because pushing a version change to `main` triggers `auto-release.yml` which runs quality gates (ruff format, ruff check, ty, bandit). If those fail, the release is blocked.

The safe release workflow:
```bash
# Option 1: Single command (recommended) — validates, bumps, commits, pushes
make release ARGS="--bump minor"  # or patch|major

# Option 2: Step by step
make validate                          # Run CI checks locally first
make version ARGS="--bump minor"       # Bumps version (runs validate again as gate)
# Then manually: git add, commit, push
```

Version bump levels:
```bash
make release ARGS="--bump patch"  # 0.12.0 -> 0.12.1 (bug fixes)
make release ARGS="--bump minor"  # 0.12.0 -> 0.13.0 (new features)
make release ARGS="--bump major"  # 0.12.0 -> 1.0.0  (breaking changes)
```

What `auto-release.yml` does on version change push to `main`:
1. **Quality & Security Checks**: `ruff format --check`, `ruff check`, `ty check`, `bandit -lll`, unit tests
2. **Generate Release Notes**: Extracts from CHANGELOG.md, optional AI generation
3. **Build and Release**: `uv build`, creates git tag, GitHub Release with artifacts
4. **PyPI**: Publishes package

If the workflow fails after push, fix the issue and use `gh workflow run auto-release.yml --field force-release=true` to re-trigger.

### Build
```bash
make build-standalone-linux       # Linux binary + install to /usr/local/bin/mgit
make build-standalone-windows     # Windows binary (from WSL)
make clean                        # Remove build artifacts
make test-standalone-linux        # Test the installed binary
make test-flat-layout-e2e         # E2E flat layout tests with binary
```

If `make build-standalone-linux` fails on the install step (sudo), run `cp /opt/aeo/mgit/dist/mgit /usr/local/bin/mgit` to complete the install, because the build isn't finished until the binary is at `/usr/local/bin/mgit`.

### Running mgit
```bash
uv run mgit --help
uv run mgit --version
mgit sync "myorg/*/*" ./repos                 # Flat layout (default)
mgit sync "myorg/*/*" ./repos --hierarchy     # Hierarchical layout
```

## Architecture Decision Records (ADRs)

Key architectural decisions are documented in `docs/ADR/`:

| ADR | Title | Summary |
|-----|-------|---------|
| [001](docs/ADR/001-provider-abstraction.md) | Provider Abstraction | Common interface for GitHub/Azure DevOps/BitBucket |
| [002](docs/ADR/002-configuration-hierarchy.md) | Configuration Hierarchy | CLI args > env vars > config file precedence |
| [003](docs/ADR/003-concurrent-operations.md) | Concurrent Operations | Semaphore-based throttling, provider-specific limits |
| [004](docs/ADR/004-pattern-matching-strategy.md) | Pattern Matching | org/project/repo format, wildcard support |

Consult ADRs before making architectural changes.

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

### Sync Directory Layout
Default is **flat layout** - repos cloned directly into target directory:
```
./target/
├── repo-a/
├── repo-b/
└── repo-c/
```

Use `--hierarchy` for hierarchical layout (original behavior):
```
./target/
└── github.com/
    └── myorg/
        └── repos/
            ├── repo-a/
            └── repo-b/
```

**Collision resolution** (flat layout): When repos from different orgs share names, automatic disambiguation appends `_orgname` suffix (e.g., `auth_org-a/`, `auth_org-b/`). If orgs also collide, provider prefix is added (e.g., `auth_github_org/`, `auth_azure_org/`).

**Testing note**: Cross-provider collision resolution (e.g., GitHub vs Azure DevOps with same org name) cannot be E2E tested with local infrastructure—requires multiple real providers. This logic is covered by unit tests only (`tests/unit/test_flat_layout.py::TestCollisionResolution::test_cross_provider_collision`).

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

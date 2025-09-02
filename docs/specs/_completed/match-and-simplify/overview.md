# Match and Simplify: Multi-Provider Pattern Matching Specification

## Executive Summary

This specification addresses critical issues discovered with mgit's pattern matching and multi-provider support, particularly in the `clone-all` command. The current implementation fails to properly search across all configured providers when patterns are used without explicit provider specification.

## Problem Statement

### Core Issue
When users run `mgit clone-all "myorg/*/*" ./repos` without specifying a provider, the expectation is that mgit will search **all configured providers** for repositories matching the pattern. Instead, it only searches the default provider, missing repositories in other configured providers.

### User Intent vs Reality

| User Command | User Expects | What Actually Happens |
|--------------|--------------|----------------------|
| `mgit clone-all "*/*/*" ./repos` | Search all providers | ✅ Works (multi-provider mode) |
| `mgit clone-all "myorg/*/*" ./repos` | Search all providers for "myorg" | ❌ Only searches default provider |
| `mgit clone-all "*/project/*" ./repos` | Search all providers for "project" | ❌ Only searches default provider |
| `mgit clone-all "myorg/proj/repo*" ./repos` | Search all providers | ❌ Only searches default provider |

## Discovery Findings

### 1. Overly Restrictive Multi-Provider Detection

**Location**: `mgit/__main__.py`, lines 406-410

```python
is_multi_provider_pattern = (
    config is None and url is None and 
    ("*" in first_segment or "?" in first_segment)
)
```

**Problem**: Multi-provider mode only activates when:
- No `--config` flag provided
- No `--url` flag provided
- The **first segment** contains wildcards (`*` or `?`)

This means patterns like `myorg/*/*` don't trigger multi-provider search because "myorg" has no wildcards.

### 2. Inconsistent Code Paths

The `clone-all` command has three different code paths for pattern matching:

1. **Multi-provider pattern** (lines 415-426): Uses `list_repositories()` with `provider_name=None`
2. **Pattern with explicit provider** (lines 430-440): Uses `list_repositories()` with specific provider
3. **Pattern without provider** (lines 442-457): Manually iterates through providers

This inconsistency leads to different behaviors and potential bugs.

### 3. Default Provider Fallback

**Location**: `mgit/__main__.py`, lines 368-371

When no provider is specified, the code attempts to infer the provider from the query:
- If inference fails (e.g., due to wildcards), it falls back to the default provider
- This prevents searching across all providers

### 4. List Command Works Correctly

**Location**: `mgit/commands/listing.py`, lines 233-368

The `list` command properly implements multi-provider discovery:
- Detects multi-provider patterns correctly
- Processes providers concurrently
- Aggregates results properly

The `clone-all` command should use the same logic.

## Root Cause Analysis

### Design Flaw
The fundamental issue is that `clone-all` tries to be "smart" about when to use multi-provider mode, but the heuristics are wrong. The logic assumes that only patterns with wildcards in the provider/organization position need multi-provider search.

### Conceptual Mismatch
- **User mental model**: "If I don't specify a provider, search everywhere"
- **Implementation model**: "If I don't specify a provider, use the default unless the pattern explicitly indicates multiple providers"

### Code Duplication
Having separate implementations for pattern matching in `clone-all` vs `list` creates inconsistencies and maintenance burden.

## Proposed Solution

### Principle: Explicit is Better Than Implicit

1. **When provider IS specified** (`--config` or `--url`):
   - Use only that provider
   - Clear, explicit behavior

2. **When provider IS NOT specified**:
   - **Always** search all configured providers when a pattern is present
   - Use default provider only for non-pattern queries

### Implementation Strategy

#### Phase 1: Fix Multi-Provider Detection
- Remove the restrictive first-segment wildcard check
- Align with user expectations: no provider = search all providers

#### Phase 2: Unify Pattern Matching Logic
- Extract common pattern matching logic to a shared module
- Ensure `list` and `clone-all` use the same code path

#### Phase 3: Simplify Code Paths
- Consolidate the three different code paths in `clone-all`
- Always use `list_repositories()` for pattern matching

#### Phase 4: Performance Optimization
- Implement proper concurrent provider processing
- Add progress indicators for multi-provider operations

## Success Criteria

- [ ] Pattern `myorg/*/*` searches all providers when no `--config` specified
- [ ] Pattern `*/project/*` searches all providers when no `--config` specified
- [ ] Explicit `--config` restricts search to that provider only
- [ ] `clone-all` and `list` commands behave consistently
- [ ] Code is simplified with single pattern matching implementation
- [ ] Performance is maintained or improved with concurrent processing
- [ ] User documentation clearly explains the behavior

## Implementation Phases

### Phase 1: Implement `sync` Command [PENDING]
- **Objective**: Create the new unified `sync` command with correct pattern matching
- **File**: `phases-pending/phase-1-implement-sync-command.md`
- **Estimated Effort**: 2 hours

### Phase 2: Fix Pattern Matching for All Providers [PENDING]
- **Objective**: Ensure pattern matching searches all providers when no provider specified
- **File**: `phases-pending/phase-2-fix-pattern-matching.md`
- **Estimated Effort**: 1 hour

### Phase 3: Deprecate Old Commands [PENDING]
- **Objective**: Add deprecation warnings and create migration aliases
- **File**: `phases-pending/phase-3-deprecate-old-commands.md`
- **Estimated Effort**: 1 hour

### Phase 4: Update Documentation and Tests [PENDING]
- **Objective**: Update all docs, examples, and tests for new `sync` command
- **File**: `phases-pending/phase-4-update-docs-tests.md`
- **Estimated Effort**: 1.5 hours

## Testing Strategy

### Test Cases

1. **Multi-Provider Search**
   ```bash
   # Should search all providers
   mgit clone-all "myorg/*/*" ./test
   mgit clone-all "*/project/*" ./test
   mgit clone-all "*/*/*service" ./test
   ```

2. **Single Provider Search**
   ```bash
   # Should only search github_work
   mgit clone-all "myorg/*/*" ./test --config github_work
   ```

3. **Default Provider Fallback**
   ```bash
   # Non-pattern: should use default provider
   mgit clone-all "myorg/myproject" ./test
   ```

### Performance Benchmarks
- Measure time for multi-provider search with 5+ providers
- Ensure concurrent processing maintains or improves performance

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing workflows | High | Add compatibility flag for old behavior |
| Performance degradation | Medium | Implement concurrent provider processing |
| Increased API calls | Medium | Add caching and smart filtering |
| User confusion | Low | Clear documentation and examples |

## Alternative Approaches Considered

### 1. Require Explicit Multi-Provider Flag
- Add `--all-providers` flag for multi-provider search
- **Rejected**: Adds complexity, not intuitive

### 2. Smart Provider Detection Based on Org Name
- Try to match organization names to providers automatically
- **Rejected**: Too magical, prone to errors

### 3. Keep Current Behavior
- Document the current limitations
- **Rejected**: Doesn't match user expectations

## Related Work

- ADR-001: Provider Abstraction Strategy
- ADR-004: Pattern Matching Strategy
- Recent commit: "feat: implement multi-provider pattern matching" (4cfd4ee)

## Open Questions

1. Should we add a `--provider all` option as an explicit way to search all providers?
2. How should we handle provider authentication failures during multi-provider search?
3. Should we implement provider priority/ordering for search results?
4. What's the best way to handle duplicate repositories across providers?

## Additional Discovery: Command Overlap and Duplication

### Clone-All vs Pull-All Analysis

After analyzing both commands, we've discovered **significant duplication** and **confusion** between `clone-all` and `pull-all`:

#### Current State

**clone-all command:**
- Has `--update-mode` with options: `skip`, `pull`, `force`
- When `--update-mode pull` is used, it effectively becomes a pull operation
- Can clone new repos OR update existing ones

**pull-all command:**
- Also has `--update-mode` with the same options: `skip`, `pull`, `force`
- When `--update-mode force` is used, it can DELETE and re-clone (!)
- Essentially duplicates most of clone-all's functionality

#### The Overlap Problem

Both commands use the **same BulkOperationProcessor** with just a different `OperationType`:

```python
# In clone-all:
processor = BulkOperationProcessor(
    git_manager=git_manager,
    provider_manager=default_provider_manager,
    operation_type=OperationType.clone,  # ← Only difference
)

# In pull-all:
processor = BulkOperationProcessor(
    git_manager=git_manager,
    provider_manager=default_provider_manager,
    operation_type=OperationType.pull,   # ← Only difference
)
```

But the `update_mode` parameter makes this distinction **almost meaningless**:

| Command | Update Mode | Behavior |
|---------|------------|----------|
| `clone-all` | `skip` | Skip existing dirs, clone new ones |
| `clone-all` | `pull` | Pull existing repos, clone new ones |
| `clone-all` | `force` | Delete & re-clone everything |
| `pull-all` | `skip` | Skip non-git dirs, pull git repos |
| `pull-all` | `pull` | Pull existing git repos |
| `pull-all` | `force` | Delete & re-clone everything |

### The Fundamental Confusion

1. **`clone-all --update-mode pull`** is effectively a "sync" operation (clone new, pull existing)
2. **`pull-all --update-mode force`** can DELETE and re-clone, which is not what "pull" implies
3. Both commands can achieve the same results with different flag combinations

### Simplification Opportunity: Just `sync`

After analysis, the cleanest solution is to **replace both commands with a single `sync` command**:

```bash
mgit sync "pattern" ./path [--force]
```

#### The `sync` Command Behavior

**Default behavior (intelligent sync):**
- **Missing repos**: Clone them
- **Existing repos**: Pull latest changes
- **Non-git directories**: Skip with warning
- **Disabled repos**: Skip with info

**With `--force` flag:**
- **All matching repos**: Delete and re-clone fresh
- Requires confirmation prompt for safety

#### Why This Is Better

1. **Intuitive**: `sync` perfectly describes the operation - synchronize local with remote
2. **Simple**: No confusing mode combinations
3. **Predictable**: Does the right thing by default
4. **Clean**: One command, one purpose, optional force

#### Implementation

```python
@app.command()
def sync(
    pattern: str = typer.Argument(..., help="Repository pattern (org/project/repo)"),
    path: str = typer.Argument(..., help="Local path to sync into"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Specific provider (otherwise all)"),
    force: bool = typer.Option(False, "--force", "-f", help="Delete and re-clone all repos"),
    concurrency: int = typer.Option(4, "--concurrency", "-c", help="Parallel operations"),
):
    """
    Synchronize repositories with remote providers.
    
    Clones missing repositories and pulls updates for existing ones.
    Use --force to delete and re-clone everything fresh.
    """
    # Pattern matching works across all providers by default
    # Single clear behavior: sync local with remote
```

#### Migration Path

1. **Phase 1**: Introduce `sync` command
2. **Phase 2**: Deprecate `clone-all` and `pull-all` with warnings
3. **Phase 3**: Add aliases for backwards compatibility:
   - `clone-all` → `sync` with deprecation warning
   - `pull-all` → `sync` with deprecation warning
4. **Phase 4**: Remove old commands in next major version

#### User Experience

```bash
# Initial setup - clones all matching repos
mgit sync "myorg/*/*" ./workspace

# Daily update - pulls changes, clones any new repos
mgit sync "myorg/*/*" ./workspace

# Fresh start - removes and re-clones everything
mgit sync "myorg/*/*" ./workspace --force

# Specific provider only
mgit sync "myorg/*/*" ./workspace --provider github_work

# Pattern matching across all providers (the main fix!)
mgit sync "*/project/*" ./workspace  # Searches ALL providers
```

This is **dramatically simpler** than the current situation and actually does what users expect.

## Detailed Behavior Specification

### Pattern Matching Rules

#### Valid Pattern Formats
```
org/project/repo     # Exact match
org/*/repo          # Wildcard in project position  
org/*/*             # All repos in org
*/project/*         # Project across all orgs
*/*/*               # Everything
org/proj/repo*      # Repos starting with "repo"
```

#### Edge Cases and Invalid Patterns

| Pattern | Interpretation | Valid? |
|---------|---------------|--------|
| `org//repo` | Empty project segment | ❌ Invalid - reject with error |
| `/org/project/repo` | Leading slash | ❌ Invalid - patterns are relative |
| `org/project/repo/` | Trailing slash | ⚠️ Warning - strip and continue |
| `org/` | Incomplete pattern | ❌ Invalid - need 3 segments |
| `//` | Double slash only | ❌ Invalid - meaningless |
| `org/*` | Two segments only | ❌ Invalid - need org/project/repo format |
| ` org / * / * ` | Spaces in pattern | ✅ Valid - trim spaces from segments |

**Pattern Validation Rules:**
1. Must have exactly 3 segments separated by `/`
2. Empty segments are errors (consecutive slashes)
3. Leading/trailing slashes are stripped with warning
4. Whitespace is trimmed from each segment
5. At least one segment must be non-wildcard (prevent `*/*/*` unless explicitly confirmed)

### Concurrency Behavior

```python
DEFAULT_CONCURRENCY = 4  # Conservative default
MAX_CONCURRENCY = 20     # Hard limit to prevent API abuse

# Per-provider limits (respect API rate limits)
PROVIDER_LIMITS = {
    "github": 10,
    "azuredevops": 4,
    "bitbucket": 5,
}
```

**Concurrency Logic:**
1. User specifies `--concurrency N` (default 4)
2. Each provider gets min(N, PROVIDER_LIMIT)
3. Providers process in parallel, repos within provider respect limit
4. Smart backoff on rate limit errors

### Visual Feedback Requirements

```
Discovering repositories...
├─ github_work: Found 45 repos
├─ github_personal: Found 12 repos
└─ azdo_enterprise: Found 78 repos

Synchronizing 135 repositories (concurrency: 4)
[████████████████████░░░░░░░] 67/135 • 49% • ETA: 0:02:15

Current Operations:
  ✓ Cloned: my-app-frontend
  ↻ Pulling: backend-services
  ↻ Cloning: new-microservice
  ⚠ Skipped: archived-repo (disabled)
  
Summary:
  Cloned: 23 | Updated: 42 | Skipped: 2 | Failed: 0
```

**Visual Elements:**
- Overall progress bar with ETA
- Per-repository status indicators
- Live updates for current operations
- Color coding: green (success), yellow (skip), red (error), cyan (in-progress)
- Final summary with categorized counts

### Scenario Decision Matrix

#### Without `--force` Flag

| Local State | Remote State | Action | Visual Feedback |
|-------------|--------------|--------|-----------------|
| Doesn't exist | Exists | Clone | `🟢 Cloning: repo-name` |
| Exists (git repo) | Exists | Pull | `🔄 Pulling: repo-name` |
| Exists (not git) | Exists | Skip | `⚠️ Skipped: repo-name (not a git repo)` |
| Exists (git repo) | Deleted | Warn & Skip | `⚠️ Warning: repo-name (remote deleted)` |
| Doesn't exist | Disabled | Skip | `⚫ Skipped: repo-name (disabled)` |
| Exists (dirty) | Exists | Pull (may fail) | `⚠️ Pull failed: repo-name (uncommitted changes)` |
| Exists (diverged) | Exists | Pull (may conflict) | `⚠️ Pull failed: repo-name (merge conflicts)` |

#### With `--force` Flag

| Local State | Remote State | Action | Visual Feedback |
|-------------|--------------|--------|-----------------|
| Any | Exists | Delete & Clone | `🔄 Replacing: repo-name` |
| Any | Disabled | Skip | `⚫ Skipped: repo-name (disabled)` |
| Any | Deleted | Delete local | `🗑️ Removed: repo-name (remote deleted)` |

**Force Confirmation:**
```
⚠️  FORCE MODE: This will DELETE and re-clone 135 repositories:
  - All local changes will be lost
  - All untracked files will be deleted
  - All git history will be reset

Continue? [y/N]: 
```

### Error Handling

#### Recoverable Errors (Continue Processing)
- **Authentication failure on one provider**: Skip provider, continue with others
- **Single repo clone/pull failure**: Log error, continue with next
- **Rate limit hit**: Exponential backoff, retry
- **Network timeout**: Retry with backoff (max 3 attempts)

#### Fatal Errors (Stop Processing)
- **No providers configured**: Exit with setup instructions
- **Invalid pattern format**: Exit with pattern help
- **Target directory not writable**: Exit with permission error
- **All providers fail auth**: Exit with auth help

#### Error Reporting
```
Synchronization completed with errors:

Failed Operations (3):
  ❌ repo-1: Authentication failed (check PAT)
  ❌ repo-2: Network timeout after 3 retries
  ❌ repo-3: Permission denied (check directory permissions)

Successful: 132 | Failed: 3 | Skipped: 0

Run with --verbose for detailed error logs.
```

### Multi-Provider Behavior

**Default (no --provider flag):**
1. Query ALL configured providers in parallel
2. Aggregate results, removing duplicates
3. Process all repos respecting per-provider concurrency

**With --provider flag:**
1. Query ONLY specified provider
2. Fail if provider doesn't exist
3. Use provider-specific concurrency limit

**Provider Priority (for duplicates):**
When same repo exists in multiple providers:
1. Use explicit priority if configured
2. Otherwise, first found wins
3. Log duplicate detection in verbose mode

### Path Construction

```python
# Repository path building logic
def build_local_path(repo: Repository, base_path: Path) -> Path:
    """
    Build consistent local paths regardless of provider.
    
    Examples:
      GitHub: myorg/myrepo -> base_path/myorg/myrepo
      Azure: myorg/myproject/myrepo -> base_path/myorg/myproject/myrepo  
      BitBucket: myworkspace/myrepo -> base_path/myworkspace/myrepo
    """
    # Use clone URL to determine structure
    # Strip protocol and host, preserve organization structure
    # Ensure no path traversal attacks (.. in repo names)
```

## Conclusion

The current implementation has two major issues:
1. **Pattern matching doesn't work as users expect** (original issue)
2. **Command overlap creates confusion** (newly discovered)

By fixing the pattern matching logic AND simplifying the command structure, we can provide a better user experience while also reducing code complexity and maintenance burden.
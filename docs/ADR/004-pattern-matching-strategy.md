# ADR-004: Pattern Matching Strategy

## Status
Accepted

## Context

mgit uses a three-part pattern system `organization/project/repository` to query repositories across different providers. However, providers have different organizational structures:
- **Azure DevOps**: Full three-level hierarchy (org → project → repo)
- **GitHub**: Two-level structure (org/user → repo)
- **BitBucket**: Two-level with optional projects (workspace → repo)

Users need a consistent pattern language that works across all providers while respecting provider differences.

Recent enhancement (v0.4.9) added multi-provider pattern matching capabilities, allowing patterns to discover repositories across multiple providers simultaneously.

## Decision

Implement a unified pattern matching strategy:

1. **Three-part pattern**: Always use `org/project/repo` format
2. **Provider adaptation**: Each provider interprets patterns according to its structure
   - Azure DevOps: Uses all three parts
   - GitHub/BitBucket: Ignores middle part or treats as wildcard
3. **Wildcard support**: `*` matches any value in any position
4. **Multi-provider discovery**: Patterns can query across all configured providers
5. **Case-insensitive matching**: Provider names and patterns are case-insensitive

Pattern examples:
```bash
# Specific provider
mgit list "myorg/*/*" --provider github_work

# All providers matching pattern
mgit list "*/*/*"  # Searches all configured providers

# Provider prefix matching
mgit list "GITHUB*/*/*"  # All GitHub-type providers
mgit list "*abc/*/*"     # Providers ending with "abc"
```

## Implementation

The pattern matching system:
1. Parses the three-part pattern
2. Identifies target providers (specific, wildcard, or pattern-based)
3. Adapts pattern for each provider's structure
4. Executes queries concurrently across providers
5. Aggregates and deduplicates results

## Consequences

### Positive:
- **Consistency**: Single pattern format for all providers
- **Flexibility**: Wildcards enable powerful queries
- **Discovery**: Multi-provider search capabilities
- **Intuitive**: Patterns map to natural repository organization

### Negative:
- **Abstraction leakage**: Provider differences still visible
- **Confusion potential**: Middle segment ignored for some providers
- **Complexity**: Pattern adaptation logic per provider

### Neutral:
- Pattern behavior documented per provider
- Users learn provider-specific quirks over time
- Trade-off between consistency and accuracy

## Related
- ADR-001: Provider abstraction strategy
- Multi-provider pattern matching feature (v0.4.9)
- Query parser implementation in utils/
# Exhaustive Pattern Combinations for mgit list

This document catalogs all possible query pattern combinations for the `mgit list` command, organized by complexity and use case.

## Pattern Structure

All patterns follow the `<organization>/<project>/<repository>` structure, where each segment can be:

- **Exact match**: `pdidev`, `Blue Cow`, `DevTools`
- **Wildcard**: `*` (matches anything)
- **Partial match**: `*dev`, `Dev*`, `*Tools*`
- **Empty**: (not specified, defaults to `*`)

## Classification System

### By Complexity Level
- **Level 1**: Single segment patterns
- **Level 2**: Two segment patterns
- **Level 3**: Three segment patterns
- **Level 4**: Compound partial patterns

### By Match Type
- **Exact**: No wildcards
- **Single**: One wildcard
- **Partial**: Partial wildcards (*text* or text*)
- **Full**: All wildcards

## Level 1: Single Segment Patterns

### Repository-Only Patterns (Auto-expanded to `*/*/<repo>`)
```
Pattern: DevTools
Expands to: */*/DevTools
Use case: Find all repos named "DevTools" across all orgs/projects
Handler: repository_name_search()

Pattern: *api*
Expands to: */*/*api*
Use case: Find all repos containing "api"
Handler: repository_pattern_search()

Pattern: automation*
Expands to: */*/automation*
Use case: Find repos starting with "automation"
Handler: repository_prefix_search()
```

### Organization-Only Patterns (Auto-expanded to `<org>/*/*`)
```
Pattern: pdidev
Expands to: pdidev/*/*
Use case: Find all repos in pdidev org
Handler: organization_exact_search()

Pattern: *dev*
Expands to: *dev*/*/*
Use case: Find orgs containing "dev"
Handler: organization_pattern_search()
```

## Level 2: Two Segment Patterns

### Organization + Repository Patterns
```
Pattern: pdidev/DevTools
Expands to: pdidev/*/DevTools
Use case: Find DevTools repo in pdidev org (any project)
Handler: org_repo_exact_search()

Pattern: pdidev/*api*
Expands to: pdidev/*/*api*
Use case: Find repos with "api" in pdidev org
Handler: org_repo_pattern_search()

Pattern: *dev*/DevTools
Expands to: *dev*/*/DevTools
Use case: Find DevTools in orgs containing "dev"
Handler: org_pattern_repo_exact_search()
```

### Organization + Project Patterns
```
Pattern: pdidev/Blue Cow
Expands to: pdidev/Blue Cow/*
Use case: Find all repos in pdidev/Blue Cow project
Handler: org_project_exact_search()

Pattern: pdidev/*backend*
Expands to: pdidev/*backend*/*
Use case: Find repos in pdidev projects containing "backend"
Handler: org_project_pattern_search()

Pattern: *dev*/Blue Cow
Expands to: *dev*/Blue Cow/*
Use case: Find repos in "Blue Cow" project of orgs containing "dev"
Handler: org_pattern_project_exact_search()
```

## Level 3: Three Segment Patterns

### All Exact Matches
```
Pattern: pdidev/Blue Cow/DevTools
Use case: Find specific repo in specific project/org
Handler: exact_triple_match()

Pattern: pdidev/Blue Cow/automation_smoke_signals
Use case: Find specific real repository
Handler: exact_triple_match()
```

### Single Wildcard Patterns
```
# Organization wildcard
Pattern: */Blue Cow/DevTools
Use case: Find DevTools in Blue Cow project across all orgs
Handler: project_repo_exact_search()

# Project wildcard
Pattern: pdidev/*/DevTools
Use case: Find DevTools in pdidev org across all projects
Handler: org_repo_exact_search()

# Repository wildcard
Pattern: pdidev/Blue Cow/*
Use case: Find all repos in pdidev/Blue Cow project
Handler: org_project_exact_search()
```

### Double Wildcard Patterns
```
# Org + Project wildcards
Pattern: */*/DevTools
Use case: Find DevTools repo across all orgs/projects
Handler: repo_only_search()

# Org + Repo wildcards
Pattern: */Blue Cow/*
Use case: Find all repos in Blue Cow project across orgs
Handler: project_only_search()

# Project + Repo wildcards
Pattern: pdidev/*/*
Use case: Find all repos in pdidev org
Handler: org_only_search()
```

### Triple Wildcard (Universal)
```
Pattern: */*/*
Use case: Find all repos across all providers/orgs/projects
Handler: universal_search()
```

## Level 4: Compound Partial Patterns

### Mixed Exact + Partial
```
Pattern: pdidev/Blue*/Dev*
Use case: pdidev org, projects starting with "Blue", repos starting with "Dev"
Handler: mixed_partial_search()

Pattern: *dev*/Blue Cow/*api*
Use case: Orgs containing "dev", exact "Blue Cow" project, repos containing "api"
Handler: complex_mixed_search()
```

### All Partial Patterns
```
Pattern: *dev*/*backend*/*api*
Use case: Complex multi-criteria search
Handler: full_partial_search()
```

## Provider-Specific Pattern Handling

### Azure DevOps Patterns
```
# All patterns work with project names containing spaces
Pattern: pdidev/Blue Cow/DevTools
Pattern: pdidev/Blue Cow/*api*
Pattern: */Blue Cow/DevTools

# Special handling for long project names
Pattern: pdidev/Rocket-To-Cosmos-Projects/*
Handler: azure_project_name_handler()
```

### GitHub Patterns
```
# No project segment (GitHub doesn't use projects like Azure DevOps)
Pattern: myorg//DevTools  (converted internally)
Pattern: myorg/*api*
Handler: github_pattern_adapter()
```

### BitBucket Patterns
```
# Similar to GitHub, projects are optional
Pattern: myworkspace//DevTools
Pattern: myworkspace/*api*
Handler: bitbucket_pattern_adapter()
```

## Algorithm Streamlining

### Handler Organization by Pattern Type

#### Exact Match Handlers
```python
def handle_exact_patterns(query_parts):
    """Handle patterns with no wildcards"""
    if len(query_parts) == 3 and no_wildcards(query_parts):
        return exact_triple_handler(query_parts)
    elif len(query_parts) == 2 and no_wildcards(query_parts):
        return exact_double_handler(query_parts)
    # ... etc

#### Single Wildcard Handlers
```python
def handle_single_wildcard(query_parts):
    """Handle patterns with exactly one wildcard"""
    wildcard_positions = find_wildcard_positions(query_parts)

    if wildcard_positions == [0]:  # org/*
        return org_wildcard_handler(query_parts)
    elif wildcard_positions == [1]:  # */project
        return project_wildcard_handler(query_parts)
    # ... etc
```

#### Partial Match Handlers
```python
def handle_partial_patterns(query_parts):
    """Handle patterns with partial wildcards (*text* or text*)"""
    partial_positions = find_partial_positions(query_parts)

    if is_complex_partial(partial_positions):
        return complex_partial_handler(query_parts)
    else:
        return simple_partial_handler(query_parts)
```

### Performance Optimization

#### Query Optimization Rules
1. **Prefer exact matches**: `org/project/repo` fastest
2. **Avoid leading wildcards**: `org/*/*` faster than `*/project/*`
3. **Use specific segments**: More specific = faster filtering
4. **Cache partial results**: Cache intermediate results for compound queries

#### Handler Selection Algorithm
```python
def select_optimal_handler(query_parts):
    """Select most efficient handler for query pattern"""

    # Fast path for exact matches
    if is_exact_match(query_parts):
        return ExactMatchHandler()

    # Fast path for single wildcards
    if is_single_wildcard(query_parts):
        return SingleWildcardHandler()

    # Complex patterns use general handler
    return GeneralPatternHandler()
```

## Training and Documentation

### Pattern Examples by Use Case

#### Common Repository Searches
```bash
# Find all API repositories
mgit list "*/*/*api*"

# Find all test repositories
mgit list "*/*/*test*"

# Find repositories by prefix
mgit list "*/*/automation*"
```

#### Organization-Based Searches
```bash
# All repos in specific org
mgit list "pdidev/*/*"

# Backend repos across orgs
mgit list "*/*/*backend*"
```

#### Project-Based Searches (Azure DevOps)
```bash
# All repos in Blue Cow project
mgit list "*/Blue Cow/*"

# API repos in Blue Cow project
mgit list "*/Blue Cow/*api*"
```

### Best Practices

1. **Start Specific**: Use exact org/project when possible
2. **Avoid Universal**: `/*/*/*` is slow across many providers
3. **Use Provider Filtering**: `--provider ado_pdidev` for faster results
4. **Combine Intelligently**: Mix exact + partial strategically
5. **Test Patterns**: Use `--limit 5` to test before full queries

### Pattern Debugging

```bash
# Debug pattern parsing
mgit list "pdidev/*/*" --debug-pattern

# Show pattern expansion
mgit list "DevTools" --show-expansion

# Validate pattern syntax
mgit list "pdidev/*" --validate-only
```

## Implementation Status

### ✅ Completed
- [x] Basic pattern parsing
- [x] Wildcard expansion for short patterns
- [x] Character validation (including spaces)
- [x] Provider-specific handling

### 🚧 In Progress
- [ ] Handler optimization by pattern type
- [ ] Performance profiling for different patterns
- [ ] Pattern suggestion system

### 📋 Planned
- [ ] Advanced pattern caching
- [ ] Pattern usage analytics
- [ ] Interactive pattern builder
- [ ] Pattern migration tools
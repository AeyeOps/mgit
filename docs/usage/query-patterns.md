# Query Patterns Guide

mgit uses a flexible pattern matching system for discovering repositories across all configured providers.

## Pattern Syntax

Patterns follow the format: `organization/project/repository`

- **Azure DevOps**: All three parts are used
- **GitHub/BitBucket**: Only organization and repository parts are used (project is ignored)

### Wildcards

- `*` - Matches any sequence of characters
- Pattern matching is case-insensitive
- Partial matches are supported

## Common Patterns

### Universal Patterns

```bash
# All repositories everywhere
mgit list "*/*/*"

# All repositories in a specific organization
mgit list "myorg/*/*"

# All repositories with specific prefix
mgit list "*/*/api-*"

# All repositories with specific suffix
mgit list "*/*/*-service"

# All repositories containing a word
mgit list "*/*/*payment*"
```

### Organization-Specific Patterns

```bash
# All repos in myorg
mgit list "myorg/*/*"

# Specific project in Azure DevOps
mgit list "myorg/backend/*"

# Cross-organization search
mgit list "*/ProjectName/*"
```

### Repository Name Patterns

```bash
# Find all API repos
mgit list "*/*/api-*"

# Find all microservices
mgit list "*/*/*-service"

# Find all frontend repos
mgit list "*/*/*-ui"

# Find repos by keyword
mgit list "*/*/*customer*"
```

## Advanced Usage

### Combining with Commands

```bash
# Clone all matching repos
mgit clone-all "myorg/*/api-*" ./api-repos

# Update specific repos
mgit pull-all "myorg/backend/*" ./backend-repos

# Check status of pattern-matched repos
mgit list "*/*/payment*" | xargs -I {} mgit status {}
```

### Output Formats

```bash
# Default table output
mgit list "myorg/*/*"

# JSON for automation
mgit list "myorg/*/*" --format json

# Limit results
mgit list "*/*/*" --limit 100

# Count repositories
mgit list "myorg/*/*" --format json | jq length
```

## Provider-Specific Behavior

### Azure DevOps
- Uses full three-part pattern: `organization/project/repository`
- Project level filtering is supported
- Example: `myorg/DataEngineering/*`

### GitHub
- Uses two-part pattern: `organization/repository`
- Middle part (project) is ignored but required for consistency
- Example: `myorg/*/my-repo` (middle * is ignored)

### BitBucket
- Uses two-part pattern: `workspace/repository`
- Middle part (project) is ignored but required for consistency
- Example: `myworkspace/*/my-repo` (middle * is ignored)

## Performance Tips

1. **Be specific when possible**
   - `myorg/backend/*` is faster than `*/backend/*`
   - `myorg/*/api-*` is faster than `*/*/api-*`

2. **Use limits for large searches**
   ```bash
   mgit list "*/*/*" --limit 500
   ```

3. **Filter at the source**
   - Use patterns rather than post-processing
   - Provider APIs filter results, reducing network traffic

## Troubleshooting

### No results found
- Verify provider is configured: `mgit config --list`
- Check pattern syntax (three parts required)
- Try broader pattern: `*/*/*`

### Too many results
- Use more specific patterns
- Apply `--limit` flag
- Filter by organization or project

### Pattern not matching expected repos
- Remember patterns are case-insensitive
- Check for typos in organization/project names
- Use `*` liberally for partial matches

## Examples by Use Case

### DevOps Team Scenarios

```bash
# Find all infrastructure repos
mgit list "*/*/infra*" 
mgit list "*/*/terraform-*"

# Find all API services
mgit list "*/*/api-*"
mgit list "*/*/*-api"

# Find database-related repos
mgit list "*/*/*db*"
mgit list "*/*/*database*"
```

### Migration Scenarios

```bash
# Find all repos to migrate from org
mgit list "old-org/*/*" --format json > repos-to-migrate.json

# Clone all repos for migration
mgit clone-all "old-org/*/*" ./migration-workspace
```

### Audit Scenarios

```bash
# Find all public repos (if supported by provider)
mgit list "*/*/*" --format json | jq '.[] | select(.visibility == "public")'

# Find repos by naming convention
mgit list "*/*/prod-*"  # Production repos
mgit list "*/*/test-*"  # Test repos
mgit list "*/*/dev-*"   # Development repos
```
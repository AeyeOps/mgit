# Multi-Provider Command Structure Design

## Design Principles

1. **Backward Compatibility**: Existing commands must continue to work without modification
2. **Provider Flexibility**: Support provider-specific features while maintaining common interface
3. **Intuitive Hierarchy**: Commands should reflect the natural hierarchy of each provider
4. **Consistent Experience**: Similar operations should have similar syntax across providers

## Command Structure Evolution

### Current Structure (Azure DevOps Only)
```bash
mgit clone-all <project> <path>
mgit pull-all <project> <path>
mgit login --org <url> --pat <token>
mgit config --show
mgit generate-env
```

### Proposed Multi-Provider Structure

#### Option 1: Provider as Global Flag (Recommended)
```bash
# Set default provider
mgit config --provider github

# Override provider for specific command
mgit --provider bitbucket clone-all <workspace> <project> <path>
mgit --provider github clone-all <organization> <path>
mgit --provider azuredevops clone-all <project> <path>

# Short form
mgit -p github clone-all octocat ./repos
```

#### Option 2: Provider as Subcommand
```bash
mgit github clone-all <organization> <path>
mgit bitbucket clone-all <workspace> <project> <path>
mgit azuredevops clone-all <project> <path>
```

#### Option 3: Provider in Command
```bash
mgit clone-all --from github <organization> <path>
mgit clone-all --from bitbucket <workspace> <project> <path>
```

## Detailed Command Specifications

### 1. Provider Configuration

```bash
# Show current provider configuration
mgit providers
mgit providers --list
mgit providers --show github

# Set default provider
mgit config --provider github
mgit config -p github

# Configure provider credentials
mgit config github --token <token>
mgit config bitbucket --username <user> --app-password <password>
mgit config azuredevops --org <url> --pat <token>
```

### 2. Authentication Commands

```bash
# Provider-specific login
mgit login  # Uses default provider
mgit login --provider github
mgit login -p bitbucket

# Test authentication
mgit auth test
mgit auth test --provider github
mgit auth test --all-providers

# Logout/clear credentials
mgit logout
mgit logout --provider github
mgit logout --all
```

### 3. Repository Listing

```bash
# List repositories
mgit list repos <organization> [project]
mgit list repos octocat  # GitHub
mgit list repos myworkspace PROJ  # BitBucket with project
mgit list repos MyProject  # Azure DevOps

# With filters
mgit list repos <org> --filter "name:*api*"
mgit list repos <org> --language python
mgit list repos <org> --archived false
```

### 4. Clone Operations

```bash
# Basic clone all
mgit clone-all <organization> [project] <path>

# Examples by provider
mgit clone-all octocat ./github-repos  # GitHub
mgit clone-all myworkspace ./bb-repos  # BitBucket (all repos)
mgit clone-all myworkspace PROJ ./bb-repos  # BitBucket (project repos)
mgit clone-all MyProject ./ado-repos  # Azure DevOps

# With options
mgit clone-all <org> <path> --concurrency 10
mgit clone-all <org> <path> --update-mode pull
mgit clone-all <org> <path> --filter "language:python"
mgit clone-all <org> <path> --exclude "archived:true"
```

### 5. Pull Operations

```bash
# Pull all repositories
mgit pull-all <path>
mgit pull-all ./repos --concurrency 5
mgit pull-all ./repos --exclude-forks
```

### 6. Advanced Operations

```bash
# Clone from multiple providers
mgit clone-multi ./all-repos

# Repository search across providers
mgit search "machine learning" --all-providers
mgit search "python" --provider github --stars ">100"

# Bulk operations
mgit bulk archive <org> --repos "old-*"
mgit bulk transfer <source-org> <dest-org> --repos <list>
```

## Provider-Specific Adaptations

### GitHub Adaptations
Since GitHub doesn't have projects:
```bash
# Use repository name patterns as pseudo-projects
mgit clone-all octocat "frontend-*" ./repos
mgit clone-all octocat --topic web ./repos
mgit clone-all octocat --team engineering ./repos
```

### BitBucket Adaptations
Projects are optional in BitBucket:
```bash
# Clone all workspace repos
mgit clone-all myworkspace ./repos

# Clone specific project repos
mgit clone-all myworkspace --project PROJ ./repos
```

### Azure DevOps Adaptations
Maintain current behavior:
```bash
# Organization inferred from config or --org flag
mgit clone-all MyProject ./repos
mgit clone-all MyProject ./repos --org https://dev.azure.com/myorg
```

## Configuration File Impact

### Current Format
```ini
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/myorg
AZURE_DEVOPS_EXT_PAT=<token>
DEFAULT_CONCURRENCY=4
DEFAULT_UPDATE_MODE=skip
```

### New Multi-Provider Format
```ini
# Global settings
DEFAULT_PROVIDER=github
DEFAULT_CONCURRENCY=4
DEFAULT_UPDATE_MODE=skip

# Provider-specific sections
[providers.azuredevops]
default_org=https://dev.azure.com/myorg
pat=<token>

[providers.github]
default_org=octocat
token=<token>
clone_protocol=https  # or ssh

[providers.bitbucket]
default_workspace=myworkspace
username=<username>
app_password=<password>
```

## Command Aliases for Convenience

```bash
# Short aliases
mgit gh  # Alias for --provider github
mgit bb  # Alias for --provider bitbucket
mgit az  # Alias for --provider azuredevops

# Usage
mgit gh clone-all octocat ./repos
mgit bb clone-all myworkspace ./repos
```

## Error Messages and Help

### Provider-Specific Help
```bash
mgit clone-all --help
# Shows general help with provider examples

mgit clone-all --help --provider github
# Shows GitHub-specific help and examples
```

### Clear Error Messages
```
Error: GitHub doesn't support project hierarchy. Use organization name only.
Hint: mgit clone-all octocat ./repos

Error: BitBucket workspace 'myworkspace' requires authentication.
Hint: Run 'mgit login --provider bitbucket' first.
```

## Migration Path for Existing Users

1. **Phase 1**: Detect old-style usage and provide warnings
   ```
   Warning: Using legacy Azure DevOps configuration.
   Consider updating to: mgit config azuredevops --org <url> --pat <token>
   ```

2. **Phase 2**: Auto-migration of config files
   ```
   Info: Migrating configuration to new multi-provider format...
   Old configuration backed up to ~/.config/mgit/config.backup
   ```

3. **Phase 3**: Support both formats for transition period

## Interactive Mode (Future Enhancement)

```bash
mgit setup
# Interactive provider setup wizard

mgit clone-interactive
# ? Select provider: (github/bitbucket/azuredevops)
# ? Enter organization: octocat
# ? Select repositories: (space to select, enter to confirm)
# ? Clone to: ./repos
```

## Environment Variable Support

Maintain support for environment variables with new naming:

```bash
# Provider selection
MGIT_PROVIDER=github

# Provider-specific (backward compatible)
AZURE_DEVOPS_ORG_URL=...
AZURE_DEVOPS_EXT_PAT=...

# New format
MGIT_GITHUB_TOKEN=...
MGIT_BITBUCKET_USERNAME=...
MGIT_BITBUCKET_APP_PASSWORD=...
```

## Command Completion

Enhanced shell completion supporting provider-specific options:

```bash
mgit clone-all <TAB>
# Shows organizations from current provider

mgit --provider github clone-all <TAB>
# Shows GitHub organizations

mgit clone-all octocat <TAB>
# Shows path suggestions
```
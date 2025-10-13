# Azure DevOps Usage Guide for mgit

This guide provides step-by-step instructions for using mgit with Azure DevOps, including authentication setup, repository management, and troubleshooting.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Creating a Personal Access Token (PAT)](#creating-a-personal-access-token-pat)
- [Configuration](#configuration)
- [Common Commands](#common-commands)
- [Project-Based Repository Management](#project-based-repository-management)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- An Azure DevOps account with access to your organization
- Git installed on your system
- mgit installed (`pip install mgit`)

## Creating a Personal Access Token (PAT)

1. **Navigate to Azure DevOps**: Go to https://dev.azure.com/[your-organization]
   
2. **Access User Settings**: Click on your profile icon (top right) → "Personal access tokens"

3. **Create New Token**:
   - Click "New Token"
   - **Name**: Give it a descriptive name (e.g., "mgit-access")
   - **Organization**: Select your organization (e.g., `myorg`)
   - **Expiration**: Set an appropriate expiration date (max 1 year)
   - **Scopes**: Select the following minimum scopes:
     - Code: Read & Write
     - Project and Team: Read
     - Work Items: Read (if you plan to use issue tracking)
   
4. **Copy the Token**: Once created, copy the token immediately - you won't be able to see it again!

## Configuration

### Method 1: Using mgit login command (Recommended)

```bash
# Login to Azure DevOps
mgit login --provider azuredevops --name work_ado
# Enter URL: https://dev.azure.com/myorg
# Enter token when prompted

# Verify configuration
mgit config --show work_ado
```

### Method 2: Manual YAML configuration

Edit `~/.config/mgit/config.yaml`:

```yaml
# Modern unified configuration
global:
  default_concurrency: 10
  default_update_mode: pull

providers:
  work_ado:
    url: https://dev.azure.com/myorg
    user: ""                           # Not used for Azure DevOps PAT auth
    token: YOUR_PAT_HERE
    workspace: ""                      # Optional
```

### Method 3: Legacy environment variables (Deprecated)

**Note**: Environment variables are deprecated. Use YAML configuration instead.

```bash
# Legacy environment variables (still supported but not recommended)
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/myorg"
export AZURE_DEVOPS_EXT_PAT="YOUR_PAT_HERE"
```

## Common Commands

### Discover and clone by project
```bash
# List repositories in a project (org/project/repo pattern)
mgit list "myorg/MyProject/*" --limit 10

# Clone or update all repositories in a project
mgit sync "myorg/MyProject/*" ./repos --provider work_ado

# Control concurrency
mgit sync "myorg/DataPlatform/*" ./data-platform-repos --provider work_ado --concurrency 10

# Pattern-filtered selection within a project
mgit sync "myorg/MyProject/*-service" ./repos --provider work_ado
mgit sync "myorg/MyProject/api-*" ./repos --provider work_ado
mgit sync "myorg/MyProject/*-frontend" ./repos --provider work_ado
```

## Project-Based Repository Management

Azure DevOps organizes repositories within projects. This hierarchical structure means:

1. **Projects contain repositories**: Each project can have multiple repositories
2. **Access is project-based**: Your PAT needs access to specific projects
3. **Repository names must be unique within a project**: But can be duplicated across projects

### Working with multiple projects

```bash
# Clone repos from multiple projects
mgit sync "myorg/Frontend/*" ./frontend-repos --provider work_ado
mgit sync "myorg/Backend/*" ./backend-repos --provider work_ado
mgit sync "myorg/Infrastructure/*" ./infra-repos --provider work_ado

# Create a workspace structure
mkdir -p workspace/{frontend,backend,infrastructure}
mgit sync "myorg/Frontend/*" ./workspace/frontend --provider work_ado
mgit sync "myorg/Backend/*" ./workspace/backend --provider work_ado
mgit sync "myorg/Infrastructure/*" ./workspace/infrastructure --provider work_ado
```

### Batch operations across projects

```bash
# Update all repos in multiple project directories
for project in Frontend Backend Infrastructure; do
  mgit sync "myorg/$project/*" "./workspace/$project" --provider work_ado
done
```

## Troubleshooting

### Authentication Errors

**Error**: "TF401019: The Git repository with name or identifier does not exist or you do not have permissions"

**Solutions**:
1. Verify your PAT hasn't expired
2. Ensure your PAT has the correct scopes (Code: Read & Write)
3. Check that you have access to the project
4. Verify the organization URL is correct (include https://)

```bash
# Test authentication by attempting to login
mgit login --provider azuredevops --name work_ado
```

### Organization URL Issues

**Common mistakes**:
- ❌ `myorg.visualstudio.com` (old format)
- ❌ `dev.azure.com/myorg/` (trailing slash)
- ✅ `https://dev.azure.com/myorg` (correct format)

### Rate Limiting

Azure DevOps has rate limits for API calls:
- **Anonymous**: 100 requests per minute
- **Authenticated**: 1000 requests per minute

If you hit rate limits:
```bash
# Reduce concurrency
mgit sync "myorg/LargeProject/*" ./repos --provider work_ado --concurrency 3
```

### SSL/TLS Errors

If behind a corporate proxy:
```bash
# Disable SSL verification (not recommended for production)
export GIT_SSL_VERIFY=false

# Or configure proxy
export HTTPS_PROXY=http://proxy.company.com:8080
```

### Repository Access Issues

**Error**: "The project with name or identifier does not exist"

**Check**:
1. Project name is correct (case-sensitive)
2. You have access to the project
3. The project exists in the specified organization

```bash
# Verify access by attempting to clone from a known project
# If you don't have access, the clone operation will fail with appropriate error messages
```

## Best Practices

1. **Use project-specific directories**: Organize cloned repos by project
2. **Regular PAT rotation**: Renew PATs before expiration
3. **Minimal PAT scopes**: Only grant necessary permissions
4. **Use SSH for better performance**: Configure SSH keys in Azure DevOps
5. **Leverage .gitignore**: Add mgit config files to .gitignore

## Advanced Usage

### Custom clone configurations

Note: Shallow clones and branch selection are not exposed as sync options. Use git commands after cloning if you need specialized history or branch setups.

### Integration with CI/CD

```yaml
# Azure Pipelines example
steps:
- script: |
    pip install mgit
    mgit login --provider azuredevops --org $(System.CollectionUri) --token $(System.AccessToken)
    # Match current project across the configured provider
    mgit sync "*/$(System.TeamProject)/*" . --provider work_ado
  displayName: 'Sync all repositories in project'
```

## Security Considerations

1. **Never commit PATs**: Add config files to .gitignore
2. **Use environment variables in CI/CD**: Don't hardcode credentials
3. **Rotate PATs regularly**: Set calendar reminders for expiration
4. **Use minimal scopes**: Only grant necessary permissions
5. **Audit PAT usage**: Regularly review PAT activity in Azure DevOps

## Examples with Real Organization

### Complete workflow example

```bash
# 1. Initial setup
mgit login --provider azuredevops --org https://dev.azure.com/myorg --token YOUR_PAT_HERE --name work_ado

# 2. Discover repositories in a project
mgit list "myorg/DataEngineering/*" --limit 10

# 3. Sync all repos from the project
mkdir -p ~/workspace/data-engineering
mgit sync "myorg/DataEngineering/*" ~/workspace/data-engineering --provider work_ado --concurrency 10

# 4. Later, update all repos
cd ~/workspace/data-engineering
mgit sync "myorg/DataEngineering/*" . --provider work_ado

# 5. Sync only specific repos by pattern
mgit sync "myorg/DataEngineering/*-etl-*" ~/workspace/etl-services --provider work_ado
```

### Multi-project management

```bash
#!/bin/bash
# Script to manage multiple Azure DevOps projects

PROJECTS=("Frontend" "Backend" "DataEngineering" "Infrastructure" "DevOps")
BASE_DIR="$HOME/workspace/myorg"

# Clone all projects
for project in "${PROJECTS[@]}"; do
  echo "Syncing repositories from project: $project"
  mkdir -p "$BASE_DIR/$project"
  mgit sync "myorg/$project/*" "$BASE_DIR/$project" --provider work_ado --concurrency 5
done

# Update all projects
for project in "${PROJECTS[@]}"; do
  echo "Updating repositories in project: $project"
  mgit sync "myorg/$project/*" "$BASE_DIR/$project" --provider work_ado
done
```

## Related Documentation

- [Provider Feature Matrix](./provider-feature-matrix.md)
- [Configuration Schema](../configuration/configuration-schema-design.md)
- [Multi-Provider Design](../architecture/multi-provider-design.md)

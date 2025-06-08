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
mgit login --provider azdevops --org https://dev.azure.com/myorg --token YOUR_PAT_HERE

# Verify configuration
mgit config --show
```

### Method 2: Using configuration file

Create or edit `~/.config/mgit/config`:

```bash
# Azure DevOps configuration
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/myorg
AZURE_DEVOPS_EXT_PAT=YOUR_PAT_HERE

# Optional: Set defaults
DEFAULT_CONCURRENCY=10
DEFAULT_UPDATE_MODE=pull
```

### Method 3: Using environment variables

```bash
# Set environment variables
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/myorg"
export AZURE_DEVOPS_EXT_PAT="YOUR_PAT_HERE"

# Optional: Set defaults
export DEFAULT_CONCURRENCY="10"
export DEFAULT_UPDATE_MODE="pull"
```

## Common Commands

### Clone repositories from a project
To see what repositories are available in a project, you'll need to use the Azure DevOps web interface or API directly. mgit focuses on bulk operations rather than listing.

### Clone all repositories from a project
```bash
# Clone all repos from a project
mgit clone-all --provider azdevops --project "MyProject" --destination ./repos

# With concurrency control (default is 5)
mgit clone-all --provider azdevops --project "DataPlatform" --destination ./data-platform-repos --concurrency 10

# Clone and update existing repos
mgit clone-all --provider azdevops --project "MyProject" --destination ./repos --update-mode merge
```

### Update all repositories
```bash
# Pull latest changes for all repos
mgit pull-all --provider azdevops --project "MyProject" --path ./repos

# With specific update strategy
mgit pull-all --provider azdevops --project "DataPlatform" --path ./data-platform-repos --strategy rebase
```

### Filter repositories
```bash
# Clone only repos matching a pattern
mgit clone-all --provider azdevops --project "MyProject" --destination ./repos --filter "*-service"

# Clone repos with multiple filters
mgit clone-all --provider azdevops --project "MyProject" --destination ./repos --filter "api-*" --filter "*-frontend"
```

## Project-Based Repository Management

Azure DevOps organizes repositories within projects. This hierarchical structure means:

1. **Projects contain repositories**: Each project can have multiple repositories
2. **Access is project-based**: Your PAT needs access to specific projects
3. **Repository names must be unique within a project**: But can be duplicated across projects

### Working with multiple projects

```bash
# Clone repos from multiple projects
mgit clone-all --provider azdevops --project "Frontend" --destination ./frontend-repos
mgit clone-all --provider azdevops --project "Backend" --destination ./backend-repos
mgit clone-all --provider azdevops --project "Infrastructure" --destination ./infra-repos

# Create a workspace structure
mkdir -p workspace/{frontend,backend,infrastructure}
mgit clone-all --provider azdevops --project "Frontend" --destination ./workspace/frontend
mgit clone-all --provider azdevops --project "Backend" --destination ./workspace/backend
mgit clone-all --provider azdevops --project "Infrastructure" --destination ./workspace/infrastructure
```

### Batch operations across projects

```bash
# Update all repos in multiple project directories
for project in Frontend Backend Infrastructure; do
    mgit pull-all --provider azdevops --project "$project" --path "./workspace/$project"
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
mgit login --provider azdevops
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
mgit clone-all --provider azdevops --project "LargeProject" --destination ./repos --concurrency 3
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

```bash
# Clone with shallow history
mgit clone-all --provider azdevops --project "MyProject" --destination ./repos --shallow --depth 1

# Clone specific branches
mgit clone-all --provider azdevops --project "MyProject" --destination ./repos --branch develop
```

### Integration with CI/CD

```yaml
# Azure Pipelines example
steps:
- script: |
    pip install mgit
    mgit login --provider azdevops --org $(System.CollectionUri) --token $(System.AccessToken)
    mgit pull-all --provider azdevops --project "$(System.TeamProject)" --path ./
  displayName: 'Update all repositories'
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
mgit login --provider azdevops --org https://dev.azure.com/myorg --token YOUR_PAT_HERE

# 2. Clone repos from a known project
# (Use Azure DevOps web interface to explore available projects and repositories)

# 3. Clone all repos from the project
mkdir -p ~/workspace/data-engineering
mgit clone-all --provider azdevops --project "DataEngineering" \
    --destination ~/workspace/data-engineering \
    --concurrency 10

# 4. Later, update all repos
cd ~/workspace/data-engineering
mgit pull-all --provider azdevops --project "DataEngineering" --path .

# 5. Clone only specific repos
mgit clone-all --provider azdevops --project "DataEngineering" \
    --destination ~/workspace/etl-services \
    --filter "*-etl-*"
```

### Multi-project management

```bash
#!/bin/bash
# Script to manage multiple Azure DevOps projects

PROJECTS=("Frontend" "Backend" "DataEngineering" "Infrastructure" "DevOps")
BASE_DIR="$HOME/workspace/myorg"

# Clone all projects
for project in "${PROJECTS[@]}"; do
    echo "Cloning repositories from project: $project"
    mkdir -p "$BASE_DIR/$project"
    mgit clone-all --provider azdevops --project "$project" \
        --destination "$BASE_DIR/$project" \
        --concurrency 5
done

# Update all projects
for project in "${PROJECTS[@]}"; do
    echo "Updating repositories in project: $project"
    mgit pull-all --provider azdevops --project "$project" \
        --path "$BASE_DIR/$project"
done
```

## Related Documentation

- [Provider Feature Matrix](./provider-feature-matrix.md)
- [Configuration Schema](../configuration/configuration-schema-design.md)
- [Multi-Provider Design](../architecture/multi-provider-design.md)
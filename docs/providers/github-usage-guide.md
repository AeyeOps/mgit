# GitHub Usage Guide for mgit

This guide provides comprehensive instructions for using mgit with GitHub, including authentication, organization management, and working with both personal and organizational repositories.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Creating a Personal Access Token](#creating-a-personal-access-token)
- [Configuration](#configuration)
- [Common Commands](#common-commands)
- [Organization vs User Repositories](#organization-vs-user-repositories)
- [Rate Limiting](#rate-limiting)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Prerequisites

- A GitHub account (personal or organization)
- Git installed and configured
- mgit installed (`pip install mgit`)

## Creating a Personal Access Token

### Classic Personal Access Token (Recommended for mgit)

1. **Go to GitHub Settings**: Click your profile photo → Settings

2. **Navigate to Developer Settings**: 
   - Scroll to the bottom of the sidebar
   - Click "Developer settings"

3. **Create Classic Token**:
   - Click "Personal access tokens" → "Tokens (classic)"
   - Click "Generate new token" → "Generate new token (classic)"

4. **Configure Token**:
   - **Note**: Give it a descriptive name (e.g., "mgit-cli-access")
   - **Expiration**: Choose expiration (or "No expiration" for permanent)
   - **Scopes**: Select the following:
     - `repo` (Full control of private repositories)
     - `read:org` (Read org and team membership)
     - `read:user` (Read user profile data)
     - `workflow` (If you need to access GitHub Actions)

5. **Generate and Copy**: Click "Generate token" and copy immediately!

### Fine-grained Personal Access Token (Advanced)

For enhanced security with specific repository access:

1. Go to Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Set expiration and repository access
4. Configure permissions:
   - Repository permissions: Contents (Read/Write), Metadata (Read)
   - Account permissions: None required for basic operations

## Configuration

### Method 1: Using mgit login command

```bash
# For personal repositories
mgit login --provider github --token YOUR_GITHUB_TOKEN

# For organization repositories
mgit login --provider github --token YOUR_GITHUB_TOKEN --org myusername

# Verify configuration
mgit config --show
```

### Method 2: Configuration file

Create or edit `~/.config/mgit/config`:

```bash
# GitHub configuration
GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: default organization
GITHUB_ORG=AeyeOps

# Optional: Set defaults
DEFAULT_CONCURRENCY=10
DEFAULT_UPDATE_MODE=pull
```

### Method 3: Environment variables

```bash
# Set GitHub token
export GITHUB_PAT="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Optional: Set default organization
export GITHUB_ORG="myusername"

# Optional: Set defaults
export DEFAULT_CONCURRENCY="10"
export DEFAULT_UPDATE_MODE="pull"
```

## Common Commands

### Working with repositories
To see what repositories are available, use the GitHub web interface or API directly. mgit focuses on bulk clone and update operations.

### Clone repositories

```bash
# Clone all repos from a user/organization
# For personal repos, use your username
mgit clone-all your-username ./my-repos --provider github

# Clone all repos from an organization
mgit clone-all myusername ./myusername-repos --provider github

# Clone all repos from AeyeOps organization
mgit clone-all AeyeOps ./aeyeops-repos --provider github

# Clone with concurrency control
mgit clone-all myusername ./repos -c 10 --provider github
```

### Update repositories

```bash
# Update all repos in a directory
mgit pull-all myusername ./myusername-repos --provider github
```

## Organization vs User Repositories

### Personal Repositories

When working without specifying an organization, mgit accesses your personal repositories:

```bash
# Clone all personal repos (use your GitHub username)
mgit clone-all your-username ~/personal-repos --provider github
```

### Organization Repositories

For organization repositories, specify the org parameter:

```bash
# Clone from multiple organizations
mgit clone-all myusername ./myusername --provider github
mgit clone-all AeyeOps ./aeyeops --provider github
```

### Mixed Repository Management

Create a structured workspace for multiple contexts:

```bash
#!/bin/bash
# Organize repos by owner

# Personal repos (use your username)
mgit clone-all your-username ~/github/personal --provider github

# Organization repos
ORGS=("myusername" "AeyeOps" "MyCompany")
for org in "${ORGS[@]}"; do
    mgit clone-all "$org" "~/github/orgs/$org" --provider github
done
```

## Rate Limiting

GitHub enforces API rate limits:

### Rate Limit Details

- **Unauthenticated**: 60 requests per hour
- **Authenticated**: 5,000 requests per hour
- **GitHub Enterprise**: 15,000 requests per hour

### Check Rate Limit Status

```bash
# Check current rate limit
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
```

### Working with Rate Limits

```bash
# Reduce concurrency to avoid rate limits
mgit clone-all large-org ./repos -c 3 --provider github
```

### Rate Limit Best Practices

1. **Use authentication**: Always use a PAT for higher limits
2. **Implement caching**: Cache repository lists when possible
3. **Batch operations**: Group operations to minimize API calls
4. **Monitor usage**: Check rate limit headers in responses

## Troubleshooting

### Authentication Issues

**Error**: "Bad credentials" or "401 Unauthorized"

```bash
# Verify token is valid
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user

# Check token scopes
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
```

**Common causes**:
- Token expired or revoked
- Incorrect token format (should start with `ghp_` for classic tokens)
- Missing required scopes
- Token copied incorrectly

### Organization Access

**Error**: "Not Found" when accessing organization repos

**Solutions**:
1. Verify organization name (case-sensitive)
2. Ensure you're a member of the organization
3. Check if organization has enabled third-party access
4. For private orgs, ensure token has `read:org` scope

```bash
# List organizations you have access to
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user/orgs
```

### SSH vs HTTPS

**Issue**: Repeated password prompts

**Solution**: Configure SSH keys or credential caching

```bash
# mgit uses HTTPS URLs by default
# To use SSH, configure git globally or per-repository after cloning

# Configure credential caching
git config --global credential.helper cache
git config --global credential.helper 'cache --timeout=3600'
```

### Two-Factor Authentication (2FA)

If you have 2FA enabled:
1. You MUST use a personal access token (not your password)
2. The token replaces your password in all Git operations
3. SSH keys are recommended for better experience

## Best Practices

### 1. Security

```yaml
# .gitignore - Always exclude config files
.mgit/
~/.config/mgit/
*.token
*.pat
```

### 2. Token Management

```bash
# Create tokens with minimal scopes
# For read-only operations:
- repo:status
- public_repo
- read:org

# For full operations:
- repo
- read:org
- read:user
```

### 3. Organization Structure

```
~/github/
├── personal/          # Personal repositories
├── work/             # Work organization
│   ├── frontend/     # Filtered by type
│   ├── backend/
│   └── infrastructure/
└── opensource/       # Open source contributions
    ├── myusername/
    └── AeyeOps/
```

### 4. Efficient Workflows

```bash
# Create aliases for common operations
alias mgit-update-all='mgit pull-all --provider github --path .'
alias mgit-clone-org='mgit clone-all'
```

## Advanced Usage

### Working with GitHub Enterprise

```bash
# Configure for GitHub Enterprise
mgit login --provider github --org https://github.company.com --token YOUR_TOKEN
```

### Filtering and Selection

```bash
# mgit clones all repositories from the specified organization
# Use the web interface to identify specific repos you want to clone
```

### Batch Operations

```bash
#!/bin/bash
# Update multiple organizations

ORGS=("myusername" "AeyeOps" "CompanyOrg")
BASE_DIR="$HOME/github/orgs"

for org in "${ORGS[@]}"; do
    echo "Updating repositories for $org..."
    if [ -d "$BASE_DIR/$org" ]; then
        mgit pull-all "$org" "$BASE_DIR/$org" --provider github
    else
        echo "Directory $BASE_DIR/$org not found, cloning..."
        mgit clone-all "$org" "$BASE_DIR/$org" --provider github
    fi
done
```

### CI/CD Integration

```yaml
# GitHub Actions example
name: Update All Repos
on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - name: Install mgit
        run: pip install mgit
        
      - name: Configure mgit
        run: |
          mgit login --provider github --token ${{ secrets.GITHUB_TOKEN }}
          
      - name: Update repositories
        run: |
          mgit pull-all ${{ github.repository_owner }} ./repos --provider github
```

### Repository Statistics

```bash
# Clone repositories from organizations
mgit clone-all myusername ./repos --provider github
mgit clone-all AeyeOps ./repos --provider github
```

## Working with Specific Examples

### Example 1: Managing myusername repositories

```bash
# Initial setup
mgit login --provider github --token ghp_xxxxxxxxxxxx --org myusername

# Clone all repositories
mkdir -p ~/projects/myusername
mgit clone-all myusername ~/projects/myusername --provider github

# Regular updates
cd ~/projects/myusername
mgit pull-all myusername . --provider github

# Clone all projects
mgit clone-all myusername ~/projects/myusername-active --provider github
```

### Example 2: Working with AeyeOps organization

```bash
# Setup for AeyeOps
mgit login --provider github --token ghp_xxxxxxxxxxxx

# Clone all AeyeOps repos
mgit clone-all AeyeOps ~/aeyeops/all --provider github
```

### Example 3: Personal repository management

```bash
# Backup all personal repos (use your username)
mgit clone-all your-username ~/github-backup/personal --provider github
```

## Performance Optimization

### Shallow Clones

```bash
# Clone repositories
mgit clone-all myusername ./repos --provider github
```

### Parallel Operations

```bash
# Increase concurrency for faster cloning
mgit clone-all large-org ./repos -c 20 --provider github
```

### Selective Updates

```bash
# Update all repos
mgit pull-all org-name ./repos --provider github
```

## Security Recommendations

1. **Token Scopes**: Use minimal required scopes
2. **Token Rotation**: Rotate tokens every 90 days
3. **Separate Tokens**: Use different tokens for different purposes
4. **Audit Logs**: Regularly review token usage in GitHub settings
5. **SSH Keys**: Prefer SSH keys for regular development work

## Related Documentation

- [Provider Feature Matrix](./provider-feature-matrix.md)
- [Configuration Schema](../configuration/configuration-schema-design.md)
- [Multi-Provider Design](../architecture/multi-provider-design.md)
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

### Method 1: Using mgit login command (Recommended)

```bash
# Login to GitHub
mgit login --provider github --name personal_gh
# Enter token when prompted (format: ghp_...)

# Verify configuration
mgit config --show personal_gh
```

### Method 2: Manual YAML configuration

Edit `~/.config/mgit/config.yaml`:

```yaml
# Modern unified configuration
global:
  default_concurrency: 10
  default_update_mode: pull

providers:
  personal_gh:
    url: https://api.github.com
    user: your-github-username
    token: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    workspace: ""                      # Optional organization name
```

### Method 3: Legacy environment variables (Deprecated)

**Note**: Environment variables are deprecated. Use YAML configuration instead.

```bash
# Legacy environment variables (still supported but not recommended)
export GITHUB_PAT="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export GITHUB_ORG="myusername"
```

## Common Commands

### Discover and sync repositories

```bash
# List repositories (org/repo; project segment is ignored for GitHub)
mgit list "your-username/*/*" --limit 10
mgit list "AeyeOps/*/*" --limit 10

# Sync all repos from a user/organization
mgit sync "your-username/*/*" ./my-repos --provider github_personal
mgit sync "myusername/*/*" ./myusername-repos --provider github_personal
mgit sync "AeyeOps/*/*" ./aeyeops-repos --provider github_org

# Sync with concurrency control
mgit sync "myusername/*/*" ./repos --concurrency 10 --provider github_personal
```

## Organization vs User Repositories

### Personal Repositories

```bash
# Sync all personal repos (use your GitHub username)
mgit sync "your-username/*/*" ~/personal-repos --provider github_personal
```

### Organization Repositories

```bash
# Sync from multiple organizations
mgit sync "myusername/*/*" ./myusername --provider github_personal
mgit sync "AeyeOps/*/*" ./aeyeops --provider github_org
```

### Mixed Repository Management

Create a structured workspace for multiple contexts:

```bash
#!/bin/bash
# Organize repos by owner

"# Personal repos (use your username)
mgit sync "your-username/*/*" ~/github/personal --provider github_personal

# Organization repos
ORGS=("myusername" "AeyeOps" "MyCompany")
for org in "${ORGS[@]}"; do
  mgit sync "$org/*/*" "~/github/orgs/$org" --provider github_personal
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
mgit sync "large-org/*/*" ./repos --concurrency 3 --provider github_work
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
alias mgit-update-all='mgit sync "${GITHUB_OWNER:-myusername}/*/*" . --provider github_personal'
alias mgit-clone-org='mgit sync'
```

## Advanced Usage

### Working with GitHub Enterprise

```bash
# Configure for GitHub Enterprise
mgit login --provider github --org https://github.company.com --token YOUR_TOKEN --name github_enterprise
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
  echo "Syncing repositories for $org..."
  mkdir -p "$BASE_DIR/$org"
  mgit sync "$org/*/*" "$BASE_DIR/$org" --provider github_personal
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
          mgit login --provider github --token ${{ secrets.GITHUB_TOKEN }} --name github_ci

      - name: Sync repositories
        run: |
          mgit sync "${{ github.repository_owner }}/*/*" ./repos --provider github_ci
```

### Repository Statistics

```bash
# Sync repositories from organizations
mgit sync "myusername/*/*" ./repos --provider github_personal
mgit sync "AeyeOps/*/*" ./repos --provider github_org
```

## Working with Specific Examples

### Example 1: Managing myusername repositories

```bash
# Initial setup
mgit login --provider github --token ghp_xxxxxxxxxxxx --name github_personal

# Sync all repositories
mkdir -p ~/projects/myusername
mgit sync "myusername/*/*" ~/projects/myusername --provider github_personal

# Regular updates
cd ~/projects/myusername
mgit sync "myusername/*/*" . --provider github_personal
```

### Example 2: Working with AeyeOps organization

```bash
# Setup for org
mgit login --provider github --token ghp_xxxxxxxxxxxx --name github_org

# Sync all org repos
mgit sync "AeyeOps/*/*" ~/aeyeops/all --provider github_org
```

### Example 3: Personal repository management

```bash
# Backup all personal repos (use your username)
mgit sync "your-username/*/*" ~/github-backup/personal --provider github_personal
```

## Performance Optimization

### Shallow Clones

```bash
# Sync repositories
mgit sync "myusername/*/*" ./repos --provider github_personal
```

### Parallel Operations

```bash
# Increase concurrency for faster sync
mgit sync "large-org/*/*" ./repos --concurrency 20 --provider github_work
```

### Selective Updates

```bash
# Update all repos
mgit sync "org-name/*/*" ./repos --provider github_work
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

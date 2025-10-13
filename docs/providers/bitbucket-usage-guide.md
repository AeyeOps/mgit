# BitBucket Usage Guide for mgit

This guide provides detailed instructions for using mgit with BitBucket, including app password setup, workspace management, and BitBucket-specific features.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Creating App Passwords](#creating-app-passwords)
- [Configuration](#configuration)
- [Common Commands](#common-commands)
- [Workspace-Based Management](#workspace-based-management)
- [BitBucket-Specific Features](#bitbucket-specific-features)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Prerequisites

- A BitBucket account with workspace access
- Git installed and configured
- mgit installed (`pip install mgit`)

## Creating App Passwords

**Important**: BitBucket uses App Passwords instead of Personal Access Tokens (PATs).

### Step-by-Step App Password Creation

1. **Login to BitBucket**: Go to https://bitbucket.org and login

2. **Access Personal Settings**: 
   - Click your avatar (bottom left in BitBucket)
   - Click "Personal settings"

3. **Navigate to App Passwords**:
   - In the left sidebar under "Access management"
   - Click "App passwords"

4. **Create New App Password**:
   - Click "Create app password"
   - **Label**: Give it a descriptive name (e.g., "mgit-cli")
   - **Permissions**: Select the following:
     - **Repositories**: Read, Write
     - **Projects**: Read (for project-based repos)
     - **Workspaces**: Read (to list workspaces)
     - **Pull requests**: Read (optional, for PR info)
     - **Issues**: Read (optional, for issue tracking)

5. **Copy the Password**: Once created, copy immediately - it won't be shown again!

### App Password vs Repository Access Keys

- **App Passwords**: User-specific, work across all your accessible repositories
- **Repository Access Keys**: Repository-specific, read-only access
- **OAuth**: For applications, not recommended for CLI tools

## Configuration

### Method 1: Using mgit login command (Recommended)

```bash
# Login to BitBucket
mgit login --provider bitbucket --name team_bb
# Enter username (not email)
# Enter app password when prompted
# Enter workspace slug

# Verify configuration
mgit config --show team_bb
```

### Method 2: Manual YAML configuration

Edit `~/.config/mgit/config.yaml`:

```yaml
# Modern unified configuration
global:
  default_concurrency: 5
  default_update_mode: pull

providers:
  team_bb:
    url: https://api.bitbucket.org/2.0
    user: your-username                # BitBucket username (not email)
    token: your-app-password-here
    workspace: myworkspace             # BitBucket workspace slug
```

### Method 3: Legacy environment variables (Deprecated)

**Note**: Environment variables are deprecated. Use YAML configuration instead.

```bash
# Legacy environment variables (still supported but not recommended)
export BITBUCKET_USERNAME="your-username"
export BITBUCKET_APP_PASSWORD="your-app-password"
export BITBUCKET_WORKSPACE="myworkspace"
```

## Common Commands

### Working with workspaces and repositories

```bash
# Discover repositories in a workspace (project segment is ignored by BitBucket)
mgit list "myworkspace/*/*" --limit 10 --provider team_bb

# Sync all repos from a workspace
mgit sync "myworkspace/*/*" ./myworkspace-repos --provider team_bb

# Sync with concurrency control
mgit sync "myworkspace/*/*" ./repos --concurrency 5 --provider team_bb

# Sync only backend repos by naming convention
mgit sync "myworkspace/*/*-backend*" ./backend-repos --provider team_bb
```

## Workspace-Based Management

BitBucket organizes repositories within workspaces (formerly teams). Understanding this structure is crucial:

### Workspace Structure

```
BitBucket Account
├── Personal Workspace (username)
│   ├── personal-repo-1
│   └── personal-repo-2
└── Organization Workspaces
    ├── myworkspace
    │   ├── project-a
    │   ├── project-b
    │   └── shared-libraries
    └── another-workspace
        └── other-repos
```

### Working with Multiple Workspaces

```bash
#!/bin/bash
# Clone repos from multiple workspaces

WORKSPACES=("myworkspace" "my-company" "opensource-proj")
BASE_DIR="$HOME/bitbucket"

for workspace in "${WORKSPACES[@]}"; do
  echo "Syncing repositories from workspace: $workspace"
  mkdir -p "$BASE_DIR/$workspace"
  mgit sync "$workspace/*/*" "$BASE_DIR/$workspace" --provider team_bb
done
```

### Project-Based Organization

BitBucket also supports projects within workspaces, but project filtering is not applied by mgit for BitBucket. Use repository name patterns instead:

```bash
# Filter by project-naming convention
mgit sync "myworkspace/*/*-service" ./backend-services --provider team_bb
```

## BitBucket-Specific Features

### 1. Mercurial Support (Legacy)

While BitBucket has discontinued Mercurial support, some organizations may have archived repos. Handle these outside mgit.

### 2. Repository Slugs

BitBucket uses slugs (URL-friendly names) for repositories:

```bash
# Repository name: "My Awesome Project"
# Slug: "my-awesome-project"

# Use slugs in filters
mgit sync "myworkspace/*/my-awesome-*" ./awesome-projects --provider team_bb
```

### 3. Branch Restrictions

Note: Branch selection per-repository is not handled by mgit sync; switch branches after cloning if needed.

### 4. Repository Access Levels

BitBucket has different access levels:
- **Public**: Anyone can view
- **Private**: Only authorized users
- **Project-based**: Inherited from project settings

```bash
# List only public repos via JSON output filtering
mgit list "myworkspace/*/*" --format json --provider team_bb | jq '.[] | select(.is_private == false)'
```

## Troubleshooting

### Authentication Issues

**Error**: "Invalid app password" or "401 Unauthorized"

**Common causes**:
1. App password expired or revoked
2. Incorrect username (use BitBucket username, not email)
3. Missing required permissions
4. Wrong authentication method (using PAT instead of app password)

**Debug authentication**:
```bash
# Test authentication
curl -u YOUR_USERNAME:YOUR_APP_PASSWORD https://api.bitbucket.org/2.0/user

# Check workspace access
curl -u YOUR_USERNAME:YOUR_APP_PASSWORD https://api.bitbucket.org/2.0/workspaces
```

### Workspace Access

**Error**: "Workspace not found"

**Solutions**:
1. Verify workspace slug (case-sensitive)
2. Check workspace membership
3. Ensure app password has workspace read permission

```bash
# List accessible workspaces via API or web; mgit operates on repository patterns.
```

### SSH Configuration

**Issue**: Repeated password prompts

**Solution**: Configure SSH keys

1. Generate SSH key:
```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```

2. Add to BitBucket:
   - Personal settings → SSH keys → Add key

3. Configure SSH in git after cloning:
```bash
# mgit uses HTTPS URLs by default
# After cloning, you can change to SSH if needed
mgit sync "myworkspace/*/*" ./repos --provider team_bb
```

### Rate Limiting

BitBucket API rate limits:
- **Anonymous**: 60 requests per hour
- **Authenticated**: 1,000 requests per hour

Handle rate limits:
```bash
# Reduce concurrency
mgit sync "large-workspace/*/*" ./repos --provider team_bb --concurrency 3
```

### Clone Failures

**Error**: "Repository not found" or clone fails

**Debugging steps**:
```bash
# 1. Verify repository exists
mgit list "myworkspace/*/*" --provider team_bb | grep repo-name

# 2. Check repository access
curl -u USERNAME:APP_PASSWORD https://api.bitbucket.org/2.0/repositories/workspace/repo-slug

# 3. Try manual clone
git clone https://USERNAME:APP_PASSWORD@bitbucket.org/workspace/repo-slug.git
```

## Best Practices

### 1. App Password Security

```yaml
# .gitignore
.mgit/
.bitbucket-credentials
*.app-password
```

```bash
# Use environment variables in scripts
export MGIT_BITBUCKET_PASSWORD="$(cat ~/.bitbucket-app-password)"
```

### 2. Workspace Organization

```
~/bitbucket/
├── personal/              # Personal workspace repos
├── work/                  # Company workspace
│   ├── team-a/           # Team-specific repos
│   ├── team-b/
│   └── shared/           # Shared libraries
└── opensource/           # Open source contributions
```

### 3. Efficient Cloning Strategies

```bash
# Clone by project type
PROJECT_TYPES=("frontend" "backend" "mobile" "infrastructure")

for type in "${PROJECT_TYPES[@]}"; do
  mgit sync "myworkspace/*/*$type*" "./repos/$type" --provider team_bb
done
```

### 4. Backup Strategy

```bash
#!/bin/bash
# Backup all BitBucket repositories

BACKUP_DIR="$HOME/bitbucket-backup/$(date +%Y%m%d)"
WORKSPACES=("myworkspace" "personal-workspace" "company-workspace")

for workspace in "${WORKSPACES[@]}"; do
  echo "Backing up workspace: $workspace"
  mgit sync "$workspace/*/*" "$BACKUP_DIR/$workspace" --provider team_bb
done

# Create archive
tar -czf "$HOME/bitbucket-backup-$(date +%Y%m%d).tar.gz" "$BACKUP_DIR"
```

## Advanced Usage

### Integration with BitBucket Pipelines

```yaml
# bitbucket-pipelines.yml
image: python:3.9

pipelines:
  custom:
    update-all-repos:
      - step:
          name: Update all workspace repos
          script:
            - pip install mgit
            - mgit login --provider bitbucket --name team_bb
            - mgit sync "$BITBUCKET_WORKSPACE/*/*" ./ --provider team_bb
```

### Repository Migration

```bash
# Migrate from BitBucket to GitHub
WORKSPACE="myworkspace"
GITHUB_ORG="my-github-org"

# Sync from BitBucket
mgit sync "$WORKSPACE/*/*" ./migration --provider team_bb

# Push to GitHub
cd ./migration
for repo in */; do
    repo_name=$(basename "$repo")
    cd "$repo"
    git remote add github "https://github.com/$GITHUB_ORG/$repo_name.git"
    git push github --all
    git push github --tags
    cd ..
done
```

### Working with Large Workspaces

```bash
# Sync all repositories from large workspace
mgit sync "large-workspace/*/*" ./repos --provider team_bb
```

### Custom Repository Naming

```bash
# Sync repositories
mgit sync "myworkspace/*/*" ./repos --provider team_bb
```

## Real-World Examples

### Example 1: myworkspace Workspace Management

```bash
# Initial setup
mgit login --provider bitbucket --name team_bb

# Sync all repositories
mkdir -p ~/projects/myworkspace
mgit sync "myworkspace/*/*" ~/projects/myworkspace --provider team_bb

# Sync only active repositories by naming convention
mgit sync "myworkspace/*/*-active*" ~/projects/active --provider team_bb

# Regular updates
cd ~/projects/myworkspace
mgit sync "myworkspace/*/*" . --provider team_bb
```

### Example 2: Project-Based Development

```bash
# Setup for different projects
WORKSPACE="myworkspace"
PROJECTS=("Web Platform" "Mobile Apps" "Data Pipeline" "Infrastructure")

# Sync all repositories from workspace
mgit sync "$WORKSPACE/*/*" ~/bitbucket/all-repos --provider team_bb
```

### Example 3: CI/CD Repository Management

```bash
# Sync all repositories
mgit sync "myworkspace/*/*" ./ci-repos --provider team_bb
```

## Performance Optimization

### Shallow Cloning

Note: Shallow clone options are not exposed via mgit sync. Use git after cloning if needed.

### Selective Sync

Use patterns or post-filter JSON output from `mgit list` to select subsets, then `mgit sync` with matching patterns.

### Parallel Operations

```bash
# Maximize concurrency for faster operations
mgit sync "myworkspace/*/*" ./repos --provider team_bb --concurrency 20
```

## Security Considerations

1. **App Password Rotation**: Rotate app passwords every 90 days
2. **Minimal Permissions**: Only grant required permissions
3. **Separate Passwords**: Use different app passwords for different tools
4. **Audit Access**: Regularly review app password usage
5. **SSH Preference**: Use SSH keys for development machines

## BitBucket Cloud vs Server

### BitBucket Cloud (bitbucket.org)
Use `mgit login --provider bitbucket --name team_bb` and enter your username and app password when prompted.

### BitBucket Server (Self-hosted)
Self-hosted BitBucket support may require custom provider integration. Use standard BitBucket Cloud flows unless you have an adapter.

## Related Documentation

- [Provider Feature Matrix](./provider-feature-matrix.md)
- [BitBucket Hierarchical Filtering](./bitbucket-hierarchical-filtering.md)
- [Configuration Schema](../configuration/configuration-schema-design.md)
- [Multi-Provider Design](../architecture/multi-provider-design.md)

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
To see available workspaces and repositories, use the BitBucket web interface. mgit focuses on bulk clone and update operations.

### Clone repositories

```bash
# Clone all repos from a workspace
mgit clone-all myworkspace ./myworkspace-repos --provider bitbucket

# Clone all repos from workspace
mgit clone-all myworkspace ./backend-repos --provider bitbucket

# Clone with concurrency control
mgit clone-all myworkspace ./repos -c 5 --provider bitbucket
```

### Update repositories

```bash
# Update all repos in a directory
mgit pull-all myworkspace ./myworkspace-repos --provider bitbucket

# Update only specific repos
mgit pull-all --provider bitbucket --path ./repos --filter "*-backend"
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
    echo "Cloning repositories from workspace: $workspace"
    mkdir -p "$BASE_DIR/$workspace"
    mgit clone-all --provider bitbucket --workspace "$workspace" \
        --destination "$BASE_DIR/$workspace"
done
```

### Project-Based Organization

BitBucket also supports projects within workspaces:

```bash
# List projects in a workspace
mgit list-projects --provider bitbucket --workspace myworkspace

# Clone repos from a specific project
mgit clone-all --provider bitbucket --workspace myworkspace \
    --project "Backend Services" \
    --destination ./backend-services

# Filter by project and name
mgit clone-all --provider bitbucket --workspace myworkspace \
    --project "Microservices" \
    --filter "*-service" \
    --destination ./microservices
```

## BitBucket-Specific Features

### 1. Mercurial Support (Legacy)

While BitBucket has discontinued Mercurial support, some organizations may have archived repos:

```bash
# Skip Mercurial repos during clone
mgit clone-all --provider bitbucket --workspace myworkspace \
    --destination ./repos \
    --git-only
```

### 2. Repository Slugs

BitBucket uses slugs (URL-friendly names) for repositories:

```bash
# Repository name: "My Awesome Project"
# Slug: "my-awesome-project"

# Use slugs in filters
mgit clone-all --provider bitbucket --workspace myworkspace \
    --filter "my-awesome-*" \
    --destination ./awesome-projects
```

### 3. Branch Restrictions

```bash
# Clone specific branch from all repos
mgit clone-all --provider bitbucket --workspace myworkspace \
    --destination ./develop-branch \
    --branch develop

# Different branches for different repos
mgit clone-all --provider bitbucket --workspace myworkspace \
    --destination ./repos \
    --branch-map "frontend:main,backend:develop,infra:master"
```

### 4. Repository Access Levels

BitBucket has different access levels:
- **Public**: Anyone can view
- **Private**: Only authorized users
- **Project-based**: Inherited from project settings

```bash
# Clone only public repos
mgit clone-all --provider bitbucket --workspace myworkspace \
    --destination ./public-repos \
    --public-only

# Include private repos (requires authentication)
mgit clone-all --provider bitbucket --workspace myworkspace \
    --destination ./all-repos \
    --include-private
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
# List accessible workspaces
mgit list-workspaces --provider bitbucket --debug
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
mgit clone-all myworkspace ./repos --provider bitbucket
```

### Rate Limiting

BitBucket API rate limits:
- **Anonymous**: 60 requests per hour
- **Authenticated**: 1,000 requests per hour

Handle rate limits:
```bash
# Reduce concurrency
mgit clone-all --provider bitbucket --workspace large-workspace \
    --destination ./repos \
    --concurrency 3 \
    --delay 2000  # 2 second delay between operations
```

### Clone Failures

**Error**: "Repository not found" or clone fails

**Debugging steps**:
```bash
# 1. Verify repository exists
mgit list-repos --provider bitbucket --workspace myworkspace | grep repo-name

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
    mgit clone-all myworkspace "./repos/$type" --provider bitbucket
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
    mgit clone-all "$workspace" "$BACKUP_DIR/$workspace" --provider bitbucket
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
            - mgit login --provider bitbucket --org $BITBUCKET_WORKSPACE --token $BITBUCKET_APP_PASSWORD
            - mgit pull-all $BITBUCKET_WORKSPACE ./ --provider bitbucket
```

### Repository Migration

```bash
# Migrate from BitBucket to GitHub
WORKSPACE="myworkspace"
GITHUB_ORG="my-github-org"

# Clone from BitBucket
mgit clone-all "$WORKSPACE" ./migration --provider bitbucket

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
# Clone all repositories from large workspace
mgit clone-all large-workspace ./repos --provider bitbucket
```

### Custom Repository Naming

```bash
# Clone repositories
mgit clone-all myworkspace ./repos --provider bitbucket
```

## Real-World Examples

### Example 1: myworkspace Workspace Management

```bash
# Initial setup
mgit login --provider bitbucket --username myusername --token app-password-here

# Clone all repositories
mkdir -p ~/projects/myworkspace
mgit clone-all myworkspace ~/projects/myworkspace --provider bitbucket

# Clone all repositories
mgit clone-all myworkspace ~/projects/active --provider bitbucket

# Regular updates
cd ~/projects/myworkspace
mgit pull-all myworkspace . --provider bitbucket
```

### Example 2: Project-Based Development

```bash
# Setup for different projects
WORKSPACE="myworkspace"
PROJECTS=("Web Platform" "Mobile Apps" "Data Pipeline" "Infrastructure")

# Clone all repositories from workspace
mgit clone-all "$WORKSPACE" ~/bitbucket/all-repos --provider bitbucket
```

### Example 3: CI/CD Repository Management

```bash
# Clone all repositories
mgit clone-all myworkspace ./ci-repos --provider bitbucket

# Update and check pipeline status
mgit pull-all --provider bitbucket --path ./ci-repos --check-pipelines
```

## Performance Optimization

### Shallow Cloning

```bash
# Clone with minimal history
mgit clone-all --provider bitbucket --workspace myworkspace \
    --destination ./repos \
    --shallow --depth 1
```

### Selective Cloning

```bash
# Clone only recently updated repos
mgit clone-all --provider bitbucket --workspace myworkspace \
    --destination ./recent-repos \
    --updated-after "2024-01-01"
```

### Parallel Operations

```bash
# Maximize concurrency for faster operations
mgit clone-all --provider bitbucket --workspace myworkspace \
    --destination ./repos \
    --concurrency 20
```

## Security Considerations

1. **App Password Rotation**: Rotate app passwords every 90 days
2. **Minimal Permissions**: Only grant required permissions
3. **Separate Passwords**: Use different app passwords for different tools
4. **Audit Access**: Regularly review app password usage
5. **SSH Preference**: Use SSH keys for development machines

## BitBucket Cloud vs Server

### BitBucket Cloud (bitbucket.org)
```bash
# Default configuration works with cloud
mgit login --provider bitbucket --username USER --password APP_PASS
```

### BitBucket Server (Self-hosted)
```bash
# Configure for self-hosted instance
mgit login --provider bitbucket \
    --username USER \
    --password APP_PASS \
    --api-url https://bitbucket.company.com/rest/api/1.0 \
    --base-url https://bitbucket.company.com
```

## Related Documentation

- [Provider Feature Matrix](./provider-feature-matrix.md)
- [BitBucket Hierarchical Filtering](./bitbucket-hierarchical-filtering.md)
- [Configuration Schema](../configuration/configuration-schema-design.md)
- [Multi-Provider Design](../architecture/multi-provider-design.md)
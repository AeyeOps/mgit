# Git CLI with Bitbucket Cloud Integration

This document covers the integration of Git CLI with Bitbucket Cloud, including authentication methods, common operations, and best practices.

## Authentication Methods

Bitbucket Cloud supports several authentication methods for Git operations:

### 1. HTTPS with Password/App Password

App passwords are recommended over regular account passwords:

```bash
# Clone with HTTPS
git clone https://username@bitbucket.org/workspace/repository.git
# You'll be prompted for password or app password
```

To create an app password:
1. Go to Bitbucket Cloud settings (your avatar) → Personal settings → App passwords
2. Create a new app password with appropriate permissions (read, write)
3. Save the password securely - it will only be shown once

### 2. HTTPS with Git Credential Manager (GCM)

GCM is recommended for Windows users and also works on macOS and Linux:

```bash
# Install Git Credential Manager (included with Git for Windows)
# On macOS: brew install --cask git-credential-manager
# On Linux: follow installation instructions from GCM repo

# Clone with HTTPS
git clone https://bitbucket.org/workspace/repository.git
# GCM will handle authentication and token storage
```

### 3. SSH Authentication

For passwordless authentication:

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add SSH key to SSH agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Copy your public key
cat ~/.ssh/id_ed25519.pub
# Add the key to Bitbucket Cloud (Settings → SSH Keys)

# Clone with SSH
git clone git@bitbucket.org:workspace/repository.git
```

## Common Git Operations with Bitbucket Cloud

### Repository Setup

```bash
# Clone an existing repository
git clone https://username@bitbucket.org/workspace/repository.git
# or with SSH
git clone git@bitbucket.org:workspace/repository.git

# Initialize a local repository and connect to Bitbucket
git init
git remote add origin https://username@bitbucket.org/workspace/repository.git
# or with SSH
git remote add origin git@bitbucket.org:workspace/repository.git
```

### Basic Workflow

```bash
# Pull the latest changes
git pull origin main

# Create a new branch
git checkout -b feature/new-feature

# Make changes, then stage and commit
git add .
git commit -m "Add new feature"

# Push branch to Bitbucket
git push -u origin feature/new-feature
```

### Pull Requests via Command Line

While Bitbucket Cloud pull requests are typically managed via the web UI, you can retrieve information using:

```bash
# Set upstream branch for a PR
git push -u origin feature/new-feature

# After creating the PR in the UI, update it with additional commits
git push origin feature/new-feature
```

## Working with Large Files (Git LFS)

Bitbucket Cloud supports Git LFS for large file storage:

```bash
# Install Git LFS
git lfs install

# Track large file types
git lfs track "*.psd"
git lfs track "*.zip"

# Ensure .gitattributes is committed
git add .gitattributes
git commit -m "Configure Git LFS tracking"

# Use Git normally - LFS takes care of large files
git add large-file.psd
git commit -m "Add design file"
git push origin main
```

## Fork Workflow for Bitbucket Cloud

```bash
# Clone your fork (after forking via Bitbucket UI)
git clone https://username@bitbucket.org/username/forked-repository.git

# Add original repository as upstream remote
git remote add upstream https://bitbucket.org/original-owner/original-repository.git

# Keep your fork updated
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

## Project Configuration for Bitbucket

Project-specific Git configuration for Bitbucket Cloud teams:

```bash
# Configure line endings consistently
git config --local core.autocrlf input

# Configure user details for this repository only
git config --local user.name "Your Name"
git config --local user.email "your.email@company.com"

# Configure default branch for pushing (if different from tracking)
git config --local push.default current
```

## Troubleshooting Bitbucket Authentication

### HTTPS Authentication Issues

```bash
# Check remote URL
git remote -v

# Update remote URL with credentials
git remote set-url origin https://username@bitbucket.org/workspace/repository.git

# Clear cached credentials if needed
git config --global --unset credential.helper
# Then reconfigure the credential helper
git config --global credential.helper manager  # for GCM
```

### SSH Authentication Issues

```bash
# Test SSH connection
ssh -T git@bitbucket.org

# Ensure SSH agent is running and key is added
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Check SSH configuration (~/.ssh/config)
# Add if needed:
Host bitbucket.org
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
```

## Advanced Features

### Bitbucket Pipes and CI/CD

While primarily configured via Bitbucket's UI, you can add pipeline configuration files:

```bash
# Create and add bitbucket-pipelines.yml
git add bitbucket-pipelines.yml
git commit -m "Add CI/CD pipeline configuration"
git push origin main
```

### Submodules with Bitbucket

```bash
# Add a submodule from another Bitbucket repository
git submodule add https://bitbucket.org/workspace/another-repository.git path/to/submodule

# Update submodules
git submodule update --init --recursive

# Clone a repository with submodules
git clone --recurse-submodules https://bitbucket.org/workspace/repository.git
```

## Best Practices for Bitbucket Cloud

1. **Use descriptive commit messages** that follow Bitbucket's integration with Jira (if applicable)
   ```bash
   git commit -m "ABC-123: Add new feature for customer authentication"
   ```

2. **Branch naming conventions** for Bitbucket
   ```bash
   git checkout -b feature/ABC-123-customer-auth
   git checkout -b bugfix/ABC-124-login-error
   git checkout -b hotfix/ABC-125-security-patch
   ```

3. **Use Git hooks** for Bitbucket project standards
   ```bash
   # Add hooks to your repository in .git/hooks/
   # Example: pre-commit hook for linting
   ```

4. **Configure .gitignore properly** for your project type
   ```bash
   # Add standard ignores for your language/framework
   # Add Bitbucket specific ignores if needed
   ```

5. **Consider commit signing** for verified commits
   ```bash
   git config --global commit.gpgsign true
   ```
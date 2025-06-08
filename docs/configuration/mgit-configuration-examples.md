# mgit Configuration Examples

This guide provides comprehensive configuration examples for mgit, covering all providers, authentication methods, and troubleshooting common issues.

## Table of Contents
- [Configuration File Location](#configuration-file-location)
- [Complete Multi-Provider Setup](#complete-multi-provider-setup)
- [Provider-Specific Configurations](#provider-specific-configurations)
- [Environment Variable Configuration](#environment-variable-configuration)
- [Advanced Configuration Options](#advanced-configuration-options)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Security Best Practices](#security-best-practices)

## Configuration File Location

mgit looks for configuration in the following order:
1. Environment variables (highest priority)
2. `~/.config/mgit/config` (key=value format, like .env files)
3. Default values (lowest priority)

### Creating the Configuration Directory

```bash
# Create mgit config directory
mkdir -p ~/.config/mgit

# Create initial config file
touch ~/.config/mgit/config

# Set appropriate permissions (important for security)
chmod 700 ~/.config/mgit
chmod 600 ~/.config/mgit/config
```

## Complete Multi-Provider Setup

### Full Configuration Example

```bash
# ~/.config/mgit/config
# Complete mgit configuration with all providers
# Format: KEY=VALUE (no spaces around =)

# Global settings
DEFAULT_CONCURRENCY=10
DEFAULT_UPDATE_MODE=pull

# Azure DevOps Configuration
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/myorg
AZURE_DEVOPS_EXT_PAT=your-azure-devops-pat-here

# GitHub Configuration
GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_ORG=steveant

# BitBucket Configuration
BITBUCKET_WORKSPACE=santonakakis
BITBUCKET_USERNAME=your-username
BITBUCKET_APP_PASSWORD=your-app-password-here

# Logging Configuration
LOG_FILENAME=mgit.log
LOG_LEVEL=DEBUG
CONSOLE_LEVEL=INFO
```

## Provider-Specific Configurations

### Azure DevOps Configuration

```bash
# ~/.config/mgit/config
# Azure DevOps specific settings

# Required settings
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/myorg
AZURE_DEVOPS_EXT_PAT=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional settings
AZUREDEVOPS_USERNAME=your-username

# Note: Project-specific settings and clone options are handled via command-line arguments
```

### GitHub Configuration

```bash
# ~/.config/mgit/config
# GitHub specific settings

# Required settings
GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional settings
GITHUB_ORG=AeyeOps
GITHUB_USERNAME=your-username

# For GitHub Enterprise (optional)
GITHUB_ENTERPRISE_URL=https://github.company.com

# Note: Organization-specific settings and clone options are handled via command-line arguments
```

### BitBucket Configuration

```bash
# ~/.config/mgit/config
# BitBucket specific settings

# Required settings
BITBUCKET_USERNAME=steveant
BITBUCKET_APP_PASSWORD=xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional settings
BITBUCKET_WORKSPACE=santonakakis

# For BitBucket Server (optional)
BITBUCKET_SERVER_URL=https://bitbucket.company.com

# Note: Workspace-specific settings and clone options are handled via command-line arguments
```

## Environment Variable Configuration

### Complete Environment Variable Setup

```bash
#!/bin/bash
# ~/.bashrc or ~/.zshrc

# Global settings
export DEFAULT_CONCURRENCY="10"
export DEFAULT_UPDATE_MODE="pull"

# Azure DevOps
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/myorg"
export AZURE_DEVOPS_EXT_PAT="your-pat-here"

# GitHub
export GITHUB_PAT="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export GITHUB_ORG="steveant"

# BitBucket
export BITBUCKET_USERNAME="steveant"
export BITBUCKET_APP_PASSWORD="app-password-here"
export BITBUCKET_WORKSPACE="santonakakis"

# Logging
export LOG_LEVEL="DEBUG"
export CONSOLE_LEVEL="INFO"
```

### Provider-Specific Environment Variables

```bash
# Azure DevOps with proxy
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/company"
export AZURE_DEVOPS_EXT_PAT="$(cat ~/.azure-pat)"  # Read from file
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1,.company.com"

# GitHub Enterprise
export GITHUB_ENTERPRISE_URL="https://github.company.com"
export GITHUB_PAT="$(security find-generic-password -s github-token -w)"  # macOS keychain

# BitBucket Server
export BITBUCKET_SERVER_URL="https://bitbucket.company.com"
```

### Temporary Configuration

```bash
# One-time use without permanent storage
GITHUB_PAT="temp-token" python -m mgit clone-all org ./repos --provider github

# Session-specific configuration
export GITHUB_PAT="temp-token"
python -m mgit clone-all org ./repos --provider github
```

## Advanced Configuration Options

### Multiple Configuration Files

```bash
# ~/.config/mgit/config.work
# Work-specific configuration
DEFAULT_CONCURRENCY=20
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/company
AZURE_DEVOPS_EXT_PAT=work-pat-token

# ~/.config/mgit/config.personal
# Personal configuration
DEFAULT_CONCURRENCY=5
GITHUB_PAT=personal-github-token
GITHUB_ORG=my-username
```

```bash
# Switch between configurations
cp ~/.config/mgit/config.work ~/.config/mgit/config
python -m mgit clone-all project ./work-repos

cp ~/.config/mgit/config.personal ~/.config/mgit/config
python -m mgit clone-all my-org ./personal-repos
```

### Profile-Based Configuration

```bash
# ~/.config/mgit/config.work
# Work profile configuration
DEFAULT_CONCURRENCY=10
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/company
AZURE_DEVOPS_EXT_PAT=work-pat-token
```

```bash
# ~/.config/mgit/config.personal
# Personal profile configuration
DEFAULT_CONCURRENCY=5
GITHUB_PAT=personal-github-token
GITHUB_ORG=my-username
```

### Using Shell Scripts for Automation

```bash
#!/bin/bash
# mgit-clone-with-setup.sh
# Script to clone repos and run setup commands

# Clone all repos
python -m mgit clone-all $1 $2

# Run setup for each cloned repo
for dir in $2/*; do
  if [ -d "$dir" ]; then
    echo "Setting up $(basename $dir)..."
    
    # Node.js projects
    if [ -f "$dir/package.json" ]; then
      (cd "$dir" && npm install)
    fi
    
    # Python projects
    if [ -f "$dir/requirements.txt" ]; then
      (cd "$dir" && pip install -r requirements.txt)
    fi
  fi
done
```

## Troubleshooting Guide

### Common Authentication Issues

#### Azure DevOps Authentication Failures

**Problem**: "TF401019: The Git repository with name or identifier does not exist"

```bash
# Check these settings in ~/.config/mgit/config
# Ensure URL format is correct
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/yourorg  # ✓ Correct
# AZURE_DEVOPS_ORG_URL=yourorg.visualstudio.com     # ✗ Old format
# AZURE_DEVOPS_ORG_URL=dev.azure.com/yourorg       # ✗ Missing https://

# Verify PAT has correct scopes
# Required: Code (Read & Write), Project and Team (Read)
```

**Debug commands**:
```bash
# Test authentication
mgit test-auth --provider azdevops --verbose

# List accessible projects
mgit list-projects --provider azdevops --debug
```

#### GitHub Token Issues

**Problem**: "Bad credentials" or "401 Unauthorized"

```bash
# Verify token format and scopes in ~/.config/mgit/config
# Classic token format
GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # 40 chars after ghp_

# Fine-grained token format  
# GITHUB_PAT=github_pat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Debug commands**:
```bash
# Verify token
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user

# Check rate limit
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
```

#### BitBucket App Password Problems

**Problem**: "Invalid app password"

```bash
# Common mistakes in ~/.config/mgit/config
BITBUCKET_USERNAME=email@example.com      # ✗ Should be username, not email
BITBUCKET_USERNAME=steveant               # ✓ Correct

BITBUCKET_APP_PASSWORD=password123        # ✗ Regular password
BITBUCKET_APP_PASSWORD=ATBB3k4j5k6j...   # ✓ App password format
```

**Debug commands**:
```bash
# Test authentication
curl -u USERNAME:APP_PASSWORD https://api.bitbucket.org/2.0/user

# List workspaces
mgit list-workspaces --provider bitbucket --debug
```

### Configuration Loading Issues

#### Configuration Not Found

```bash
# Check configuration search path
mgit config --show-path

# Typical output:
# 1. Environment variables
# 2. /home/user/.config/mgit/config
# 3. Built-in defaults
```

#### Configuration Format

**Note**: mgit uses key=value format (like .env files), NOT YAML format.

Common format rules:
```bash
# ✓ Correct - key=value with no spaces around =
GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEFAULT_CONCURRENCY=10

# ✗ Incorrect - spaces around =
GITHUB_PAT = ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ✗ Incorrect - quotes not needed unless value has spaces
GITHUB_PAT="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# ✓ Correct - quotes for values with spaces
CUSTOM_MESSAGE="This has spaces"
```

### Network and Proxy Issues

#### Corporate Proxy Configuration

```bash
# Environment variables for proxy configuration
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1,.company.com"

# SSL configuration
export SSL_CERT_FILE="/etc/ssl/certs/company-ca-bundle.crt"
export REQUESTS_CA_BUNDLE="/etc/ssl/certs/company-ca-bundle.crt"
```

#### SSL Certificate Issues

```bash
# Temporary disable SSL verification (not recommended)
export GIT_SSL_VERIFY=false
export MGIT_SSL_VERIFY=false

# Better solution - add corporate CA
export SSL_CERT_FILE="/path/to/corporate-ca.crt"
export REQUESTS_CA_BUNDLE="/path/to/corporate-ca.crt"
```

### Performance Issues

#### Slow Clone Operations

```bash
# Optimize for large repositories in ~/.config/mgit/config
DEFAULT_CONCURRENCY=5      # Reduce if hitting limits

# Use command-line options for clone settings:
# python -m mgit clone-all project ./repos --concurrency 5

# For shallow clones, use git config after cloning:
# git clone --depth 1 --single-branch <repo>
```

#### Memory Issues

```bash
# Limit concurrent operations to reduce memory usage
DEFAULT_CONCURRENCY=3

# For very large operations, use smaller batches:
# python -m mgit clone-all project ./repos --concurrency 2
```

## Security Best Practices

### Credential Storage

```bash
# ~/.config/mgit/config
# Reference credentials from environment variables

# Read tokens from environment instead of hardcoding
GITHUB_PAT=${GITHUB_TOKEN}
AZURE_DEVOPS_EXT_PAT=${AZURE_PAT}
BITBUCKET_APP_PASSWORD=${BITBUCKET_PASS}

# Or use command substitution to read from secure storage
# GITHUB_PAT=$(pass show github/token)
# AZURE_DEVOPS_EXT_PAT=$(security find-generic-password -s azure-pat -w)
```

### Secure Configuration Script

```bash
#!/bin/bash
# secure-mgit-setup.sh

# Create secure directory
mkdir -p ~/.config/mgit
chmod 700 ~/.config/mgit

# Create config with secure permissions
touch ~/.config/mgit/config
chmod 600 ~/.config/mgit/config

# Use password manager
GITHUB_TOKEN=$(pass show github/mgit-token)
AZURE_PAT=$(pass show azure/mgit-pat)
BITBUCKET_PASS=$(pass show bitbucket/mgit-app-password)

# Export for current session
export GITHUB_TOKEN AZURE_PAT BITBUCKET_PASS

# Create config that references environment variables
cat > ~/.config/mgit/config << EOF
# mgit configuration - references environment variables
GITHUB_PAT=\${GITHUB_TOKEN}
AZURE_DEVOPS_EXT_PAT=\${AZURE_PAT}
BITBUCKET_APP_PASSWORD=\${BITBUCKET_PASS}
DEFAULT_CONCURRENCY=10
EOF
```

### Audit Configuration

```bash
#!/bin/bash
# audit-mgit-config.sh

# Check for exposed credentials
echo "Checking for exposed credentials..."
grep -E "(TOKEN|PAT|PASSWORD)=" ~/.config/mgit/config | grep -v "\${" | head -20

# Check file permissions
echo "Checking file permissions..."
ls -la ~/.config/mgit/

# Check environment variables
echo "Checking environment variables..."
env | grep MGIT_ | grep -E "(TOKEN|PAT|PASSWORD)" | cut -d= -f1
```

### Git Configuration Integration

```bash
# Configure git to use mgit credentials
git config --global credential.helper "!mgit git-credential"

# Per-provider git configuration
git config --global credential.https://github.com.helper "!mgit git-credential --provider github"
git config --global credential.https://dev.azure.com.helper "!mgit git-credential --provider azdevops"
git config --global credential.https://bitbucket.org.helper "!mgit git-credential --provider bitbucket"
```

## Configuration Templates

### Minimal Configuration

```bash
# ~/.config/mgit/config
# Minimal working configuration

GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Team Configuration Template

```bash
# team-config-template
# Template for team members

# Team defaults
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/ourcompany
AZURE_DEVOPS_EXT_PAT=${AZURE_DEVOPS_PAT}  # Each member sets their own
DEFAULT_CONCURRENCY=10

# Each team member copies this template and adds their PAT
```

### Multi-Environment Setup

```bash
# ~/.config/mgit/config.personal
# Personal environment
GITHUB_PAT=${PERSONAL_GITHUB_TOKEN}
GITHUB_ORG=my-username
DEFAULT_CONCURRENCY=5

# ~/.config/mgit/config.work
# Work environment
AZURE_DEVOPS_ORG_URL=${WORK_AZURE_ORG}
AZURE_DEVOPS_EXT_PAT=${WORK_AZURE_PAT}
DEFAULT_CONCURRENCY=10

# ~/.config/mgit/config.client
# Client environment
BITBUCKET_USERNAME=${CLIENT_BITBUCKET_USER}
BITBUCKET_APP_PASSWORD=${CLIENT_BITBUCKET_PASS}
BITBUCKET_WORKSPACE=${CLIENT_WORKSPACE}
```

Usage:
```bash
# Switch environments
cp ~/.config/mgit/config.work ~/.config/mgit/config
python -m mgit clone-all project ./work-repos

cp ~/.config/mgit/config.personal ~/.config/mgit/config
python -m mgit clone-all my-org ./personal-repos
```

## Related Documentation

- [Architecture Documentation](../architecture/)
- [Provider Feature Matrix](../providers/provider-feature-matrix.md)
- [CLI Command Structure](../cli-design/command-structure-design.md)
- [README](../../README.md)
# mgit v0.2.1 Migration Guide

This guide helps you migrate from mgit v0.2.0 (Azure DevOps-only) to v0.2.1 (multi-provider).

## Overview of Changes

mgit v0.2.1 introduces multi-provider support, which requires some changes to configuration and environment variables. However, we've maintained backward compatibility where possible to minimize disruption.

## Step-by-Step Migration

### 1. Backup Current Configuration

First, backup your existing configuration:

```bash
cp ~/.config/mgit/config ~/.config/mgit/config.backup
```

### 2. Update Environment Variables

If you use environment variables, update them with provider-specific prefixes:

#### Azure DevOps
```bash
# Old
export AZURE_DEVOPS_PAT="your-pat-token"
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/myorg"

# New
export MGIT_AZDEVOPS_PAT="your-pat-token"
export MGIT_AZDEVOPS_ORG_URL="https://dev.azure.com/myorg"
```

#### GitHub (New)
```bash
export MGIT_GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
export MGIT_GITHUB_ORG="myorganization"
```

#### BitBucket (New)
```bash
export MGIT_BITBUCKET_APP_PASSWORD="app-password-here"
export MGIT_BITBUCKET_USERNAME="myusername"
export MGIT_BITBUCKET_WORKSPACE="myworkspace"
```

### 3. Update Configuration File Format

The configuration file now uses provider-specific sections:

#### Old Format (v0.2.0)
```yaml
# ~/.config/mgit/config
pat: "your-azure-devops-pat"
org_url: "https://dev.azure.com/myorg"
log_level: "INFO"
default_concurrency: 4
```

#### New Format (v0.2.1)
```yaml
# ~/.config/mgit/config
# Global settings
log_level: "INFO"
console_level: "INFO"

# Provider-specific settings
providers:
  azdevops:
    pat: "your-azure-devops-pat"
    org_url: "https://dev.azure.com/myorg"
    default_concurrency: 4
    
  github:
    token: "ghp_xxxxxxxxxxxx"
    default_concurrency: 10
    
  bitbucket:
    app_password: "app-password-here"
    username: "myusername"
    default_concurrency: 5
```

### 4. Update Your Scripts

If you have scripts using mgit, here are the changes needed:

#### Login Commands
```bash
# Old (Azure DevOps specific)
mgit login --org https://dev.azure.com/myorg --pat $AZURE_DEVOPS_PAT

# New Option 1: Auto-detection from URL
mgit login --org https://dev.azure.com/myorg --pat $MGIT_AZDEVOPS_PAT

# New Option 2: Explicit provider
mgit login --provider azdevops --pat $MGIT_AZDEVOPS_PAT
```

#### Clone Commands
```bash
# Old
mgit clone-all MyProject ~/repos/azure

# New (works the same for Azure DevOps)
mgit clone-all MyProject ~/repos/azure

# New (for other providers)
mgit clone-all myorg ~/repos/github --provider github
mgit clone-all myworkspace ~/repos/bitbucket --provider bitbucket
```

### 5. Test Your Migration

After updating, test your configuration:

```bash
# Check version
python -m mgit --version

# Test configuration
python -m mgit config --show

# Test login (Azure DevOps)
mgit login --provider azdevops --pat $MGIT_AZDEVOPS_PAT

# Test a small clone operation
mgit clone-all YourTestProject /tmp/test-repos -c 1
```

## Common Issues and Solutions

### Issue: "Provider not found" error
**Solution**: Ensure you're either:
- Using the `--provider` flag explicitly, or
- Providing a full URL that can be auto-detected

### Issue: Authentication failures
**Solution**: Check that:
- Environment variables use new prefixes (MGIT_PROVIDER_*)
- PAT/tokens have necessary permissions
- Configuration file uses provider sections

### Issue: Old scripts failing
**Solution**: Update environment variable names and add `--provider` flags where needed

## Provider-Specific Setup

### Setting up GitHub
```bash
# 1. Generate a Personal Access Token at GitHub
# Settings → Developer settings → Personal access tokens → Generate new token
# Scopes needed: repo (full control)

# 2. Configure mgit
mgit login --provider github --pat ghp_xxxxxxxxxxxx

# 3. Test with a clone
mgit clone-all your-github-org ~/github/repos
```

### Setting up BitBucket
```bash
# 1. Generate an App Password at BitBucket
# Personal settings → App passwords → Create app password
# Permissions needed: Repositories (Read)

# 2. Configure mgit
mgit login --provider bitbucket --pat app-password --username yourusername

# 3. Test with a clone
mgit clone-all your-workspace ~/bitbucket/repos
```

## Rollback Instructions

If you need to rollback to v0.2.0:

```bash
# 1. Restore old configuration
cp ~/.config/mgit/config.backup ~/.config/mgit/config

# 2. Restore old environment variables
export AZURE_DEVOPS_PAT="your-pat-token"
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/myorg"
unset MGIT_AZDEVOPS_PAT
unset MGIT_AZDEVOPS_ORG_URL

# 3. Downgrade mgit
pip install mgit==0.2.0
```

## Getting Help

- Check the [CHANGELOG.md](CHANGELOG.md) for detailed changes
- Review [README.md](README.md) for updated usage examples
- See [docs/](docs/) for comprehensive documentation
- Report issues at [GitHub Issues](https://github.com/yourusername/mgit/issues)

## Summary

The migration to v0.2.1 mainly involves:
1. Adding provider prefixes to environment variables
2. Restructuring the configuration file with provider sections
3. Optionally specifying providers in commands

Your existing Azure DevOps workflows will continue to work with minimal changes, while gaining the ability to manage GitHub and BitBucket repositories with the same tool.
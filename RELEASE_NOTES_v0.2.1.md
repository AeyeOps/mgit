# mgit v0.2.1 Release Notes

## 🎉 Multi-Provider Git Management is Here!

We're excited to announce mgit v0.2.1, a major release that transforms mgit from an Azure DevOps-only tool into a comprehensive multi-provider git management solution. This release brings full support for GitHub and BitBucket alongside Azure DevOps, with complete feature parity across all providers.

## 🚀 Key Features

### Multi-Provider Support
- **GitHub**: Full integration with organizations and user repositories
- **BitBucket**: Complete workspace and repository management
- **Azure DevOps**: Enhanced with improved authentication and error handling

### Unified Experience
- Single consistent CLI interface across all providers
- Automatic provider detection from repository URLs
- Feature parity: login, clone-all, pull-all work identically everywhere

### Enhanced Capabilities
- **Smart Authentication**: Secure credential storage per provider
- **Concurrent Operations**: Provider-optimized concurrency settings
- **Update Modes**: Skip, pull, or force modes for existing repositories
- **Rich Output**: Beautiful progress indicators and status reporting

## 📦 What's New

### For Azure DevOps Users
- Your existing workflows continue to work
- Enhanced error messages and retry logic
- Improved handling of disabled repositories

### For GitHub Users
- Clone entire organizations or user accounts
- Full support for GitHub Enterprise
- Respects GitHub API rate limits (5000/hour authenticated)

### For BitBucket Users
- Manage complete workspaces
- Support for BitBucket Server
- App Password authentication

## 🔄 Migration Guide

### From v0.2.0 to v0.2.1

#### 1. Update Environment Variables (if used)
```bash
# Old
export AZURE_DEVOPS_PAT="your-token"

# New (provider-specific)
export MGIT_AZDEVOPS_PAT="your-azure-token"
export MGIT_GITHUB_TOKEN="your-github-token"
export MGIT_BITBUCKET_APP_PASSWORD="your-bitbucket-password"
```

#### 2. Update Configuration File
The configuration file now uses provider-specific sections:

```yaml
# Old format (~/.config/mgit/config)
pat: "your-token"
org_url: "https://dev.azure.com/myorg"

# New format
providers:
  azdevops:
    pat: "your-azure-token"
    org_url: "https://dev.azure.com/myorg"
  github:
    token: "your-github-token"
  bitbucket:
    app_password: "your-bitbucket-password"
    username: "your-username"
```

#### 3. Update Login Commands
```bash
# Old (Azure DevOps only)
mgit login --org https://dev.azure.com/myorg --pat TOKEN

# New (auto-detection)
mgit login --org https://dev.azure.com/myorg --pat TOKEN
mgit login --org https://github.com/myorg --pat TOKEN
mgit login --org https://bitbucket.org/myworkspace --pat APP_PASSWORD

# New (explicit provider)
mgit login --provider github --pat TOKEN
mgit login --provider bitbucket --pat APP_PASSWORD --username myuser
```

#### 4. Clone and Pull Commands
Commands now support all providers with auto-detection:

```bash
# Azure DevOps (works as before)
mgit clone-all MyProject /path/to/repos

# GitHub
mgit clone-all myorg /path/to/repos --provider github
mgit clone-all https://github.com/myorg /path/to/repos  # auto-detected

# BitBucket
mgit clone-all myworkspace /path/to/repos --provider bitbucket
mgit clone-all https://bitbucket.org/myworkspace /path/to/repos  # auto-detected
```

## 💡 Quick Start Examples

### GitHub Organization
```bash
# Login
mgit login --provider github --pat ghp_xxxxxxxxxxxx

# Clone all repositories
mgit clone-all myorg ~/github/myorg

# Update all repositories
mgit pull-all myorg ~/github/myorg
```

### BitBucket Workspace
```bash
# Login with app password
mgit login --provider bitbucket --pat app-password-here --username myuser

# Clone workspace
mgit clone-all myworkspace ~/bitbucket/myworkspace

# Pull updates with force mode
mgit pull-all myworkspace ~/bitbucket/myworkspace -u force
```

## 🙏 Acknowledgments

This release represents a complete architectural overhaul of mgit. Special thanks to:
- The Azure DevOps Python SDK team for the solid foundation
- The GitHub and BitBucket API teams for excellent documentation
- Our early adopters who provided valuable feedback
- Contributors who helped with testing across different platforms

## 📝 Breaking Changes

Please review the Migration Guide above. Key breaking changes:
1. Environment variables now use provider-specific prefixes
2. Configuration file requires provider sections
3. Some login commands may need updating for explicit provider specification

## 🐛 Bug Fixes

- Resolved provider initialization and registration issues
- Fixed module import paths for proper package structure
- Enhanced error messages for authentication failures
- Improved handling of disabled/inaccessible repositories
- Fixed provider naming warnings for aliases

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:
- Architecture overview and provider design
- Configuration system documentation
- CLI command reference
- Provider-specific guides

## 🔮 What's Next

We're planning to add:
- GitLab provider support
- Batch operations across multiple providers
- Repository filtering and search
- Enhanced reporting and analytics

## 📞 Get Involved

- Report issues: [GitHub Issues](https://github.com/yourusername/mgit/issues)
- Contribute: See CONTRIBUTING.md
- Documentation: See docs/README.md

Thank you for using mgit! We hope this multi-provider support makes your repository management even more efficient.

---
*Released: January 29, 2025*
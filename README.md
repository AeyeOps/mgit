# mgit - Multi-Provider Git Repository Manager

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.4.0-blue.svg)](#)

**One CLI for all your Git repositories across Azure DevOps, GitHub, and BitBucket.**

## What is mgit?

Managing repositories across multiple Git providers is painful. You need different tools, different authentication, different commands. mgit solves this with a single CLI that works consistently across all major providers.

**Before mgit**: Multiple tools, scattered repos, manual synchronization  
**After mgit**: One command to find, clone, and update repositories anywhere

**Key Benefits:**
- **Universal**: Works with Azure DevOps, GitHub, and BitBucket
- **Powerful**: Pattern-based discovery finds repos across all providers  
- **Fast**: Concurrent operations with provider-optimized rate limiting
- **Secure**: Automatic credential masking and secure file permissions
- **Scale**: Tested with 1000+ repositories across enterprise environments

## Choose Your Provider

**Not sure which provider to use or have multiple?** mgit works with all of them.

| Provider | Best For | Repository Organization | Authentication |
|----------|----------|------------------------|----------------|
| **Azure DevOps** | Enterprise, .NET teams, Microsoft ecosystem | Projects → Repositories | Personal Access Token |
| **GitHub** | Open source, modern development, CI/CD | Organizations → Repositories | Personal Access Token |
| **BitBucket** | Atlassian tools (Jira/Confluence), small teams | Workspaces → Repositories | App Password |

**Most common scenarios:**
- **Enterprise with Azure/Office 365**: Start with Azure DevOps
- **Open source or modern development**: Start with GitHub  
- **Using Jira or Confluence**: Start with BitBucket
- **Multi-provider environment**: Configure all three

## 5-Minute Quick Start

**Goal**: Clone your first repositories in under 5 minutes.

### 1. Install mgit

**Option 1: Download Binary (Recommended)**
```bash
# Download latest Linux binary
wget https://github.com/AeyeOps/mgit/releases/latest/download/mgit
chmod +x mgit
sudo mv mgit /usr/local/bin/mgit

# Verify installation
mgit --version
# Should show: mgit version: 0.4.0
```

**Option 2: Build from Source**
```bash
git clone https://github.com/AeyeOps/mgit && cd mgit
pip install poetry
poetry install
poetry run poe build-linux
sudo cp dist/mgit /usr/local/bin/mgit
```

### 2. Choose and configure one provider

**GitHub (easiest to start):**
```bash
# Create token: GitHub → Settings → Developer settings → Personal access tokens
# Required scopes: repo, read:org
mgit login --provider github --name my_github
# Enter your token when prompted (format: ghp_...)
```

**Verify connection:**
```bash
mgit list "your-username/*/*" --limit 5
# Should show your repositories
```

### 3. Clone repositories

```bash
# Clone repositories matching pattern
mgit clone-all "your-username/*/*" ./test-repos

# Verify success
ls ./test-repos
# Should show cloned repository directories
```

**Success?** You now have mgit working! Continue to [Provider Setup](#provider-setup) for your full environment.

**Problems?** Check [Quick Troubleshooting](#quick-troubleshooting) below.

### Quick Troubleshooting

**"Command not found"**
```bash
# If you installed to /usr/local/bin, check PATH
echo $PATH | grep -q "/usr/local/bin" && echo "PATH is correct" || echo "Add /usr/local/bin to PATH"

# Or run directly
./mgit --version
```

**"Bad credentials" (GitHub)**
```bash
# Verify your token works
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
# Should return your user info, not 401 error
```

**"No repositories found"**
```bash
# Try broader pattern
mgit list "*/*/*" --limit 10
```

## Provider Setup

See detailed provider setup guides:
- **[Azure DevOps Guide](docs/providers/azure-devops-usage-guide.md)** - Enterprise setup with organizations and projects
- **[GitHub Guide](docs/providers/github-usage-guide.md)** - Open source and organization repositories  
- **[BitBucket Guide](docs/providers/bitbucket-usage-guide.md)** - Workspace and team repositories
- **[Provider Comparison](docs/providers/provider-comparison-guide.md)** - Feature comparison and selection guide

### Quick Setup (All Providers)
```bash
# Azure DevOps
mgit login --provider azuredevops --name work_ado

# GitHub  
mgit login --provider github --name personal_gh

# BitBucket
mgit login --provider bitbucket --name team_bb
```

## Core Operations

These are the commands you'll use daily with mgit.

### Find Repositories

**Pattern Format**: `organization/project/repository`
- **Azure DevOps**: Uses all three parts (org/project/repo)
- **GitHub/BitBucket**: Uses organization/repository (project part ignored)
- **Wildcards** (`*`) work in any position

#### Filtering Patterns Explained

**Basic Wildcards:**
```bash
mgit list "*/*/*"           # All repositories everywhere
mgit list "myorg/*/*"       # All repos in specific organization
mgit list "*/*/api-*"       # All repos starting with "api-"
mgit list "*/*/*-service"   # All repos ending with "-service"
```

**Provider-Specific Filtering:**
```bash
# Azure DevOps - Project-level filtering
mgit list "myorg/backend/*"     # Only backend project repos
mgit list "myorg/*/user-*"      # User-related repos across projects

# GitHub/BitBucket - Organization-level filtering  
mgit list "myorg/*/*"           # All org repos (project ignored)
mgit list "*/webapp/*"          # Any org with webapp repos
```

**Advanced Pattern Matching:**
```bash
# Multi-word matching
mgit list "*/*/*payment*gateway*"  # Contains both "payment" and "gateway"

# Provider-specific queries
mgit list "*/project/*" --provider work_ado    # Only Azure DevOps
mgit list "*/*/*" --provider github_personal   # Only GitHub

# Output filtering with CLI tools
mgit list "*/*/*" --format json | jq '.[] | select(.is_private == false)'
```

#### Common Usage Examples

```bash
# Basic discovery
mgit list "myorg/*/*" --limit 10        # First 10 repos in organization
mgit list "*/*/*" --format json         # All repos in JSON format

# Real-world examples (specify provider for organization access)
mgit list "AeyeOps/*/*" --provider github_aeyeops     # GitHub: all AeyeOps repos
mgit list "myworkspace/*/*" --provider bitbucket_team # BitBucket: all workspace repos  
mgit list "myorg/*/*" --provider work_ado             # Azure DevOps: all org repos
```

### Clone Multiple Repositories

```bash
# Clone from specific provider
mgit clone-all "myorg/backend/*" ./repos --provider work_ado

# Clone with custom concurrency (default: 4)
mgit clone-all "myorg/*/*" ./repos --concurrency 10

# Update existing repositories during clone
mgit clone-all "myorg/*/*" ./repos --update-mode pull
```

### Update Repositories

```bash
# Update all repositories in a directory
mgit pull-all "myproject" ./repos

# Update with specific provider
mgit pull-all "myorg" ./repos --provider github_personal

# Update with concurrency control
mgit pull-all "myproject" ./repos --concurrency 8
```

### Check Repository Status

```bash
# Status of all repos in directory (only shows dirty repos)
mgit status ./repos

# Include clean repos in output
mgit status ./repos --show-clean

# Fetch from remote before checking status
mgit status ./repos --fetch

# Fail if any repo has uncommitted changes (useful for CI)
mgit status ./repos --fail-on-dirty
```

## Configuration

mgit stores configuration in `~/.config/mgit/config.yaml`. Use `mgit login` to configure providers automatically.

For detailed configuration examples and troubleshooting, see:
- **[Configuration Examples](docs/configuration/mgit-configuration-examples.md)** - Complete YAML examples for all providers
- **[Query Patterns Guide](docs/usage/query-patterns.md)** - Repository discovery patterns

### Configuration Management

```bash
# List all configured providers
mgit config --list

# Show provider details (tokens automatically masked)
mgit config --show work_ado

# Set default provider
mgit config --set-default personal_gh

# Remove old configuration
mgit config --remove old_config
```

### Environment Variables (Limited)

```bash
# Legacy Azure DevOps support
export AZURE_DEVOPS_EXT_PAT=your-azure-pat

# Security settings
export MGIT_SECURITY_MASK_CREDENTIALS_IN_LOGS=true

# Proxy configuration (if needed)
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
```

## Real-World Patterns

### DevOps Team Workflows

```bash
# Find all infrastructure repositories
mgit list "*/*/infra*"
mgit list "*/*/terraform-*"

# Clone all API services for a project
mgit clone-all "myorg/*/api-*" ./api-services

# Update all repositories in workspace
mgit pull-all "." ./my-workspace

# Check which repos need attention
mgit status ./my-workspace --all
```

### Migration Scenarios

```bash
# Find all repos to migrate from old organization
mgit list "old-org/*/*" --format json > repos-to-migrate.json

# Clone all repos for migration
mgit clone-all "old-org/*/*" ./migration-workspace

# Verify migration readiness
mgit status ./migration-workspace --fail-on-dirty
```

### CI/CD Integration

```bash
# In CI pipeline - fail build if any repo is dirty
mgit status . --fail-on-dirty

# Update all repos in build environment
mgit pull-all "." --concurrency 20

# Clone specific repos for deployment
mgit clone-all "myorg/prod-*" ./deployment-repos
```

### Multi-Project Management

```bash
# Azure DevOps: Clone repos from multiple projects
mgit clone-all "myorg/Frontend/*" ./frontend-repos
mgit clone-all "myorg/Backend/*" ./backend-repos
mgit clone-all "myorg/Infrastructure/*" ./infra-repos

# GitHub: Organize by purpose  
mgit clone-all "AeyeOps/*/*" ./aeyeops --filter "*-api"
mgit clone-all "myusername/*/*" ./personal

# Cross-provider: Find similar repos everywhere
mgit list "*/*/*-service" --format json
```

## Command Reference

| Command | Description | Example |
|---------|-------------|---------|
| `mgit login` | Configure provider access | `mgit login --provider github --name work` |
| `mgit list <pattern>` | Find repositories | `mgit list "myorg/*/*"` |
| `mgit clone-all <pattern> <path>` | Clone repositories | `mgit clone-all "*/api-*" ./apis` |
| `mgit pull-all <pattern> <path>` | Update repositories | `mgit pull-all myorg ./repos` |
| `mgit status <path>` | Check repository status | `mgit status ./workspace` |
| `mgit config` | Manage configuration | `mgit config --list` |

### Global Options

| Option | Description | Default |
|--------|-------------|---------|
| `--provider NAME` | Use specific provider configuration | Default provider |
| `--concurrency N` | Number of parallel operations | 4 |
| `--update-mode MODE` | Handle existing directories: skip/pull/force | skip |
| `--format FORMAT` | Output format: table/json | table |
| `--debug` | Enable debug logging | false |

## Installation Options

### Pre-built Binary (Recommended)

```bash
# Linux
wget https://github.com/AeyeOps/mgit/releases/latest/download/mgit
chmod +x mgit && sudo mv mgit /usr/local/bin/mgit

# macOS (when available)
wget https://github.com/AeyeOps/mgit/releases/latest/download/mgit-macos
chmod +x mgit-macos && sudo mv mgit-macos /usr/local/bin/mgit

# Windows (when available)  
# Download mgit.exe from releases page
```

### From Source

```bash
# Build your own binary
git clone https://github.com/AeyeOps/mgit
cd mgit
pip install poetry
poetry install
poetry run poe build-linux    # Creates dist/mgit
sudo cp dist/mgit /usr/local/bin/
```

### For Contributors

```bash
# Development installation
git clone https://github.com/AeyeOps/mgit
cd mgit  
poetry install
poetry run mgit --version    # Use poetry run for development
```

**Note**: Pre-built releases coming soon. Currently requires building from source.

## Advanced Features

### Security

mgit implements comprehensive security controls:
- **Automatic credential masking** in all logs and output
- **Secure file permissions** (600) for configuration files
- **Input validation** prevents path traversal and injection attacks
- **Rate limiting** prevents API abuse
- **SSL/TLS verification** for all network communications

Security best practices:
```bash
# Never commit configuration files
echo "~/.config/mgit/" >> .gitignore

# Rotate credentials every 90 days
# Use minimal token scopes for each provider
```

### Performance

mgit is designed for enterprise scale:
- **Concurrent operations**: Provider-optimized rate limiting
- **Memory efficient**: Streaming for large repository sets  
- **Retry logic**: Automatic retry with exponential backoff
- **Scale tested**: 1000+ repositories across enterprise environments

Default performance settings:
- Concurrency: 4 operations (configurable)
- Rate limits: GitHub (10), Azure DevOps (4), BitBucket (5)  
- Timeout: 30 seconds per API call

### Performance Optimization

```bash
# Monitor performance with debug mode
mgit --debug list "large-org/*/*"

# Adjust concurrency for your environment
mgit clone-all "myorg/*/*" ./repos --concurrency 8

# Use specific patterns for faster queries
mgit list "myorg/specific-project/*"  # Better than broad wildcards
```

## Comprehensive Troubleshooting

### Network Issues

**Rate limiting**
```bash
# Reduce concurrency if hitting limits
mgit clone-all "large-org/*/*" ./repos --concurrency 2

# Use debug mode to see rate limit information
mgit --debug list "large-org/*/*"
```

**Corporate proxy/SSL**
```bash
# Configure proxy
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,.company.com

# For SSL certificate issues
export SSL_CERT_FILE=/path/to/corporate-ca.crt
```

### Configuration Issues

**Configuration not found**
```bash
# List current configuration
mgit config --list

# Check configuration file location (stored at ~/.config/mgit/config.yaml)
ls -la ~/.config/mgit/config.yaml
```

**Field name mismatches in YAML**
```bash
# Common configuration mistakes:
# ✗ Wrong: organization_url (should be org_url)
# ✗ Wrong: pat (should be token for GitHub)  
# ✗ Wrong: password (should be app_password for BitBucket)

# Use 'mgit login' to avoid manual YAML editing
```

### Performance Issues

**Slow operations**
```bash
# Reduce concurrency for stability
mgit clone-all "large-org/*/*" ./repos --concurrency 3

# Use specific patterns (faster than wildcards)
mgit list "myorg/specific-project/*"  # Better than "*/specific-project/*"

# Monitor performance with debug mode
mgit --debug clone-all "large-org/*/*" ./repos
```

### Advanced Pattern Matching

**Complex scenarios**
```bash
# DevOps team scenarios
mgit list "*/*/infra*"        # Infrastructure repos
mgit list "*/*/terraform-*"   # Terraform modules  
mgit list "*/*/*db*"          # Database-related repos

# Development patterns
mgit list "*/*/frontend-*"    # Frontend applications
mgit list "*/*/*-ui"          # UI repositories
mgit list "*/*/test-*"        # Test repositories

# Cross-organization search
mgit list "*/ProjectName/*"   # Find project across orgs

# Performance optimization
mgit list "myorg/backend/*"    # Specific (faster)
mgit list "*/*/*" --limit 500  # Limit large searches
```

### Getting Help

```bash
# Command-specific help
mgit --help
mgit <command> --help

# Debug mode for troubleshooting
mgit --debug list "myorg/*/*"

# Check configuration and provider status
mgit config --list
```

## Technical Reference

### Command Details: `mgit clone-all`

The `clone-all` command is mgit's most powerful feature, enabling bulk repository operations across providers. This section provides comprehensive documentation for advanced usage.

#### Command Syntax
```bash
mgit clone-all <pattern> <path> [OPTIONS]
```

#### Arguments and Options

| Parameter | Required | Short | Description | Example |
|-----------|----------|-------|-------------|---------|
| `pattern` | Yes | - | Pattern to match repositories (org/project/repo) | `"myorg/*/*"`, `"*/*/api-*"` |
| `path` | Yes | - | Target directory for cloning (relative or absolute) | `./repos`, `/home/user/code` |
| `--provider` | No | `-p` | Use specific provider configuration | `--provider github_work` |
| `--concurrency` | No | `-c` | Number of parallel clone operations (default: 4) | `--concurrency 10` |
| `--update-mode` | No | - | How to handle existing directories | `--update-mode pull` |

#### Update Modes Explained

| Mode | Behavior | Use Case |
|------|----------|----------|
| `skip` (default) | Skip directories that already exist | Safe default, no data loss |
| `pull` | Update existing Git repositories with `git pull` | Keep repos synchronized |
| `force` | Delete existing directories and clone fresh | Clean slate, requires confirmation |

#### Real-World Examples

```bash
# Basic usage - clone repos matching pattern
mgit clone-all "MyOrg/*/*" ./myproject-repos

# Clone with specific provider configuration
mgit clone-all "FrontendTeam/*/*" ./frontend --provider github_work

# Update existing repositories
mgit clone-all "BackendServices/*/*" ./backend --update-mode pull

# High-performance cloning for large organizations
mgit clone-all "AcmeCorp/*/*" ./acme --concurrency 20

# Force fresh clones (with confirmation prompt)
mgit clone-all "DevOpsTools/*/*" ./tools --update-mode force
```

#### Behavior Matrix

| Scenario | Existing Directory | Is Git Repo? | Update Mode | Action |
|----------|-------------------|--------------|-------------|---------|
| New clone | No | - | Any | Clone repository |
| Directory exists | Yes | Yes | `skip` | Skip, no action |
| Directory exists | Yes | Yes | `pull` | Execute `git pull` |
| Directory exists | Yes | No | `pull` | Skip with warning |
| Directory exists | Yes | Any | `force` | Prompt, then delete & clone |

#### Performance Considerations

- **Default concurrency (4)**: Balanced for most networks and systems
- **High concurrency (10-20)**: For fast networks and many small repos
- **Low concurrency (1-2)**: For large repos or limited bandwidth
- **Provider limits**: GitHub (10), Azure DevOps (4), BitBucket (5)

#### Error Handling

The command handles various failure scenarios gracefully:

- **Authentication failures**: Clear message with fix instructions
- **Network timeouts**: Automatic retry with exponential backoff
- **Disk space issues**: Fail fast with helpful error
- **Permission denied**: Skip repo and continue with others
- **Invalid project names**: Validate before starting operations

#### Advanced Patterns

```bash
# Clone from multiple projects into organized structure
for project in Frontend Backend Infrastructure; do
  mgit clone-all "$project" "./code/$project" --config azdo_work
done

# Selective cloning with post-processing
mgit list "MyOrg/*api*" --format json | \
  jq -r '.[].repository' | \
  xargs -I {} mgit clone-all MyOrg ./apis --filter {}

# Parallel provider operations
mgit clone-all WorkProject ./work --config github_work &
mgit clone-all PersonalProject ./personal --config github_personal &
wait
```

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development environment setup
- Code style guidelines  
- Testing requirements
- Pull request process

Development commands:
```bash
poetry run poe test     # Run tests
poetry run poe lint     # Check code quality
poetry run poe format   # Format code
poetry run poe build-all # Build binaries
```

### Release Process

mgit uses an automated release process that triggers when the version changes:

1. **Update Version**: Use either Poetry or the helper script
   ```bash
   # Using Poetry directly:
   poetry version patch  # For bug fixes (0.3.1 -> 0.3.2)
   poetry version minor  # For features (0.3.1 -> 0.4.0)
   poetry version major  # For breaking changes (0.3.1 -> 1.0.0)
   poetry version 1.2.3  # Specific version
   
   # Or using the helper script (wraps Poetry):
   python scripts/update_version.py patch
   python scripts/update_version.py minor
   python scripts/update_version.py major
   python scripts/update_version.py 1.2.3
   ```

2. **Update CHANGELOG.md**: Document your changes under the new version

3. **Commit and Push**:
   ```bash
   git add -A
   git commit -m "chore: bump version to X.Y.Z"
   git push origin main
   ```

The automated workflow will:
- Create a git tag
- Build Python packages and Docker images
- Generate AI-powered release notes from CHANGELOG
- Create GitHub release with binaries
- Publish to PyPI (if configured)

## Security

Please report vulnerabilities using the process outlined in our [Security Policy](SECURITY.md).

**Security features include:**
- Comprehensive threat model and risk analysis
- Automatic credential masking and sanitization
- Input validation and injection prevention  
- Security monitoring and event tracking
- Regular security testing and auditing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built for DevOps teams who manage repositories at scale.**
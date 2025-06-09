# mgit - Multi-Provider Git Repository Manager

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.13-blue.svg)](#)

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

```bash
# Install from source (requires Git and Python 3.9+)
git clone https://github.com/AeyeOps/mgit && cd mgit
pip install poetry  # if you don't have Poetry
poetry install
```

**Verify installation:**
```bash
poetry run mgit --version
# Should show: mgit version: 0.2.13
```

### 2. Choose and configure one provider

**GitHub (easiest to start):**
```bash
# Create token: GitHub → Settings → Developer settings → Personal access tokens
# Required scopes: repo, read:org
poetry run mgit login --provider github --name my_github
# Enter your token when prompted (format: ghp_...)
```

**Verify connection:**
```bash
poetry run mgit list "your-username/*/*" --limit 5
# Should show your repositories
```

### 3. Clone repositories

```bash
# Clone a few repositories to test
poetry run mgit clone-all "your-username/*/*" ./test-repos --limit 3

# Verify success
ls ./test-repos
# Should show cloned repository directories
```

**Success?** You now have mgit working! Continue to [Provider Setup](#provider-setup) for your full environment.

**Problems?** Check [Quick Troubleshooting](#quick-troubleshooting) below.

### Quick Troubleshooting

**"Command not found"**
```bash
# Try with explicit path
python -m mgit --version
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
poetry run mgit list "*/*/*" --limit 10
```

## Provider Setup

Configure mgit for your complete environment. You can set up multiple providers.

### Azure DevOps

**Best for**: Enterprise environments, Microsoft-centric organizations, project-based organization

#### 1. Create Personal Access Token
- Go to https://dev.azure.com/[your-organization]
- Click your profile icon → "Personal access tokens"
- Create token with scopes: **Code** (Read & Write), **Project and Team** (Read)
- Copy the token immediately (you won't see it again)

#### 2. Configure mgit
```bash
poetry run mgit login --provider azuredevops --name work_ado
# Enter organization URL: https://dev.azure.com/myorg
# Enter PAT when prompted
```

#### 3. Test and usage
```bash
# List projects (use Azure DevOps web interface to see available projects)
# Clone all repos from a project
poetry run mgit clone-all "myorg/DataEngineering/*" ./data-eng --config work_ado
```

**Azure DevOps uses project-based organization**: Repositories exist within projects, so you need the project name in your patterns.

#### Azure DevOps Troubleshooting
**"TF401019: Repository does not exist"**
```bash
# Check URL format - must include https://
# ✓ Correct: https://dev.azure.com/myorg
# ✗ Wrong: myorg.visualstudio.com
# ✗ Wrong: dev.azure.com/myorg (missing https://)

# Verify PAT scopes: Code (Read & Write), Project (Read)
poetry run mgit config --show work_ado
```

### GitHub

**Best for**: Open source development, modern CI/CD, developer experience

#### 1. Create Personal Access Token
- Go to GitHub → Settings → Developer settings → Personal access tokens
- Create "Classic" token with scopes: **repo**, **read:org**, **read:user**
- Copy the token (format: `ghp_` followed by 40 characters)

#### 2. Configure mgit
```bash
poetry run mgit login --provider github --name personal_gh
# Enter token when prompted
```

#### 3. Test and usage
```bash
# Clone personal repositories
poetry run mgit clone-all "your-username/*/*" ./personal-repos --config personal_gh

# Clone organization repositories  
poetry run mgit clone-all "AeyeOps/*/*" ./aeyeops-repos --config personal_gh
```

**GitHub uses flat organization**: No projects, just organizations/users containing repositories directly.

#### GitHub Troubleshooting
**"Bad credentials" or "401 Unauthorized"**
```bash
# Verify token format (should be ghp_ + 40 characters)
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user

# Check token scopes
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
```

### BitBucket

**Best for**: Atlassian ecosystem, small teams, workspace organization

#### 1. Create App Password (NOT Personal Access Token)
- Go to Bitbucket → Personal settings → App passwords
- Create password with permissions: **Repositories** (Read, Write), **Workspaces** (Read)
- Copy the app password immediately

#### 2. Configure mgit
```bash
poetry run mgit login --provider bitbucket --name team_bb
# Enter your BitBucket username (not email)
# Enter app password when prompted
```

#### 3. Test and usage
```bash
# Clone all repos from a workspace
poetry run mgit clone-all "myworkspace/*/*" ./workspace-repos --config team_bb
```

**BitBucket uses workspace organization**: Workspaces contain repositories (and optional projects).

#### BitBucket Troubleshooting
**"Invalid app password"**
```bash
# Use username, not email address
# ✓ Correct: BITBUCKET_USERNAME=myusername  
# ✗ Wrong: BITBUCKET_USERNAME=email@example.com

# Verify app password (not regular password)
curl -u YOUR_USERNAME:YOUR_APP_PASSWORD https://api.bitbucket.org/2.0/user
```

## Core Operations

These are the commands you'll use daily with mgit.

### Find Repositories

**Pattern Format**: `organization/project/repository`
- **Azure DevOps**: Uses all three parts (org/project/repo)
- **GitHub/BitBucket**: Uses organization/repository (project part ignored)
- **Wildcards** (`*`) work in any position

```bash
# Find repositories across all configured providers
mgit list "myorg/*/*"                    # All repos in organization
mgit list "*/*/api-*"                    # All API repositories
mgit list "*/*/*payment*"               # All payment-related repos

# Provider-specific patterns
mgit list "myorg/backend/*"              # Azure DevOps: specific project  
mgit list "AeyeOps/*/*"                 # GitHub: all repos in org
mgit list "myworkspace/*/*"             # BitBucket: all repos in workspace

# Output options
mgit list "myorg/*/*" --format json     # JSON for automation
mgit list "*/*/*" --limit 100           # Limit results
```

### Clone Multiple Repositories

```bash
# Clone from specific provider
mgit clone-all "myorg/backend/*" ./repos --config work_ado

# Clone with custom concurrency (default: 4)
mgit clone-all "myorg/*/*" ./repos --concurrency 10

# Clone with filtering
mgit clone-all "myorg/*/*" ./repos --filter "*-service"
```

### Update Repositories

```bash
# Update all repositories in a directory
mgit pull-all "myproject" ./repos

# Update with specific provider
mgit pull-all "myorg" ./repos --config github_personal

# Update with strategy
mgit pull-all "myproject" ./repos --strategy rebase
```

### Check Repository Status

```bash
# Status of all repos in directory (only shows dirty repos)
mgit status ./repos

# Include clean repos in output
mgit status ./repos --all

# Fetch from remote before checking status
mgit status ./repos --fetch

# Fail if any repo has uncommitted changes (useful for CI)
mgit status ./repos --fail-on-dirty
```

## Configuration

mgit stores configuration in `~/.config/mgit/config.yaml`. You usually don't need to edit this directly - use `mgit login` instead.

### Multiple Provider Setup

```yaml
# ~/.config/mgit/config.yaml (created by 'mgit login')
global:
  default_provider: work_ado
  default_concurrency: 8

providers:
  work_ado:
    org_url: https://dev.azure.com/myorg    # Note: 'org_url' not 'organization_url'
    pat: your-azure-devops-pat
    
  personal_gh:
    token: ghp_your-github-token            # Note: 'token' not 'pat' for GitHub
    
  team_bb:
    username: myusername
    app_password: your-bitbucket-app-password
    workspace: myworkspace
```

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
| `--config NAME` | Use specific provider configuration | Default provider |
| `--concurrency N` | Number of parallel operations | 4 |
| `--update-mode MODE` | Handle existing directories: skip/pull/force | skip |
| `--format FORMAT` | Output format: table/json | table |
| `--debug` | Enable debug logging | false |

## Installation Options

### From Source (Recommended)

```bash
# Clone and install with Poetry
git clone https://github.com/AeyeOps/mgit
cd mgit
pip install poetry  # if needed
poetry install

# Run mgit
poetry run mgit --version
```

### Build Binaries

```bash
# Build platform-specific binaries
poetry run poe build-linux    # Linux binary
poetry run poe build-windows  # Windows binary
poetry run poe build-all      # All platforms
```

**Note**: PyPI packages and pre-built releases planned for future versions.

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

### Monitoring

Enable monitoring for production environments:

```bash
# Start monitoring server
mgit monitoring server --port 8080

# Check health status  
mgit monitoring health --detailed

# Available endpoints:
# /metrics - Prometheus metrics
# /health - Overall health
# /health/ready - Readiness probe (Kubernetes)
# /health/live - Liveness probe (Kubernetes)
```

## Comprehensive Troubleshooting

### Network Issues

**Rate limiting**
```bash
# Reduce concurrency if hitting limits
mgit clone-all "large-org/*/*" ./repos --concurrency 2

# Check current rate limit status
mgit monitoring metrics | grep rate_limit
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
# Check configuration location
mgit config --show-path
# Should show: ~/.config/mgit/config.yaml

# List current configuration
mgit config --list
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

# Monitor performance
mgit monitoring performance --hours 1
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

# Check system health
mgit monitoring health --detailed
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

## Security

For security vulnerabilities, see our [Security Policy](SECURITY.md).

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
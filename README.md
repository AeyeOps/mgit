# mgit - Multi-Provider Git Repository Manager

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.13-blue.svg)](#)

Efficiently manage repositories across Azure DevOps, GitHub, and BitBucket from a single CLI.

## What is mgit?

DevOps teams managing hundreds of repositories across multiple providers face daily challenges with discovery, synchronization, and bulk operations. mgit provides a unified interface to work with all your repositories regardless of where they're hosted.

**Key Benefits:**
- Single tool for all major Git providers (Azure DevOps, GitHub, BitBucket)
- Bulk operations that respect API rate limits
- Pattern-based repository discovery across providers
- Concurrent execution for performance at scale
- Secure credential management with token masking and safe file permissions

## Requirements

- **Python**: 3.9+ (if using pip installation) or standalone binary
- **Git**: 2.25+
- **Credentials**: Personal Access Tokens for each provider
- **OS**: Linux, macOS, Windows

## Quick Start

```bash
# 1. Install mgit from source
git clone https://github.com/AeyeOps/mgit && cd mgit
poetry install --with dev

# 2. Configure provider access
poetry run mgit login --provider github --name work

# 3. Find repositories across all providers
poetry run mgit list "myorg/*/*"

# 4. Clone multiple repositories
poetry run mgit clone-all "myorg/backend/*" ./repos

# 5. Check status across all repositories
poetry run mgit status ./repos
```

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/AeyeOps/mgit
cd mgit

# Install with Poetry
poetry install --with dev

# Run mgit
poetry run mgit --version
# Should show: mgit version: 0.2.13

# Or install globally
poetry build
pip install dist/mgit-0.2.13-py3-none-any.whl
```

### Building Binaries

```bash
# Build Linux binary
poetry run poe build-linux

# Build Windows binary
poetry run poe build-windows

# Build all platforms
poetry run poe build-all
```

**Note**: Pre-built releases and PyPI packages are planned for future versions.

## Provider Setup

### Azure DevOps

1. **Create Personal Access Token:**
   - Go to Azure DevOps → User Settings → Personal Access Tokens
   - Create token with: Code (Read & Write), Project and Team (Read)

2. **Configure mgit:**
   ```bash
   mgit login --provider azuredevops --name work_ado
   # Enter organization URL: https://dev.azure.com/myorg
   # Enter PAT when prompted
   ```

### GitHub

1. **Create Personal Access Token:**
   - Go to GitHub → Settings → Developer settings → Personal access tokens
   - Create token with: repo, read:org scopes

2. **Configure mgit:**
   ```bash
   mgit login --provider github --name personal_gh
   # Enter token when prompted
   ```

### BitBucket

1. **Create App Password:**
   - Go to Bitbucket → Personal settings → App passwords
   - Create password with: Repositories (Read), Account (Read)

2. **Configure mgit:**
   ```bash
   mgit login --provider bitbucket --name team_bb
   # Enter username and app password when prompted
   ```

## Core Commands

### Repository Discovery

Find repositories using flexible patterns:

```bash
# All repositories everywhere
mgit list "*/*/*"

# All repositories in specific organization
mgit list "myorg/*/*"

# Find repositories by name pattern
mgit list "*/*/api-*"         # APIs
mgit list "*/*/*-service"     # Microservices
mgit list "*/*/*payment*"    # Payment-related

# Output as JSON for automation
mgit list "myorg/*/*" --format json

# Limit results
mgit list "*/*/*" --limit 100
```

**Pattern Format:** `organization/project/repository`
- **Azure DevOps**: Uses all three parts
- **GitHub/BitBucket**: Uses organization/repository (project ignored)
- Wildcards (`*`) supported in any position
- Case-insensitive matching

### Bulk Operations

Clone multiple repositories:
```bash
# Clone from specific provider
mgit clone-all "myorg/backend/*" ./repos --config work_ado

# Auto-detect provider from URL
mgit clone-all myproject ./repos --url https://dev.azure.com/myorg

# High-speed with custom concurrency
mgit clone-all myorg ./repos --concurrency 10
```

Update repositories:
```bash
# Pull all repositories in directory
mgit pull-all myproject ./repos

# Update with specific provider
mgit pull-all myorg ./repos --config github_personal
```

Check repository status:
```bash
# Status of all repos in directory
mgit status ./repos

# Include clean repos in output
mgit status ./repos --all

# Fetch from remote before checking
mgit status ./repos --fetch

# Fail if any repo has uncommitted changes (useful for CI)
mgit status ./repos --fail-on-dirty
```

### Configuration Management

```bash
# List all configured providers
mgit config --list

# Show provider details (tokens masked)
mgit config --show work_ado

# Set default provider
mgit config --set-default personal_gh

# Remove old configuration
mgit config --remove old_config
```

## Configuration

mgit uses YAML configuration with support for multiple provider profiles:

**Configuration file location:**
- All platforms: `~/.config/mgit/config.yaml`

**Example configuration:**
```yaml
global:
  default_provider: work_ado
  default_concurrency: 8
  default_update_mode: pull

providers:
  work_ado:
    organization_url: https://dev.azure.com/myorg
    pat: your-azure-devops-pat
    
  personal_gh:
    pat: ghp_your-github-token
    
  team_bb:
    username: myusername
    app_password: your-bitbucket-app-password
    workspace: myworkspace
```

**Environment variables (limited support):**
```bash
# Only Azure DevOps PAT is supported via environment variable
export AZURE_DEVOPS_EXT_PAT=your-azure-pat

# Security settings (advanced users)
export MGIT_SECURITY_MASK_CREDENTIALS_IN_LOGS=true
export MGIT_SECURITY_VERIFY_SSL_CERTIFICATES=true
```

## Common Use Cases

### DevOps Team Workflows

```bash
# Find all infrastructure repositories
mgit list "*/*/infra*"
mgit list "*/*/terraform-*"

# Clone all API services for a project
mgit clone-all "myorg/*/api-*" ./api-services

# Update all repositories in workspace
mgit pull-all . ./my-workspace

# Check which repos need attention
mgit status ./my-workspace --all
```

### Migration Scenarios

```bash
# Find all repos to migrate
mgit list "old-org/*/*" --format json > repos-to-migrate.json

# Clone all repos for migration
mgit clone-all "old-org/*/*" ./migration-workspace

# Verify migration status
mgit status ./migration-workspace --fail-on-dirty
```

### CI/CD Integration

```bash
# In CI pipeline - fail if any repo is dirty
mgit status . --fail-on-dirty

# Update all repos in build environment
mgit pull-all . --concurrency 20

# Clone specific repos for deployment
mgit clone-all "myorg/prod-*" ./deployment-repos
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
| `--config NAME` | Use specific provider | Default provider |
| `--concurrency N` | Parallel operations | 4 |
| `--update-mode MODE` | Handle existing: skip/pull/force | skip |
| `--format FORMAT` | Output: table/json | table |
| `--debug` | Enable debug logging | false |

## Security Features

- **Token Masking** in all logs and console output
- **Secure File Permissions** (600) for config files  
- **Input Validation** with path and URL sanitization
- **Credential Logging Prevention** - tokens never appear in logs
- **Security Monitoring** with event tracking

Configuration files are automatically created with secure permissions (0600). All credential values are masked in logs, console output, and error messages. Comprehensive input validation prevents path traversal and injection attacks.

## Performance

mgit is designed for enterprise scale:
- **Concurrent Operations**: Provider-optimized rate limiting
- **Memory Efficient**: Streaming operations for large result sets
- **Retry Logic**: Automatic retry with exponential backoff
- **Scale**: Tested with 1000+ repositories

Default settings:
- Concurrency: 4 concurrent operations (configurable)
- Update mode: skip (don't overwrite existing directories)
- Timeout: 30 seconds per API call
- Rate limiting: Tracking only (no enforcement)

## Troubleshooting

### Common Issues

**Command not found**
```bash
# Check if mgit is in PATH
which mgit
# Add to PATH if needed
export PATH="$PATH:/path/to/mgit"
```

**Authentication errors**
```bash
# Test provider configuration
mgit config --show provider_name
# Re-run login if needed
mgit login --provider github --name provider_name
```

**Rate limiting**
```bash
# Reduce concurrency
mgit clone-all "pattern" ./path --concurrency 2
```

**SSL/TLS errors (corporate proxies)**
```bash
# Set proxy variables
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

# Note: SSL certificate verification uses system defaults
# For custom certificates, configure your system trust store
```

### Getting Help

Run `mgit --help` or `mgit <command> --help` for detailed usage information.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development environment setup
- Code style guidelines
- Testing requirements
- Pull request process

## Security

For security vulnerabilities, please see our [Security Policy](SECURITY.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built for DevOps teams who manage repositories at scale.**
# mgit - Multi-Provider Git CLI Tool 🚀

[![GitHub Release](https://img.shields.io/github/release/AeyeOps/mgit.svg)](https://github.com/AeyeOps/mgit/releases/latest)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Security](https://img.shields.io/badge/Security-Enterprise_Grade-green)](docs/security)

**The modern CLI for DevOps teams managing repositories across Azure DevOps, GitHub, and BitBucket.**

Discover, clone, and manage hundreds of repositories with powerful query patterns, enhanced progress tracking, and enterprise-grade configuration management.

## ✨ What Makes mgit Special

🔍 **Smart Repository Discovery** - Find repositories across providers using powerful query patterns like `"pdidev/*/*"` or `"*/*/payment*"`

📊 **Professional Progress Tracking** - Multi-level progress bars show real-time discovery and operation status

🏢 **Enterprise Configuration** - YAML-based config system with named provider profiles and secure credential management

⚡ **Blazing Fast Operations** - Async operations with intelligent concurrency limits optimized per provider

🎯 **Provider Agnostic** - Identical commands work across Azure DevOps, GitHub, and BitBucket

## Quick Start

```bash
# 1. Install mgit
pip install https://github.com/AeyeOps/mgit/releases/download/v0.2.3/mgit-0.2.3-py3-none-any.whl

# 2. Set up your first provider
mgit login --provider azuredevops --name work_ado

# 3. Discover repositories
mgit list "pdidev/*/*"

# 4. Clone everything from a project
mgit clone-all "pdidev/PDIOperations/*" ./my-repos
```

## 🔍 Repository Discovery

The `mgit list` command provides powerful repository discovery across all your providers:

```bash
# Find all repositories everywhere
mgit list "*/*/*"

# Find all repos in specific organization
mgit list "myorg/*/*" 

# Find all payment-related repos
mgit list "*/*/pay*"

# Find repos in specific project  
mgit list "myorg/backend/*"

# Output as JSON for automation
mgit list "*/*/*" --format json --limit 100
```

**Features:**
- 🌐 Cross-provider search with single command
- 📈 Real-time progress with live repository counters
- 🎯 Flexible pattern matching (wildcards supported)
- 📋 Rich table output or JSON for automation
- ⚡ Async discovery for maximum speed

## 🚀 Bulk Operations

### Clone All Repositories

```bash
# Clone from specific provider configuration
mgit clone-all "myorg/backend/*" ./repos --config work_ado

# Auto-detect provider from URL  
mgit clone-all myproject ./repos --url https://dev.azure.com/myorg

# High-speed cloning with custom concurrency
mgit clone-all myorg ./repos --concurrency 10

# Force mode with confirmation prompts
mgit clone-all myproject ./repos --update-mode force
```

### Bulk Updates

```bash
# Pull all repositories in a directory
mgit pull-all myproject ./repos

# Update with specific provider
mgit pull-all myorg ./repos --config github_personal
```

## 🏢 Provider Management

### Authentication & Setup

```bash
# Interactive setup for Azure DevOps
mgit login --provider azuredevops --name company_ado

# GitHub with Personal Access Token  
mgit login --provider github --name personal_gh --token ghp_xxxxx

# BitBucket workspace
mgit login --provider bitbucket --name team_bb --username myuser

# Test existing configuration
mgit login --config work_ado
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

# View global settings
mgit config --global
```

## 📊 Enhanced Progress Tracking

mgit v0.2.3 features professional-grade progress tracking:

```
⠋ Processing organizations (1/3) • 1,247 repos found
  └─ Scanning myorg
      └─ backend-services: 45 repos
      └─ frontend-apps: 23 repos
      └─ devops-tools: 12 repos
```

**Features:**
- 🔄 Real-time discovery progress
- 📈 Live repository counters  
- 🌳 Hierarchical display (Organizations → Projects → Repositories)
- ⏱️ Non-blocking progress updates
- 🎯 Per-project and per-organization tracking

## 💻 Installation

### Option 1: Install from GitHub Release (Recommended)

```bash
# Latest stable release
pip install https://github.com/AeyeOps/mgit/releases/download/v0.2.3/mgit-0.2.3-py3-none-any.whl

# Verify installation
mgit --version  # Should show: mgit version: 0.2.3
```

### Option 2: Pre-built Binaries (No Python Required)

Download standalone executables from [releases](https://github.com/AeyeOps/mgit/releases/latest):

```bash
# Linux
wget https://github.com/AeyeOps/mgit/releases/download/v0.2.3/mgit-linux-x64
chmod +x mgit-linux-x64
./mgit-linux-x64 --version

# macOS  
curl -L https://github.com/AeyeOps/mgit/releases/download/v0.2.3/mgit-macos-x64 -o mgit
chmod +x mgit && ./mgit --version

# Windows
# Download mgit-windows-x64.exe from releases page
```

### Option 3: Docker

```bash
# Pull and run
docker pull ghcr.io/aeyeops/mgit:v0.2.3
docker run --rm ghcr.io/aeyeops/mgit:v0.2.3 --version

# Create convenient alias
alias mgit='docker run --rm -v $(pwd):/workspace -v ~/.config/mgit:/root/.config/mgit ghcr.io/aeyeops/mgit:v0.2.3'
```

### Option 4: From Source

```bash
git clone https://github.com/AeyeOps/mgit.git
cd mgit
poetry install --with dev
poetry run mgit --version
```

## 🔧 Configuration

mgit uses a modern YAML-based configuration system with named provider profiles:

### Configuration File Location
- **Linux/macOS**: `~/.config/mgit/config.yaml`
- **Windows**: `%APPDATA%\mgit\config.yaml`

### Example Configuration

```yaml
# ~/.config/mgit/config.yaml
global:
  default_provider: work_ado
  default_concurrency: 8
  default_update_mode: pull
  log_level: INFO

providers:
  work_ado:
    org_url: https://dev.azure.com/mycompany
    pat: your-azure-devops-pat
    
  personal_gh:
    token: ghp_your-github-token
    
  team_bb:
    username: myuser
    app_password: your-bitbucket-app-password
```

### Environment Variable Override

Any setting can be overridden with environment variables:

```bash
export MGIT_DEFAULT_CONCURRENCY=16
export AZURE_DEVOPS_EXT_PAT=your-token
export GITHUB_TOKEN=your-token
export BITBUCKET_APP_PASSWORD=your-password
```

## 📚 Command Reference

### Repository Discovery

| Command | Description |
|---------|-------------|
| `mgit list "org/proj/repo"` | Find repositories matching pattern |
| `mgit list "*/*/*" --format json` | Output all repos as JSON |
| `mgit list "*/*/*" --limit 50` | Limit results to 50 repositories |

### Bulk Operations  

| Command | Description |
|---------|-------------|
| `mgit clone-all "pattern" ./dir` | Clone matching repositories |
| `mgit pull-all project ./dir` | Update all repos in directory |

### Provider Management

| Command | Description |
|---------|-------------|
| `mgit login --provider TYPE --name NAME` | Set up new provider configuration |
| `mgit config --list` | List all configured providers |
| `mgit config --show NAME` | Show provider details |
| `mgit config --set-default NAME` | Set default provider |

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--config NAME` | Use specific provider configuration | Default provider |
| `--concurrency N` | Concurrent operations | 4 |
| `--update-mode MODE` | Handle existing dirs: skip/pull/force | skip |
| `--format FORMAT` | Output format: table/json | table |

## 🎯 Query Patterns

mgit supports flexible pattern matching for repository discovery:

| Pattern | Matches | Example |
|---------|---------|---------|
| `"*/*/*"` | All repos from all orgs/projects | All repositories |
| `"myorg/*/*"` | All repos in organization | All repos in "myorg" |
| `"*/backend/*"` | All backend projects | Any org, project named "backend" |
| `"myorg/*/api*"` | API repos in myorg | Repos starting with "api" |
| `"*/*/payment*"` | Payment-related repos | Repos starting with "payment" |

**Pattern Rules:**
- Use `*` for wildcards (matches any characters)
- Three parts: `organization/project/repository` (Azure DevOps)
- Two parts: `organization/repository` (GitHub, BitBucket)
- Case-insensitive matching
- Supports partial matches with wildcards

## 🏢 Provider Support

| Provider | Authentication | Organization Structure | API Rate Limits |
|----------|---------------|----------------------|-----------------|
| **Azure DevOps** | Personal Access Token (PAT) | Organization → Project → Repository | Generous (enterprise) |
| **GitHub** | Personal Access Token | Organization/User → Repository | 5,000/hour (authenticated) |
| **BitBucket** | App Password | Workspace → Repository | 1,000/hour |

**All providers support:**
- ✅ Repository discovery with patterns
- ✅ Bulk clone operations  
- ✅ Concurrent operations with provider-optimized limits
- ✅ Progress tracking and error handling
- ✅ Secure credential management

## 🔐 Security Features

- 🔒 **AES-256 Encryption** for stored credentials
- 🎭 **Token Masking** in all logs and console output  
- 📁 **Secure File Permissions** (600) for config files
- 🔑 **Multiple Auth Methods** per provider
- 🚫 **No Credential Logging** - tokens never appear in logs
- 🛡️ **Environment Variable Support** for CI/CD security

## 📊 Performance & Scalability

- ⚡ **Async Operations** - All network calls are non-blocking
- 🎯 **Provider-Optimized Concurrency** - Respects API rate limits
- 📈 **Scalable to 1000+ Repositories** - Tested with large enterprise setups
- 💾 **Minimal Memory Footprint** - Efficient async iteration
- 🔄 **Intelligent Error Recovery** - Continues on individual repo failures

## 🚧 Migration from v0.1.x

If upgrading from mgit v0.1.x:

1. **Configuration Migration**: Old `.env` files are automatically migrated to YAML
2. **New Commands**: Use `mgit list` instead of manual repository enumeration
3. **Provider Setup**: Re-run `mgit login` to set up named provider configurations
4. **Query Patterns**: Update scripts to use new pattern-based discovery

```bash
# Old way (v0.1.x)
mgit clone-all myproject ./repos

# New way (v0.2.3)
mgit clone-all "myorg/myproject/*" ./repos --config work_ado
```

## 🤝 Contributing

Contributions welcome! See our [development guide](docs/development.md) for:

- Setting up development environment
- Running tests (`pytest tests/ -v --cov=mgit`)
- Building binaries (`poe build-linux`)
- Code style guidelines (Black, Ruff)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built for DevOps teams who manage repositories at scale.** 🚀

For technical details, see [CLAUDE.md](CLAUDE.md) and the [docs/](docs/) directory.
# mgit - Multi-Provider Git CLI Tool 🚀

[![GitHub Release](https://img.shields.io/github/release/AeyeOps/mgit.svg)](https://github.com/AeyeOps/mgit/releases/latest)
[![Install from GitHub](https://img.shields.io/badge/pip%20install-GitHub%20Release-brightgreen)](https://github.com/AeyeOps/mgit/releases/latest)
[![Docker Image](https://img.shields.io/docker/v/aeyeops/mgit?label=docker)](https://ghcr.io/aeyeops/mgit)
[![Security](https://img.shields.io/badge/Security-AES--256-green)](docs/security)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A powerful **enterprise-grade** command-line tool for managing repositories across multiple git platforms. Clone entire projects, update multiple repositories, and automate your git workflows with support for:

✅ **Azure DevOps** - Full feature support with organizations and projects  
✅ **GitHub** - Complete integration for organizations and users  
✅ **BitBucket** - Full workspace and repository management  

**All providers have feature parity** - login, clone-all, pull-all, and configuration work identically across platforms.

Ready for production deployment with comprehensive security, monitoring, and automation capabilities.

## Provider Comparison

| Feature | Azure DevOps | GitHub | BitBucket |
|---------|--------------|--------|-----------|
| **Authentication** | Personal Access Token (PAT) | Personal Access Token | App Password |
| **Repository Scope** | Projects | Organizations/Users | Workspaces |
| **API Support** | Full REST API v7.1 | Full REST API v3 | Full REST API v2.0 |
| **Concurrent Operations** | 4 (default) | 10 (default) | 5 (default) |
| **Enterprise Support** | Yes | Yes (GitHub Enterprise) | Yes (BitBucket Server) |
| **Disabled Repo Handling** | ✅ Auto-skip | ✅ Auto-skip | ✅ Auto-skip |
| **Clone Methods** | HTTPS/SSH | HTTPS/SSH | HTTPS/SSH |
| **Rate Limiting** | Generous | 5000/hour (authenticated) | 1000/hour |

## Overview

mgit simplifies repository management across multiple git providers:
- Clone all repositories from any supported git provider with a single command
- Pull updates for multiple repositories simultaneously across different platforms
- Configure provider-specific settings with a unified interface
- Manage authentication credentials securely for all providers
- Automatically handle disabled repositories with clear reporting
- Auto-detect providers from URLs or specify explicitly

Built with Python using modern package structure, leveraging asynchronous operations for speed and providing rich console output for better visibility.

## Project Structure

```
mgit/
├── mgit/                    # Main package
│   ├── __main__.py         # Entry point
│   ├── cli/                # CLI components  
│   ├── config/             # Configuration management
│   ├── git/                # Git operations
│   └── utils/              # Utility functions
├── docs/                   # Comprehensive documentation
│   ├── architecture/       # Technical design docs
│   └── configuration/      # Config system docs
└── scripts/               # Automation scripts
```

## Installation

### Prerequisites

- **Git** (required for all installation methods)
- **Python 3.8+** (for pip and source installation)
- **Docker** (for containerized installation)

### Installation Methods

#### 1. Install from GitHub Release (Recommended)

```bash
# Install the latest release
pip install https://github.com/AeyeOps/mgit/releases/download/v0.2.1/mgit-0.2.1-py3-none-any.whl

# Verify installation
mgit --version
```

#### 2. Download Pre-built Binary (No Python Required)

Download the standalone executable for your platform from the [latest release](https://github.com/AeyeOps/mgit/releases/latest):

```bash
# Linux
wget https://github.com/AeyeOps/mgit/releases/download/v0.2.1/mgit-v0.2.1-linux-x64
chmod +x mgit-v0.2.1-linux-x64
./mgit-v0.2.1-linux-x64 --version

# macOS
curl -L https://github.com/AeyeOps/mgit/releases/download/v0.2.1/mgit-v0.2.1-macos-x64 -o mgit
chmod +x mgit
./mgit --version

# Windows (PowerShell)
Invoke-WebRequest -Uri https://github.com/AeyeOps/mgit/releases/download/v0.2.1/mgit-v0.2.1-windows-x64.exe -OutFile mgit.exe
.\mgit.exe --version
```

#### 3. Use Docker

```bash
# Pull the latest image
docker pull ghcr.io/aeyeops/mgit:latest

# Run mgit
docker run --rm ghcr.io/aeyeops/mgit:latest --version

# Create an alias for convenience
alias mgit='docker run --rm -v $(pwd):/workspace -v ~/.config/mgit:/root/.config/mgit ghcr.io/aeyeops/mgit:latest'
```

#### 4. Install from Source

```bash
# Clone the repository
git clone https://github.com/AeyeOps/mgit.git
cd mgit

# Install in development mode
pip install -r requirements.txt
pip install -e .

# Run mgit
mgit --version
```

### Post-Installation Setup

1. **Verify Installation**
   ```bash
   mgit --version
   mgit --help
   ```

2. **Optional: Add to PATH**
   ```bash
   # For downloaded binaries
   sudo mv mgit-v0.2.1-linux-x64 /usr/local/bin/mgit
   ```

3. **Configure Authentication**
   ```bash
   # Set up credentials for your providers
   mgit login --provider github --token YOUR_TOKEN --store
   mgit login --provider azuredevops --org https://dev.azure.com/your-org --token YOUR_PAT --store
   mgit login --provider bitbucket --username YOUR_USER --token YOUR_APP_PASSWORD --store
   ```

## Quick Start

### Basic Operations

Get the current version:
```bash
# If installed via pip
mgit --version

# If using Docker
docker run --rm ghcr.io/aeyeops/mgit:latest --version

# If running from source
python -m mgit --version
```

### Authentication

Authenticate with your git provider:

#### Azure DevOps
```bash
# Interactive login (using pip-installed version)
mgit login --provider azuredevops

# Or specify credentials directly
mgit login --provider azuredevops --org https://dev.azure.com/your-org --token your-pat

# Using Docker (credentials saved in mounted volume)
docker run --rm -v ~/.config/mgit:/root/.config/mgit ghcr.io/aeyeops/mgit:latest login --provider azuredevops --store
```

#### GitHub
```bash
# Personal or organization repositories
mgit login --provider github --token your-github-pat

# GitHub Enterprise
mgit login --provider github --org https://github.enterprise.com --token your-pat
```

#### BitBucket
```bash
# BitBucket Cloud with app password
mgit login --provider bitbucket --org your-workspace --token your-app-password
```

Note: Use `--store` flag to save credentials to config file (~/.config/mgit/config)

### Clone All Repositories

Clone all repositories from a project/organization/workspace:

#### Auto-detect provider from URL
```bash
# Azure DevOps
mgit clone-all my-project ./repos https://dev.azure.com/my-org

# GitHub  
mgit clone-all my-org ./repos https://github.com

# BitBucket
mgit clone-all my-workspace ./repos https://bitbucket.org

# Using Docker
docker run --rm -v $(pwd):/workspace ghcr.io/aeyeops/mgit:latest clone-all my-org /workspace/repos https://github.com
```

#### Explicit provider selection
```bash
# Azure DevOps project
mgit clone-all my-project ./repos --provider azuredevops

# GitHub organization or user
mgit clone-all octocat ./repos --provider github

# BitBucket workspace
mgit clone-all my-workspace ./repos --provider bitbucket
```

#### With custom options
```bash
# Clone with 8 concurrent operations and force mode
mgit clone-all my-project ./repos -c 8 -u force --provider azuredevops

# GitHub with higher concurrency (supports more connections)
mgit clone-all my-org ./repos -c 20 --provider github

# Docker with environment variables for auth
docker run --rm \
  -e GITHUB_PAT=your-token \
  -v $(pwd):/workspace \
  ghcr.io/aeyeops/mgit:latest \
  clone-all my-org /workspace/repos -c 20 --provider github
```

### Update All Repositories

Pull the latest changes for all repositories:

```bash
# Auto-detect provider from existing repo remotes
mgit pull-all my-project ./repos

# Or specify provider explicitly
mgit pull-all my-org ./repos --provider github
mgit pull-all my-workspace ./repos --provider bitbucket

# Using Docker
docker run --rm -v $(pwd):/workspace ghcr.io/aeyeops/mgit:latest pull-all my-project /workspace/repos
```

### Global Configuration

View or set global configuration:

```bash
# Show current settings for all providers
mgit config --show

# Set default values
mgit config --concurrency 16 --update-mode pull

# Set provider-specific configuration
mgit config --provider azuredevops --org https://dev.azure.com/your-org
mgit config --provider github --org your-github-org  
mgit config --provider bitbucket --workspace your-workspace
```

## Commands Reference

Run without arguments to see available commands:

```bash
mgit

# Or with Docker
docker run --rm ghcr.io/aeyeops/mgit:latest
```

### Core Git Commands

#### login

Authenticate with a git provider using appropriate credentials.

```bash
mgit login [--provider PROVIDER] [--org URL] [--token TOKEN] [--store/--no-store]
```

Options:
- `--provider`: Git provider (azuredevops, github, bitbucket) - defaults to azuredevops
- `--org`: Organization/workspace URL (provider-specific)
- `--token`: Access token (PAT for Azure DevOps/GitHub, App Password for BitBucket)
- `--store`: Save credentials to config file

#### clone-all

Clone all repositories from a provider project/organization/workspace.

```bash
mgit clone-all PROJECT DESTINATION [URL] [--provider PROVIDER] [--concurrency N] [--update-mode MODE]
```

Arguments:
- `PROJECT`: Project name (Azure DevOps), organization/user (GitHub), or workspace (BitBucket)
- `DESTINATION`: Local directory to clone into
- `URL`: Optional organization URL (auto-detects provider)

Options:
- `--provider`: Explicitly specify provider (azuredevops, github, bitbucket)
- `--concurrency`: Number of concurrent operations (default: 4)
- `--update-mode`: How to handle existing directories:
  - `skip`: Skip existing directories (default)
  - `pull`: Try to git pull if it's a valid repository
  - `force`: Remove existing directories and clone fresh

#### pull-all

Pull updates for all repositories in a directory.

```bash
mgit pull-all PROJECT REPOSITORY_PATH [--provider PROVIDER]
```

The provider is usually auto-detected from the git remotes, but can be specified explicitly.

#### config

View or set global configuration settings.

```bash
mgit config [--show] [--org URL] [--concurrency N] [--update-mode MODE]
```

#### generate-env

Generate a sample environment file with configuration options.

```bash
mgit generate-env
```

### Global Options

#### --version

Show the application's version and exit.

```bash
mgit --version
```

#### --help

Show help for any command.

```bash
mgit [command] --help
```

## 🕹️ Configuration (Totally Rad Edition)

```
╔═══════════════════════════════════════════════════════════════╗
║  ░▒▓█ CONFIGURATION HIERARCHY █▓▒░  (Like a High Score List) ║
╠═══════════════════════════════════════════════════════════════╣
║  1. 🏆 Environment Variables    [HIGHEST PRIORITY]            ║
║  2. 💾 Config File              [~/.config/mgit/config]       ║  
║  3. 📼 Default Values           [Built-in defaults]           ║
╚═══════════════════════════════════════════════════════════════╝
```

### 🎮 Dual Configuration System

mgit supports **BOTH** environment variables AND config file settings! Mix and match like your favorite 80s mixtape! 🎵

### 📊 Configuration Reference Table

| Environment Variable | Config File Key | Default | What It Does | Required? |
|---------------------|-----------------|---------|--------------|----------|
| **🌐 Global Settings** |||||
| `DEFAULT_CONCURRENCY` | `DEFAULT_CONCURRENCY` | `4` | Max parallel git operations (like multi-ball in pinball!) | No |
| `DEFAULT_UPDATE_MODE` | `DEFAULT_UPDATE_MODE` | `skip` | How to handle existing repos: `skip`/`pull`/`force` | No |
| `LOG_FILENAME` | `LOG_FILENAME` | `mgit.log` | Where to save your high scores... err, logs | No |
| `LOG_LEVEL` | `LOG_LEVEL` | `DEBUG` | File log verbosity: `DEBUG`/`INFO`/`WARNING`/`ERROR` | No |
| `CON_LEVEL` | `CON_LEVEL` | `INFO` | Console output level (your CRT monitor display) | No |
| **🔷 Azure DevOps** |||||
| `AZURE_DEVOPS_ORG_URL` | `AZURE_DEVOPS_ORG_URL` | - | Your Azure DevOps org URL | Yes* |
| `AZURE_DEVOPS_EXT_PAT` | `AZURE_DEVOPS_EXT_PAT` | - | Personal Access Token (your secret code!) | Yes* |
| `AZURE_DEVOPS_USERNAME` | `AZURE_DEVOPS_USERNAME` | - | Username (optional player name) | No |
| **🐙 GitHub** |||||
| `GITHUB_PAT` | `GITHUB_PAT` | - | GitHub Personal Access Token | Yes* |
| `GITHUB_ORG` | `GITHUB_ORG` | - | Default organization to clone from | No |
| `GITHUB_ENTERPRISE_URL` | `GITHUB_ENTERPRISE_URL` | - | GitHub Enterprise URL (for corporate arcade) | No |
| `GITHUB_USERNAME` | `GITHUB_USERNAME` | - | Your GitHub username | No |
| **🪣 BitBucket** |||||
| `BITBUCKET_WORKSPACE` | `BITBUCKET_WORKSPACE` | - | BitBucket workspace name | Yes* |
| `BITBUCKET_USERNAME` | `BITBUCKET_USERNAME` | - | BitBucket username | Yes* |
| `BITBUCKET_APP_PASSWORD` | `BITBUCKET_APP_PASSWORD` | - | BitBucket app password | Yes* |
| `BITBUCKET_SERVER_URL` | `BITBUCKET_SERVER_URL` | - | BitBucket Server URL (self-hosted) | No |

*Required only when using that specific provider

### 💿 Example Configurations

#### Environment Variables (Bash/Zsh)
```bash
# 🎯 Azure DevOps Setup
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/radical-corp"
export AZURE_DEVOPS_EXT_PAT="your-gnarly-token-here"

# 🐙 GitHub Setup  
export GITHUB_PAT="ghp_totallyTubularToken1234567890"
export GITHUB_ORG="awesome-sauce-inc"

# 🎮 Performance Tuning
export DEFAULT_CONCURRENCY="10"  # TURBO MODE!
export DEFAULT_UPDATE_MODE="pull"
```

#### Config File (~/.config/mgit/config)
```ini
# ╔════════════════════════════════════╗
# ║   mgit Configuration File v0.2.1   ║
# ║   「 RADICAL CONFIG 」              ║
# ╚════════════════════════════════════╝

# Global Settings - Crank it to 11!
DEFAULT_CONCURRENCY=8
DEFAULT_UPDATE_MODE=pull
LOG_LEVEL=INFO
CON_LEVEL=INFO

# Azure DevOps - The Corporate Arcade
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/bigcorp
AZURE_DEVOPS_EXT_PAT=secret-token-dont-share

# GitHub - Where the Cool Kids Hang
GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_ORG=rad-startup

# BitBucket - The Underground Scene
BITBUCKET_WORKSPACE=elite-hackers
BITBUCKET_USERNAME=zerocool
BITBUCKET_APP_PASSWORD=hack-the-planet
```

### 🎯 Pro Tips

1. **Mix & Match**: Use env vars for secrets, config file for defaults
2. **Override on the Fly**: `DEFAULT_CONCURRENCY=20 mgit clone-all ...`
3. **Check Your Config**: `mgit config --show` displays the final merged config
4. **Provider Auto-Detection**: mgit is smart enough to figure out which provider you're using from URLs!

### 🔐 Security Best Practices

- 🚫 Never commit tokens to version control (that's a Game Over, man!)
- 🔒 Config file is created with 0600 permissions (owner-only access)
- 🎭 All tokens are masked in logs and console output
- 💾 Use environment variables in CI/CD for maximum security

## Practical Examples

### Managing Multiple Provider Repositories

```bash
# Clone all repos from different providers into organized folders
mgit clone-all my-azure-project ./work/azure --provider azuredevops
mgit clone-all my-github-org ./work/github --provider github
mgit clone-all my-bb-workspace ./work/bitbucket --provider bitbucket

# Update all repositories across providers
cd ./work/azure && mgit pull-all my-azure-project .
cd ./work/github && mgit pull-all my-github-org .
cd ./work/bitbucket && mgit pull-all my-bb-workspace .
```

### Provider Auto-Detection

```bash
# mgit automatically detects the provider from the URL
mgit clone-all tensorflow ./ml-repos https://github.com
mgit clone-all my-project ./work https://dev.azure.com/company
mgit clone-all atlassian ./tools https://bitbucket.org
```

### Mixed Provider Workflows

```bash
# Set up authentication for all providers
mgit login --provider azuredevops --store
mgit login --provider github --store
mgit login --provider bitbucket --store

# Clone from multiple providers in one session
mgit clone-all frontend-team ./repos/frontend https://dev.azure.com/company
mgit clone-all backend-libs ./repos/backend https://github.com
mgit clone-all devops-tools ./repos/ops https://bitbucket.org
```

### Docker Workflows

```bash
# Create an alias for convenience
alias mgit-docker='docker run --rm -v $(pwd):/workspace -v ~/.config/mgit:/root/.config/mgit ghcr.io/aeyeops/mgit:latest'

# Use mgit with Docker like normal
mgit-docker login --provider github --store
mgit-docker clone-all my-org /workspace/repos
mgit-docker pull-all my-org /workspace/repos
```

## Security

The tool handles sensitive information securely:
- All tokens (PATs, app passwords) are masked in logs and console output
- Configuration files have secure permissions (0600)
- Credentials can be stored securely or used only for the current session
- Provider-specific authentication methods:
  - **Azure DevOps**: Personal Access Tokens (PAT)
  - **GitHub**: Personal Access Tokens or GitHub Apps
  - **BitBucket**: App Passwords (more secure than regular passwords)

## For Developers

For technical implementation details, see the [documentation](docs/) directory and [CLAUDE.md](CLAUDE.md) for codebase guidance.

### Provider Implementation Status

| Provider | Status | Implementation Details |
|----------|--------|----------------------|
| Azure DevOps | ✅ Complete | Full API integration using azure-devops SDK |
| GitHub | ✅ Complete | REST API v3 with PyGithub library |
| BitBucket | ✅ Complete | REST API v2.0 with atlassian-python-api |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
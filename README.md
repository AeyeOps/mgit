# mgit - Multi-Provider Git CLI Tool 🚀

[![PyPI version](https://img.shields.io/pypi/v/mgit.svg)](https://pypi.org/project/mgit/)
[![Install from GitHub](https://img.shields.io/badge/pip%20install-GitHub%20Release-brightgreen)](https://github.com/steveant/mgit/releases/latest)
[![Docker Image](https://img.shields.io/docker/v/steveant/mgit?label=docker)](https://ghcr.io/steveant/mgit)
[![GitHub Release](https://img.shields.io/github/release/steveant/mgit.svg)](https://github.com/steveant/mgit/releases/latest)
[![Enterprise Certified](https://img.shields.io/badge/Enterprise-Certified-gold)](ENTERPRISE_CERTIFICATION_SUMMARY.md)
[![Security](https://img.shields.io/badge/Security-AES--256-green)](docs/security)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](Dockerfile)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-Automated-success)](.github/workflows)

A powerful **enterprise-grade** command-line tool for managing repositories across multiple git platforms. Clone entire projects, update multiple repositories, and automate your git workflows with support for:

✅ **Azure DevOps** - Full feature support with organizations and projects  
✅ **GitHub** - Complete integration for organizations and users  
✅ **BitBucket** - Full workspace and repository management  

**All providers have feature parity** - login, clone-all, pull-all, and configuration work identically across platforms.

🏆 **ENTERPRISE CERTIFIED** - ID: MGIT-ENT-2025-001 | Ready for production deployment with comprehensive security, monitoring, and automation.

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

### 🚀 Quick Install - Works NOW!

```bash
# Install mgit directly from GitHub Release (Available NOW!)
pip install https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-0.2.1-py3-none-any.whl

# Verify installation
mgit --version
```

### Prerequisites

- Python 3.7 or higher (for pip/source installation)
- Git
- Docker (for Docker installation method)

### Installation Methods

#### Method 1: Install from GitHub Release (Available NOW!)

```bash
# Install directly from GitHub - THIS WORKS RIGHT NOW!
pip install https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-0.2.1-py3-none-any.whl

# Run mgit directly
mgit --version
```

#### Method 2: Install from PyPI (Coming Soon)

```bash
# Will be available after PyPI approval
pip install mgit
```

#### Method 3: Download Binary from GitHub Releases

Download the pre-built binary for your platform:

1. Visit [mgit releases](https://github.com/steveant/mgit/releases/tag/v0.2.1)
2. Download the appropriate binary for your OS:
   - `mgit-v0.2.1-linux-x64` for Linux
   - `mgit-v0.2.1-macos-x64` for macOS
   - `mgit-v0.2.1-windows-x64.exe` for Windows
3. Make it executable (Linux/macOS):
   ```bash
   chmod +x mgit-v0.2.1-linux-x64
   ./mgit-v0.2.1-linux-x64 --version
   ```

#### Method 4: Use Docker

```bash
# Pull the latest image
docker pull ghcr.io/steveant/mgit:latest

# Run mgit in Docker
docker run --rm ghcr.io/steveant/mgit:latest --version

# With volume mount for local repo access
docker run --rm -v $(pwd):/workspace ghcr.io/steveant/mgit:latest clone-all my-project /workspace/repos
```

#### Method 5: Install from Source

1. Clone this repository:
   ```bash
   git clone https://github.com/steveant/mgit.git
   cd mgit
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e .  # Development installation
   ```

3. Run the tool:
   ```bash
   python -m mgit --version
   ```

### Installation Method Comparison

| Method | Prerequisites | Pros | Cons | Best For | Available Now? |
|--------|--------------|------|------|---------|----------------|
| **GitHub pip** | Python 3.7+, pip | • Works NOW!<br>• Easy install<br>• Automatic dependencies | • Manual version specification | Anyone needing pip install TODAY | ✅ YES |
| **PyPI** | Python 3.7+, pip | • Easy updates<br>• Standard Python workflow<br>• Automatic dependencies | • Requires Python environment | Regular users, Python developers | ❌ Coming Soon |
| **GitHub Binary** | None | • No dependencies<br>• Fast startup<br>• Single file | • Manual updates<br>• Platform-specific | CI/CD, users without Python | ✅ YES |
| **Docker** | Docker | • Fully isolated<br>• Consistent environment<br>• No local dependencies | • Requires Docker<br>• Slightly slower startup | Containers, isolated environments | ✅ YES |
| **Source** | Python 3.7+, Git | • Latest features<br>• Can modify code<br>• Development mode | • Manual updates<br>• Requires Git | Contributors, developers | ✅ YES |

For detailed installation instructions and troubleshooting, see [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md).

### 🎯 Working Installation Methods Summary

**All of these methods are available and working RIGHT NOW:**

1. **pip from GitHub** (Recommended for Python users):
   ```bash
   pip install https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-0.2.1-py3-none-any.whl
   ```

2. **Binary Download** (No Python required):
   - [Linux](https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-v0.2.1-linux-x64)
   - [macOS](https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-v0.2.1-macos-x64)
   - [Windows](https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-v0.2.1-windows-x64.exe)

3. **Docker** (Fully isolated):
   ```bash
   docker pull ghcr.io/steveant/mgit:latest
   ```

4. **From Source** (For developers):
   ```bash
   git clone https://github.com/steveant/mgit.git && cd mgit
   pip install -r requirements.txt && pip install -e .
   ```

See [WORKING_INSTALLATION_METHODS.md](WORKING_INSTALLATION_METHODS.md) for quick installation instructions.

## Quick Start

### Basic Operations

Get the current version:
```bash
# If installed via pip
mgit --version

# If using Docker
docker run --rm ghcr.io/steveant/mgit:latest --version

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
docker run --rm -v ~/.config/mgit:/root/.config/mgit ghcr.io/steveant/mgit:latest login --provider azuredevops --store
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
docker run --rm -v $(pwd):/workspace ghcr.io/steveant/mgit:latest clone-all my-org /workspace/repos https://github.com
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
  ghcr.io/steveant/mgit:latest \
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
docker run --rm -v $(pwd):/workspace ghcr.io/steveant/mgit:latest pull-all my-project /workspace/repos
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
docker run --rm ghcr.io/steveant/mgit:latest
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

## Configuration

The tool uses a hierarchical configuration system:

1. **Environment variables** (highest priority)
2. **Global config** in `~/.config/mgit/config` (second priority)
3. **Default values** in code (lowest priority)

### Provider-Specific Configuration

#### Azure DevOps
- `AZURE_DEVOPS_ORG_URL`: Organization URL (e.g., https://dev.azure.com/myorg)
- `AZURE_DEVOPS_EXT_PAT`: Personal Access Token
- `AZUREDEVOPS_USERNAME`: Username (optional)

#### GitHub
- `GITHUB_PAT`: Personal Access Token
- `GITHUB_ORG`: Default organization (optional)
- `GITHUB_ENTERPRISE_URL`: GitHub Enterprise URL (optional)
- `GITHUB_USERNAME`: Username (optional)

#### BitBucket
- `BITBUCKET_WORKSPACE`: Default workspace
- `BITBUCKET_USERNAME`: Username (required)
- `BITBUCKET_APP_PASSWORD`: App Password
- `BITBUCKET_SERVER_URL`: BitBucket Server URL (optional)

### Global Settings
- `DEFAULT_CONCURRENCY`: Number of concurrent operations (default: 4)
- `DEFAULT_UPDATE_MODE`: Default update mode (skip, pull, force)

### Example Configuration File

```bash
# ~/.config/mgit/config

# Global settings
DEFAULT_CONCURRENCY=8
DEFAULT_UPDATE_MODE=pull

# Azure DevOps
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/mycompany
AZURE_DEVOPS_EXT_PAT=mytoken123

# GitHub
GITHUB_PAT=ghp_xxxxxxxxxxxx
GITHUB_ORG=my-github-org

# BitBucket  
BITBUCKET_WORKSPACE=myworkspace
BITBUCKET_USERNAME=myusername
BITBUCKET_APP_PASSWORD=myapppassword
```

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
alias mgit-docker='docker run --rm -v $(pwd):/workspace -v ~/.config/mgit:/root/.config/mgit ghcr.io/steveant/mgit:latest'

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

For technical implementation details, architecture diagrams, and future improvement plans, please see [ARCHITECTURE.md](ARCHITECTURE.md).

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
# Azure DevOps CLI Tool

A powerful command-line tool for managing Azure DevOps repositories with ease. Clone entire projects, update multiple repositories, and automate your DevOps workflows.

## Overview

The Azure DevOps CLI Tool simplifies common repository management tasks by providing an intuitive command-line interface. It was created to solve the challenge of managing multiple repositories across Azure DevOps projects, allowing developers and DevOps engineers to:

- Clone all repositories from a project with a single command
- Pull updates for multiple repositories simultaneously
- Configure global settings for repeated operations
- Manage authentication credentials securely
- Automatically handle disabled repositories with clear reporting

Built with Python, it leverages asynchronous operations for speed and provides rich console output for better visibility.

## Installation

### Prerequisites

- Python 3.7 or higher
- Azure CLI with azure-devops extension (will be installed automatically if missing)
- Git

### Installation Steps

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/ado-git.git
   cd ado-git
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the tool:
   ```bash
   python ado-cli.py
   ```

### Building a Standalone Executable

For convenience, you can build a standalone executable that can be distributed without requiring Python:

```bash
# Install PyInstaller
pip install pyinstaller

# Create a single executable file
pyinstaller --onefile ado-cli.py
```

The executable will be created in the `dist/` directory and can be run directly:

```bash
./dist/ado-cli
```

## Quick Start

### Authentication

First, authenticate with Azure DevOps:

```bash
# Interactive login with prompts
python ado-cli.py login

# Or specify credentials directly
python ado-cli.py login --org https://dev.azure.com/your-org --pat your-pat
```

### Clone All Repositories

Clone all repositories from a project:

```bash
python ado-cli.py clone-all my-project ./repos
```

With custom options:

```bash
# Clone with 8 concurrent operations and force mode (overwrite existing repos)
python ado-cli.py clone-all my-project ./repos -c 8 -u force
```

### Update All Repositories

Pull the latest changes for all repositories:

```bash
python ado-cli.py pull-all my-project ./repos
```

### Global Configuration

View or set global configuration:

```bash
# Show current settings
python ado-cli.py config --show

# Set default values
python ado-cli.py config --org https://dev.azure.com/your-org --concurrency 16 --update-mode pull
```

## Commands Reference

Run without arguments to see available commands:

```bash
python ado-cli.py
```

### login

Authenticate with Azure DevOps using a Personal Access Token (PAT).

```bash
python ado-cli.py login [--org URL] [--pat TOKEN] [--no-store]
```

### clone-all

Clone all repositories from an Azure DevOps project.

```bash
python ado-cli.py clone-all PROJECT DESTINATION [--concurrency N] [--update-mode MODE]
```

Update modes:
- `skip`: Skip existing directories (default)
- `pull`: Try to git pull if it's a valid repository 
- `force`: Remove existing directories and clone fresh

### pull-all

Pull updates for all repositories in a directory.

```bash
python ado-cli.py pull-all PROJECT REPOSITORY_PATH
```

### config

View or set global configuration settings.

```bash
python ado-cli.py config [--show] [--org URL] [--concurrency N] [--update-mode MODE]
```

### generate-env

Generate a sample environment file with configuration options.

```bash
python ado-cli.py generate-env
```

## Configuration

The tool uses a hierarchical configuration system:

1. **Environment variables** (highest priority)
2. **Global config** in `~/.config/ado-cli/config` (second priority)
3. **Default values** in code (lowest priority)

Key configuration options:

- `AZURE_DEVOPS_ORG_URL`: Azure DevOps organization URL
- `AZURE_DEVOPS_EXT_PAT`: Personal Access Token
- `DEFAULT_CONCURRENCY`: Number of concurrent operations (default: 4)
- `DEFAULT_UPDATE_MODE`: Default update mode (skip, pull, force)

## Security

The tool handles sensitive information securely:
- PAT tokens are masked in logs and console output
- Configuration files have secure permissions (0600)
- Credentials can be stored securely or used only for the current session

## For Developers

For technical implementation details, architecture diagrams, and future improvement plans, please see [ARCHITECTURE.md](ARCHITECTURE.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
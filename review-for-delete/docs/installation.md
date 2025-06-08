# Installation Guide

This guide covers all installation methods for mgit.

## System Requirements

- **Python**: 3.9 or higher (if using pip installation)
- **Git**: 2.25 or higher
- **Operating Systems**: Linux, macOS, Windows
- **Memory**: 256MB minimum
- **Disk Space**: 50MB for binary, 100MB for Python installation

## Installation Methods

### Method 1: pip Installation (Recommended)

The simplest way to install mgit if you have Python:

```bash
# Install from latest release
pip install https://github.com/AeyeOps/mgit/releases/download/v0.2.3/mgit-0.2.3-py3-none-any.whl

# Verify installation
mgit --version
```

To upgrade:
```bash
pip install --upgrade https://github.com/AeyeOps/mgit/releases/download/v0.2.3/mgit-0.2.3-py3-none-any.whl
```

### Method 2: Standalone Binary

No Python required. Download pre-built executables:

#### Linux
```bash
wget https://github.com/AeyeOps/mgit/releases/latest/download/mgit-linux-x64
chmod +x mgit-linux-x64
sudo mv mgit-linux-x64 /usr/local/bin/mgit
```

#### macOS
```bash
curl -L https://github.com/AeyeOps/mgit/releases/latest/download/mgit-macos-x64 -o mgit
chmod +x mgit
sudo mv mgit /usr/local/bin/mgit
```

#### Windows
1. Download `mgit-windows-x64.exe` from [releases page](https://github.com/AeyeOps/mgit/releases/latest)
2. Rename to `mgit.exe`
3. Add to PATH or move to a directory in PATH

### Method 3: Docker

Run mgit in a container:

```bash
# Pull latest image
docker pull ghcr.io/aeyeops/mgit:latest

# Run mgit
docker run --rm ghcr.io/aeyeops/mgit:latest --version

# Create alias for convenience
alias mgit='docker run --rm -v $(pwd):/workspace -v ~/.config/mgit:/root/.config/mgit ghcr.io/aeyeops/mgit:latest'
```

### Method 4: From Source

For development or latest features:

```bash
# Clone repository
git clone https://github.com/AeyeOps/mgit.git
cd mgit

# Install with Poetry
poetry install --with dev

# Run mgit
poetry run mgit --version

# Or install globally
poetry build
pip install dist/*.whl
```

## Post-Installation

### Verify Installation

```bash
# Check version
mgit --version

# View help
mgit --help

# Check Python and Git versions (if relevant)
python --version
git --version
```

### Initial Configuration

Create the configuration directory:

```bash
# Linux/macOS
mkdir -p ~/.config/mgit

# Windows
mkdir %APPDATA%\mgit
```

### Shell Completion (Optional)

For bash completion:
```bash
mgit --install-completion bash
source ~/.bashrc
```

For zsh completion:
```bash
mgit --install-completion zsh
source ~/.zshrc
```

## Troubleshooting

### Common Issues

**Command not found**
- Ensure mgit is in your PATH
- Try using the full path to the executable

**Permission denied**
- Use `chmod +x` on Linux/macOS binaries
- Run with appropriate permissions

**SSL/TLS errors**
- Update certificates: `pip install --upgrade certifi`
- For corporate proxies, see proxy configuration below

### Proxy Configuration

For corporate environments:

```bash
# Set proxy environment variables
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1

# For Git operations
git config --global http.proxy http://proxy.company.com:8080
```

## Uninstallation

### pip Installation
```bash
pip uninstall mgit
```

### Binary Installation
```bash
# Linux/macOS
sudo rm /usr/local/bin/mgit

# Windows - remove mgit.exe from installation directory
```

### Docker
```bash
docker rmi ghcr.io/aeyeops/mgit:latest
```

## Next Steps

- [Configure your first provider](providers/README.md)
- [Read the user guide](usage/guide.md)
- [View command reference](reference/commands.md)
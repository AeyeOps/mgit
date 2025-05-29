# mgit Installation Guide

This guide provides comprehensive installation instructions for mgit across different platforms and installation methods.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [PyPI Installation](#pypi-installation)
  - [GitHub Binary Installation](#github-binary-installation)
  - [Docker Installation](#docker-installation)
  - [Source Installation](#source-installation)
- [Platform-Specific Notes](#platform-specific-notes)
- [Post-Installation Setup](#post-installation-setup)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)

## Prerequisites

### Basic Requirements

- **Git**: Required for all installation methods (for cloning repositories)
- **Internet connection**: For downloading packages and accessing git providers

### Method-Specific Requirements

| Method | Requirements |
|--------|-------------|
| PyPI | Python 3.7+, pip |
| GitHub Binary | None (standalone executable) |
| Docker | Docker Engine 20.10+ |
| Source | Python 3.7+, pip, git |

## Installation Methods

### PyPI Installation

The recommended method for most users. Provides easy updates and integrates with Python environments.

#### Standard Installation

```bash
# Install the latest stable version
pip install mgit

# Verify installation
mgit --version
```

#### Virtual Environment Installation (Recommended)

```bash
# Create a virtual environment
python -m venv mgit-env

# Activate the environment
# On Linux/macOS:
source mgit-env/bin/activate
# On Windows:
mgit-env\Scripts\activate

# Install mgit
pip install mgit

# Verify installation
mgit --version
```

#### User Installation (No sudo required)

```bash
# Install for current user only
pip install --user mgit

# Add user bin to PATH if needed
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
mgit --version
```

#### Upgrading

```bash
# Upgrade to the latest version
pip install --upgrade mgit
```

### GitHub Binary Installation

Pre-built standalone executables that require no dependencies.

#### Latest Release (v0.2.1)

1. **Download the binary**:
   
   Visit: https://github.com/steveant/mgit/releases/tag/v0.2.1
   
   Or use command line:
   ```bash
   # Linux
   wget https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-v0.2.1-linux-x64
   
   # macOS
   curl -L https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-v0.2.1-macos-x64 -o mgit
   
   # Windows (PowerShell)
   Invoke-WebRequest -Uri https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-v0.2.1-windows-x64.exe -OutFile mgit.exe
   ```

2. **Make executable** (Linux/macOS):
   ```bash
   chmod +x mgit-v0.2.1-linux-x64
   ```

3. **Move to PATH** (optional):
   ```bash
   # Linux/macOS
   sudo mv mgit-v0.2.1-linux-x64 /usr/local/bin/mgit
   
   # Windows: Add to PATH through System Properties
   ```

4. **Verify installation**:
   ```bash
   mgit --version
   ```

### Docker Installation

Ideal for isolated environments and consistent behavior across platforms.

#### Pull the Image

```bash
# Pull the latest stable version
docker pull ghcr.io/steveant/mgit:latest

# Or pull a specific version
docker pull ghcr.io/steveant/mgit:v0.2.1
```

#### Create an Alias (Recommended)

```bash
# Add to ~/.bashrc or ~/.zshrc
alias mgit='docker run --rm -v $(pwd):/workspace -v ~/.config/mgit:/root/.config/mgit ghcr.io/steveant/mgit:latest'

# Reload shell configuration
source ~/.bashrc  # or ~/.zshrc
```

#### Direct Usage

```bash
# Run mgit commands
docker run --rm ghcr.io/steveant/mgit:latest --version

# With volume mounts for file access
docker run --rm \
  -v $(pwd):/workspace \
  -v ~/.config/mgit:/root/.config/mgit \
  ghcr.io/steveant/mgit:latest \
  clone-all my-org /workspace/repos
```

#### Docker Compose Setup

Create a `docker-compose.yml`:

```yaml
version: '3.8'
services:
  mgit:
    image: ghcr.io/steveant/mgit:latest
    volumes:
      - .:/workspace
      - ~/.config/mgit:/root/.config/mgit
    working_dir: /workspace
```

Usage:
```bash
docker-compose run --rm mgit --version
docker-compose run --rm mgit clone-all my-org ./repos
```

### Source Installation

For developers and contributors who want the latest features or need to modify the code.

#### Clone and Install

```bash
# Clone the repository
git clone https://github.com/steveant/mgit.git
cd mgit

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Verify installation
python -m mgit --version
```

#### Building from Source

```bash
# Install build dependencies
pip install build

# Build the package
python -m build

# Install the built package
pip install dist/mgit-*.whl

# Verify installation
mgit --version
```

#### Creating Standalone Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile mgit/__main__.py

# The executable will be in dist/
./dist/__main__ --version

# Optionally rename it
mv dist/__main__ dist/mgit
```

## Platform-Specific Notes

### Windows

1. **Path Considerations**:
   - Use forward slashes in paths: `C:/Users/name/repos`
   - Or escape backslashes: `C:\\Users\\name\\repos`
   - Or use raw strings in scripts: `r"C:\Users\name\repos"`

2. **Git Line Endings**:
   ```bash
   # Configure Git for Windows line endings
   git config --global core.autocrlf true
   ```

3. **Long Path Support**:
   ```bash
   # Enable long path support (requires Admin)
   git config --global core.longpaths true
   ```

### macOS

1. **Command Line Tools**:
   ```bash
   # Install if not present
   xcode-select --install
   ```

2. **Homebrew Python** (if using):
   ```bash
   # Use python3 and pip3
   pip3 install mgit
   ```

3. **Security Permissions**:
   - First run may require security approval
   - Go to System Preferences → Security & Privacy → General
   - Click "Allow Anyway" for mgit

### Linux

1. **Python Version**:
   ```bash
   # Check Python version
   python3 --version
   
   # Use python3 if python points to 2.x
   python3 -m pip install mgit
   ```

2. **Package Manager Installation**:
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3-pip git
   
   # Fedora
   sudo dnf install python3-pip git
   
   # Arch
   sudo pacman -S python-pip git
   ```

## Post-Installation Setup

### 1. Verify Installation

```bash
# Check version
mgit --version

# View help
mgit --help

# Check available commands
mgit
```

### 2. Configure Authentication

```bash
# Set up provider credentials
mgit login --provider github --store
mgit login --provider azuredevops --store
mgit login --provider bitbucket --store
```

### 3. Set Default Configuration

```bash
# View current configuration
mgit config --show

# Set defaults
mgit config --concurrency 8 --update-mode pull
```

### 4. Generate Environment Template

```bash
# Create .env.sample file
mgit generate-env
```

## Troubleshooting

### Common Issues

#### 1. Command Not Found

**Problem**: `mgit: command not found`

**Solutions**:
```bash
# Check if mgit is in PATH
which mgit

# For pip installation, ensure pip bin is in PATH
export PATH="$HOME/.local/bin:$PATH"

# For system pip
export PATH="/usr/local/bin:$PATH"
```

#### 2. Permission Denied

**Problem**: Permission errors during installation

**Solutions**:
```bash
# Use user installation
pip install --user mgit

# Or use virtual environment
python -m venv mgit-env
source mgit-env/bin/activate
pip install mgit
```

#### 3. SSL Certificate Errors

**Problem**: SSL verification failures

**Solutions**:
```bash
# Update certificates
pip install --upgrade certifi

# For corporate networks (not recommended for production)
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org mgit
```

#### 4. Docker Permission Issues

**Problem**: Docker requires sudo

**Solutions**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker run hello-world
```

#### 5. Python Version Conflicts

**Problem**: Wrong Python version

**Solutions**:
```bash
# Use specific Python version
python3.9 -m pip install mgit

# Or use pyenv for version management
pyenv install 3.9.0
pyenv local 3.9.0
pip install mgit
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Set debug environment variable
export MGIT_DEBUG=1

# Run command with debug output
mgit clone-all my-org ./repos
```

## Uninstallation

### GitHub pip / PyPI Installation

```bash
# Uninstall mgit
pip uninstall mgit

# Remove configuration (optional)
rm -rf ~/.config/mgit
```

### Binary Installation

```bash
# Remove the binary
sudo rm /usr/local/bin/mgit

# Remove configuration (optional)
rm -rf ~/.config/mgit
```

### Docker Installation

```bash
# Remove the image
docker rmi ghcr.io/steveant/mgit:latest

# Remove all mgit images
docker rmi $(docker images | grep mgit | awk '{print $3}')

# Remove configuration (optional)
rm -rf ~/.config/mgit
```

### Source Installation

```bash
# If installed with pip -e
pip uninstall mgit

# Remove the cloned directory
rm -rf /path/to/mgit

# Remove configuration (optional)
rm -rf ~/.config/mgit
```

## Getting Help

1. **Documentation**: See the [README](README.md) for usage instructions
2. **Issues**: Report bugs at https://github.com/steveant/mgit/issues
3. **Discussions**: Ask questions at https://github.com/steveant/mgit/discussions

## Next Steps

After installation:
1. Read the [Quick Start](README.md#quick-start) guide
2. Set up [authentication](README.md#authentication) for your providers
3. Try [cloning repositories](README.md#clone-all-repositories)
4. Explore [provider-specific guides](docs/providers/) for your git platform
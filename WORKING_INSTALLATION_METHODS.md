# Working Installation Methods for mgit

This document lists ONLY the installation methods that are **available and working RIGHT NOW**.

## ✅ Method 1: pip Install from GitHub Release

**Status: WORKING NOW!**

```bash
# Install mgit directly from GitHub release
pip install https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-0.2.1-py3-none-any.whl

# Verify installation
mgit --version
```

### Additional Options:

**Virtual Environment (Recommended):**
```bash
python -m venv mgit-env
source mgit-env/bin/activate  # On Windows: mgit-env\Scripts\activate
pip install https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-0.2.1-py3-none-any.whl
```

**User Installation (No sudo):**
```bash
pip install --user https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-0.2.1-py3-none-any.whl
export PATH="$HOME/.local/bin:$PATH"  # Add to your shell profile
```

## ✅ Method 2: Download Binary from GitHub

**Status: WORKING NOW!**

### Linux
```bash
wget https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-v0.2.1-linux-x64
chmod +x mgit-v0.2.1-linux-x64
./mgit-v0.2.1-linux-x64 --version
```

### macOS
```bash
curl -L https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-v0.2.1-macos-x64 -o mgit
chmod +x mgit
./mgit --version
```

### Windows
```powershell
Invoke-WebRequest -Uri https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-v0.2.1-windows-x64.exe -OutFile mgit.exe
.\mgit.exe --version
```

## ✅ Method 3: Docker

**Status: WORKING NOW!**

```bash
# Pull and run
docker pull ghcr.io/steveant/mgit:latest
docker run --rm ghcr.io/steveant/mgit:latest --version

# Create an alias for convenience
alias mgit='docker run --rm -v $(pwd):/workspace -v ~/.config/mgit:/root/.config/mgit ghcr.io/steveant/mgit:latest'
```

## ✅ Method 4: Install from Source

**Status: WORKING NOW!**

```bash
# Clone and install
git clone https://github.com/steveant/mgit.git
cd mgit
pip install -r requirements.txt
pip install -e .

# Run directly
python -m mgit --version
```

## Quick Decision Guide

| Your Situation | Best Method |
|----------------|-------------|
| Have Python, want pip install | **Method 1: pip from GitHub** |
| No Python, want simple binary | **Method 2: GitHub Binary** |
| Using containers/K8s | **Method 3: Docker** |
| Want to modify code | **Method 4: Source** |

## Requirements Summary

- **Methods 1 & 4**: Python 3.7+ and pip
- **Method 2**: No requirements (standalone binary)
- **Method 3**: Docker Engine 20.10+
- **All methods**: Git (for cloning repositories)

## Need Help?

- See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for detailed instructions
- Report issues at https://github.com/steveant/mgit/issues
- Check [README.md](README.md) for usage examples
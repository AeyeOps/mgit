# Installing mgit from GitHub

## Direct Installation from GitHub

Since PyPI credentials are not available, you can install mgit directly from GitHub:

### Install Latest Release
```bash
pip install https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-0.2.1-py3-none-any.whl
```

### Install from Source (Latest Main Branch)
```bash
pip install git+https://github.com/steveant/mgit.git
```

### Install Specific Version from Source
```bash
pip install git+https://github.com/steveant/mgit.git@v0.2.1
```

### Install in Development Mode
```bash
git clone https://github.com/steveant/mgit.git
cd mgit
pip install -e .
```

## Docker Installation

Docker images are published to GitHub Container Registry:

```bash
# Pull latest image
docker pull ghcr.io/steveant/mgit:latest

# Run mgit in Docker
docker run --rm ghcr.io/steveant/mgit:latest --help

# Run with local directory mounted
docker run --rm -v $(pwd):/workspace ghcr.io/steveant/mgit:latest config --show
```

## Verification

After installation, verify mgit is working:

```bash
mgit --version
mgit --help
```

## Requirements

- Python 3.8 or higher
- Git installed on your system
- For Docker: Docker Engine installed

## Troubleshooting

If you encounter issues:

1. Ensure you have the latest pip:
   ```bash
   pip install --upgrade pip
   ```

2. Install in a virtual environment:
   ```bash
   python -m venv mgit-env
   source mgit-env/bin/activate  # On Windows: mgit-env\Scripts\activate
   pip install https://github.com/steveant/mgit/releases/download/v0.2.1/mgit-0.2.1-py3-none-any.whl
   ```

3. Check GitHub Release page for all available versions:
   https://github.com/steveant/mgit/releases
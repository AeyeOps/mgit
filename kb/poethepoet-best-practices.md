# Poethepoet (Poe) Best Practices Guide

## Table of Contents
1. [Introduction](#introduction)
2. [TOML Syntax Basics](#toml-syntax-basics)
3. [Task Types](#task-types)
4. [Conditional Logic and Error Handling](#conditional-logic-and-error-handling)
5. [Environment Variables and Dependencies](#environment-variables-and-dependencies)
6. [File Operations and Permissions](#file-operations-and-permissions)
7. [PyInstaller Integration](#pyinstaller-integration)
8. [Best Practices for Complex Build Tasks](#best-practices-for-complex-build-tasks)
9. [Real-World Examples](#real-world-examples)

## Introduction

Poethepoet (poe) is a task runner that integrates seamlessly with Poetry and UV package managers. It allows you to define and run tasks directly from your `pyproject.toml` file, making it ideal for build automation, testing, and deployment workflows.

### Installation

```bash
# With pip
pip install poethepoet

# With poetry
poetry add --group dev poethepoet

# As a poetry plugin (recommended)
poetry self add 'poethepoet[poetry_plugin]'
```

## TOML Syntax Basics

### Basic Task Definition

Tasks are defined under the `[tool.poe.tasks]` section in `pyproject.toml`:

```toml
[tool.poe.tasks]
# Simple command task (string format)
test = "pytest"

# Command with arguments
test-cov = "pytest --cov=mgit --cov-report=term"

# Task with help text
test-quick.help = "Run tests excluding slow tests"
test-quick.cmd = "pytest -m 'not slow'"
```

### Alternative TOML Syntaxes

```toml
# Table format (most explicit)
[tool.poe.tasks.build]
help = "Build the project"
cmd = "python -m build"

# Inline table format
[tool.poe.tasks]
build = { cmd = "python -m build", help = "Build the project" }

# Deep key format
[tool.poe.tasks]
build.cmd = "python -m build"
build.help = "Build the project"
```

## Task Types

### 1. Command Tasks (`cmd`)

Execute a single command without a shell:

```toml
[tool.poe.tasks]
# Simple command
format = "black ."

# Command with complex arguments
build-exe = """
pyinstaller --onefile \
    --name mgit \
    --add-data "README.md:." \
    --hidden-import mgit.providers \
    mgit/__main__.py
"""

# Using table format for clarity
[tool.poe.tasks.lint]
cmd = "ruff check mgit tests"
help = "Run linting checks"
```

### 2. Shell Tasks (`shell`)

Execute commands through a shell (bash/cmd):

```toml
[tool.poe.tasks]
# Simple shell command
clean = { shell = "rm -rf dist build *.egg-info" }

# Multi-line shell script
[tool.poe.tasks.install-local]
shell = """
pip install -e . && \
echo "Installation complete" && \
mgit --version
"""
interpreter = "bash"  # Specify shell (default: sh on Unix, cmd on Windows)
```

### 3. Script Tasks (`script`)

Call Python functions directly:

```toml
[tool.poe.tasks]
# Call a function from a module
validate = { script = "mgit.utils:validate_config" }

# Pass arguments to the function
build-release = { script = "build_tools:create_release(version='${VERSION}')" }

# Script with environment variables
[tool.poe.tasks.deploy]
script = "deployment:deploy_to_server"
env = { SERVER = "production", PORT = "8080" }
```

### 4. Sequence Tasks (`sequence`)

Run multiple tasks in order:

```toml
[tool.poe.tasks]
# Simple sequence using task references
release = ["test", "build", "publish"]

# Sequence with inline tasks
[tool.poe.tasks.full-check]
sequence = [
    { cmd = "ruff check ." },
    { cmd = "black --check ." },
    { cmd = "mypy mgit" },
    "test",  # Reference to existing task
]

# Sequence with error handling
[tool.poe.tasks.ci]
sequence = ["lint", "type-check", "test", "build"]
ignore_fail = false  # Stop on first failure (default)

# Continue on failure
[tool.poe.tasks.check-all]
sequence = ["lint", "format-check", "test"]
ignore_fail = true  # Continue even if a task fails

# Continue but return non-zero if any failed
[tool.poe.tasks.validate-all]
sequence = ["security-check", "dependency-check", "test"]
ignore_fail = "return_non_zero"
```

### 5. Expression Tasks (`expr`)

Evaluate Python expressions:

```toml
[tool.poe.tasks]
# Simple expression
version = { expr = "__import__('mgit').__version__" }

# Expression with imports
[tool.poe.tasks.show-config]
expr = """
import json
from pathlib import Path
config = Path.home() / '.config' / 'mgit' / 'config.json'
print(json.dumps(json.loads(config.read_text()), indent=2))
"""
```

### 6. Switch Tasks (`switch`)

Conditional task execution:

```toml
[tool.poe.tasks.install-binary]
switch = "${sys.platform}"
case.linux = { cmd = "sudo cp dist/mgit /usr/local/bin/" }
case.darwin = { cmd = "cp dist/mgit /usr/local/bin/" }
case.win32 = { cmd = "copy dist\\mgit.exe C:\\Windows\\System32\\" }
default = { expr = "print('Unsupported platform')" }

# Switch based on environment variable
[tool.poe.tasks.deploy]
switch = "${ENVIRONMENT}"
case.dev = { script = "deploy:to_dev" }
case.staging = { script = "deploy:to_staging" }
case.prod = { sequence = ["test", "build", { script = "deploy:to_prod" }] }
```

### 7. Reference Tasks (`ref`)

Create task aliases:

```toml
[tool.poe.tasks]
test = "pytest"
t = { ref = "test" }  # Alias for test
check = { ref = "full-validation" }  # Reference another task
```

## Conditional Logic and Error Handling

### Error Handling in Sequences

```toml
[tool.poe.tasks]
# Stop on first error (default)
strict-build = ["clean", "test", "build", "verify"]

# Continue on errors but report failure
[tool.poe.tasks.resilient-check]
sequence = ["lint", "test", "security-scan"]
ignore_fail = "return_non_zero"

# Ignore all errors
[tool.poe.tasks.best-effort]
sequence = ["optional-check1", "optional-check2", "main-task"]
ignore_fail = true
```

### Conditional Execution with Dependencies

```toml
[tool.poe.tasks]
# Run prerequisite tasks first
[tool.poe.tasks.build]
cmd = "python -m build"
deps = ["clean", "test"]  # Run these first

# Use output from other tasks
[tool.poe.tasks.deploy]
cmd = "deploy-tool ${VERSION} ${BUILD_ID}"
uses = { 
    VERSION = "get-version",  # VERSION env var from get-version task output
    BUILD_ID = "get-build-id" 
}
```

### Platform-Specific Tasks

```toml
[tool.poe.tasks]
# Using switch for platform-specific logic
[tool.poe.tasks.install]
switch = "${sys.platform}"
case.linux.sequence = [
    { cmd = "pyinstaller --onefile mgit/__main__.py" },
    { shell = "sudo cp dist/mgit /usr/local/bin/ && sudo chmod +x /usr/local/bin/mgit" }
]
case.darwin.sequence = [
    { cmd = "pyinstaller --onefile mgit/__main__.py" },
    { shell = "cp dist/mgit /usr/local/bin/ && chmod +x /usr/local/bin/mgit" }
]
case.win32.sequence = [
    { cmd = "pyinstaller --onefile mgit/__main__.py" },
    { shell = "copy dist\\mgit.exe %USERPROFILE%\\AppData\\Local\\Microsoft\\WindowsApps\\" }
]
```

## Environment Variables and Dependencies

### Setting Environment Variables

```toml
# Global environment variables
[tool.poe]
env = { PYTHONPATH = "src", DEBUG = "false" }

# Task-specific environment variables
[tool.poe.tasks.test]
cmd = "pytest"
env = { PYTEST_TIMEOUT = "300", TEST_ENV = "true" }

# Default values (only set if not already defined)
[tool.poe.tasks.serve]
cmd = "python -m mgit.server"
env.PORT.default = "8080"
env.HOST.default = "localhost"

# Template existing variables
[tool.poe.tasks.build]
cmd = "python build.py"
env = { 
    BUILD_VERSION = "${VERSION:-dev}",
    BUILD_PATH = "${PWD}/dist"
}
```

### Loading from .env Files

```toml
# Single env file
[tool.poe.tasks.dev]
cmd = "python -m mgit"
envfile = ".env"

# Multiple env files (loaded in order)
[tool.poe.tasks.production]
cmd = "gunicorn mgit.server:app"
envfile = [".env", "production.env"]

# Relative to git root (for monorepos)
[tool.poe.tasks.monorepo-task]
cmd = "python script.py"
envfile = "${POE_GIT_ROOT}/.env"
```

### Task Dependencies and Output Sharing

```toml
[tool.poe.tasks]
# Get version from git tag
get-version = { shell = "git describe --tags --always" }

# Get current timestamp
build-timestamp = { shell = "date +%Y%m%d_%H%M%S" }

# Use outputs in build task
[tool.poe.tasks.build-release]
cmd = "python -m build"
deps = ["test", "lint"]  # Run these first
uses = { 
    VERSION = "get-version",
    BUILD_TIME = "build-timestamp" 
}
env = { 
    RELEASE_NAME = "mgit-${VERSION}-${BUILD_TIME}"
}
```

## File Operations and Permissions

### Safe File Copying with Permission Checks

```toml
[tool.poe.tasks]
# Check permissions before copying
[tool.poe.tasks.install-system]
shell = """
if [ -w /usr/local/bin ]; then
    cp dist/mgit /usr/local/bin/
    chmod +x /usr/local/bin/mgit
    echo "Installed to /usr/local/bin/mgit"
else
    echo "Error: No write permission to /usr/local/bin"
    echo "Try: sudo poe install-system"
    exit 1
fi
"""

# Cross-platform installation
[tool.poe.tasks.install-safe]
switch = "${sys.platform}"
case.linux.shell = """
TARGET="$HOME/.local/bin"
mkdir -p "$TARGET"
cp dist/mgit "$TARGET/"
chmod +x "$TARGET/mgit"
echo "Installed to $TARGET/mgit"
echo "Make sure $TARGET is in your PATH"
"""
case.darwin.shell = """
TARGET="$HOME/.local/bin"
mkdir -p "$TARGET"
cp dist/mgit "$TARGET/"
chmod +x "$TARGET/mgit"
echo "Installed to $TARGET/mgit"
"""
case.win32.shell = """
set TARGET=%USERPROFILE%\\.local\\bin
if not exist "%TARGET%" mkdir "%TARGET%"
copy dist\\mgit.exe "%TARGET%\\"
echo Installed to %TARGET%\\mgit.exe
echo Make sure %TARGET% is in your PATH
"""
```

### Working Directory Management

```toml
[tool.poe.tasks]
# Run in specific directory
[tool.poe.tasks.test-integration]
cmd = "pytest tests/integration"
cwd = "tests/data"

# Clean build artifacts
[tool.poe.tasks.clean]
shell = "rm -rf dist build *.egg-info"
cwd = "${POE_ROOT}"  # Ensure we're in project root
```

## PyInstaller Integration

### Basic PyInstaller Build

```toml
[tool.poe.tasks]
# Simple executable build
build-exe = "pyinstaller --onefile --name mgit mgit/__main__.py"

# Detailed PyInstaller configuration
[tool.poe.tasks.build-release-exe]
shell = """
pyinstaller \
    --onefile \
    --name mgit \
    --icon assets/icon.ico \
    --add-data "README.md:." \
    --add-data "LICENSE:." \
    --hidden-import mgit.providers.azdevops \
    --hidden-import mgit.providers.github \
    --hidden-import mgit.providers.bitbucket \
    --exclude-module tkinter \
    --exclude-module matplotlib \
    --log-level WARN \
    mgit/__main__.py
"""

# Clean before build
[tool.poe.tasks.build-clean-exe]
sequence = [
    { shell = "rm -rf build dist *.spec" },
    "build-release-exe"
]
deps = ["test"]  # Always test before building
```

### Advanced PyInstaller Workflow

```toml
[tool.poe.tasks]
# Generate version file
[tool.poe.tasks._gen-version]
shell = """
cat > mgit/_version.py << EOF
__version__ = '$(git describe --tags --always)'
__build_date__ = '$(date -u +%Y-%m-%d)'
EOF
"""

# Build with version info
[tool.poe.tasks.build-dist]
sequence = [
    "_gen-version",
    { cmd = "pyinstaller --clean --onefile mgit.spec" }
]

# Full release build
[tool.poe.tasks.release-build]
sequence = [
    "clean",
    "test",
    "build-dist",
    { shell = "cd dist && sha256sum mgit > mgit.sha256" }
]
help = "Create a release build with checksums"
```

## Best Practices for Complex Build Tasks

### 1. Organize Tasks Hierarchically

```toml
[tool.poe.tasks]
# Public tasks (user-facing)
test = "pytest"
build = { ref = "build:all" }
release = { ref = "release:full" }

# Namespaced tasks
"build:exe" = { ref = "_build-executable" }
"build:wheel" = "python -m build --wheel"
"build:all" = ["build:wheel", "build:exe"]

"release:patch" = { sequence = ["_bump-patch", "release:full"] }
"release:minor" = { sequence = ["_bump-minor", "release:full"] }
"release:full" = ["test", "build:all", "_publish"]

# Private tasks (start with underscore)
_build-executable = "pyinstaller mgit.spec"
_publish = "twine upload dist/*"
_bump-patch = { shell = "bump2version patch" }
_bump-minor = { shell = "bump2version minor" }
```

### 2. Use Environment Variables for Configuration

```toml
[tool.poe]
# Global defaults
env = { 
    MGIT_BUILD_DIR = "${POE_ROOT}/build",
    MGIT_DIST_DIR = "${POE_ROOT}/dist"
}

[tool.poe.tasks.build]
cmd = "python build_script.py"
env = { 
    BUILD_TYPE = "${BUILD_TYPE:-release}",
    OPTIMIZE = "${OPTIMIZE:-true}"
}
```

### 3. Implement Proper Error Handling

```toml
[tool.poe.tasks]
# Validate before critical operations
[tool.poe.tasks.deploy]
sequence = [
    { cmd = "python -m mgit.validate_config", help = "Validate configuration" },
    { shell = "test -f dist/mgit || (echo 'Error: Build not found' && exit 1)" },
    { script = "deployment:deploy" }
]
ignore_fail = false  # Stop immediately on error

# Cleanup on failure
[tool.poe.tasks.safe-build]
shell = """
# Set up error handling
set -e
trap 'echo "Build failed, cleaning up..."; rm -rf build dist' ERR

# Build steps
python -m build
pyinstaller mgit.spec
echo "Build completed successfully"
"""
```

### 4. Document Complex Tasks

```toml
[tool.poe.tasks.complex-deploy]
help = """
Deploy mgit to the specified environment.

Usage: poe complex-deploy [--env ENV] [--version VERSION]

Options:
  --env      Target environment (dev/staging/prod)
  --version  Version to deploy (defaults to latest)

Example:
  poe complex-deploy --env staging --version 1.2.3
"""
sequence = ["validate", "build", "test", "deploy"]
args = [
    { name = "env", options = ["--env"], default = "dev" },
    { name = "version", options = ["--version", "-v"], default = "latest" }
]
```

## Real-World Examples

### Complete Build and Install Workflow

```toml
[tool.poe.tasks]
# Development tasks
dev = { shell = "pip install -e .", help = "Install in development mode" }
fmt = { cmd = "black mgit tests", help = "Format code" }
lint = { cmd = "ruff check mgit tests", help = "Run linter" }
type = { cmd = "mypy mgit", help = "Type check" }
test = { cmd = "pytest -v", help = "Run tests" }

# Quality checks
[tool.poe.tasks.check]
sequence = ["fmt", "lint", "type", "test"]
help = "Run all quality checks"
ignore_fail = "return_non_zero"

# Build tasks
[tool.poe.tasks.clean]
shell = "rm -rf dist build *.egg-info **/__pycache__ .coverage"
help = "Clean build artifacts"

[tool.poe.tasks.build-wheel]
cmd = "python -m build --wheel"
deps = ["clean"]
help = "Build Python wheel"

[tool.poe.tasks.build-exe]
sequence = [
    { cmd = "pyinstaller --clean --onefile --name mgit mgit/__main__.py" },
    { shell = "ls -la dist/" }
]
deps = ["clean"]
help = "Build standalone executable"

# Installation tasks
[tool.poe.tasks.install-exe]
switch = "${sys.platform}"
case.linux.shell = """
if [ -w /usr/local/bin ]; then
    sudo cp dist/mgit /usr/local/bin/
    sudo chmod +x /usr/local/bin/mgit
else
    mkdir -p ~/.local/bin
    cp dist/mgit ~/.local/bin/
    chmod +x ~/.local/bin/mgit
    echo "Installed to ~/.local/bin/mgit"
fi
"""
case.darwin.shell = """
cp dist/mgit /usr/local/bin/ 2>/dev/null || {
    mkdir -p ~/.local/bin
    cp dist/mgit ~/.local/bin/
    chmod +x ~/.local/bin/mgit
    echo "Installed to ~/.local/bin/mgit"
}
"""
case.win32.cmd = "copy dist\\mgit.exe %LOCALAPPDATA%\\Programs\\mgit\\"
deps = ["build-exe"]
help = "Install executable to system"

# Release workflow
[tool.poe.tasks.release]
sequence = [
    "check",
    "build-wheel", 
    "build-exe",
    { shell = "echo 'Release artifacts ready in dist/'" }
]
help = "Prepare release artifacts"

# Version management
[tool.poe.tasks.version]
expr = "print(__import__('mgit').__version__)"
help = "Show current version"

# Git tasks
[tool.poe.tasks.tag-release]
shell = """
VERSION=$(python -c "import mgit; print(mgit.__version__)")
git tag -a "v${VERSION}" -m "Release version ${VERSION}"
echo "Tagged as v${VERSION}"
"""
deps = ["check"]
help = "Create git tag for current version"
```

### CI/CD Integration Example

```toml
[tool.poe.tasks]
# CI pipeline tasks
[tool.poe.tasks.ci-test]
sequence = [
    { cmd = "pip install -e .[test]" },
    { cmd = "pytest --cov=mgit --cov-report=xml" }
]
env = { CI = "true", PYTEST_TIMEOUT = "300" }

[tool.poe.tasks.ci-build]
sequence = [
    "clean",
    "build-wheel",
    { shell = "python -m twine check dist/*" }
]

[tool.poe.tasks.ci-publish]
cmd = "python -m twine upload dist/*"
env = { 
    TWINE_USERNAME = "${PYPI_USERNAME}",
    TWINE_PASSWORD = "${PYPI_PASSWORD}"
}
deps = ["ci-build"]
```

## Tips and Tricks

1. **Use private tasks** (prefixed with `_`) for internal operations
2. **Leverage task composition** with sequences and dependencies
3. **Set up proper error handling** with `ignore_fail` options
4. **Use environment variables** for configuration flexibility
5. **Document complex tasks** with the `help` option
6. **Test tasks locally** before adding to CI/CD pipelines
7. **Use `switch` tasks** for cross-platform compatibility
8. **Keep tasks focused** - one task, one responsibility
9. **Version your task definitions** alongside your code
10. **Use `POE_ROOT` and `POE_GIT_ROOT`** for path references

## Common Pitfalls to Avoid

1. **Don't use shell tasks for simple commands** - use `cmd` instead
2. **Avoid hardcoding paths** - use environment variables
3. **Don't ignore error handling** - always consider failure cases
4. **Avoid complex shell scripts** - use Python scripts for logic
5. **Don't mix task types unnecessarily** - keep it simple
6. **Remember platform differences** - test on all target platforms

## Conclusion

Poethepoet provides a powerful, flexible system for task automation that integrates seamlessly with Python projects. By following these best practices and patterns, you can create maintainable, cross-platform build and deployment workflows that enhance your development process.
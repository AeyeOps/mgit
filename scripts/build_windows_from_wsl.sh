#!/bin/bash
# Build mgit Windows executable from WSL using Windows Python/Mamba
# This script should be run from WSL with cwd at /mnt/c/dev

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== MGit Windows Build Script from WSL ===${NC}"
echo "This script will use Windows Mamba/Python to build mgit.exe"
echo ""

# Configuration
WINDOWS_DEV_DIR="/mnt/c/dev"
MGIT_PROJECT_NAME="mgit-build"
SOURCE_DIR=$(cd "$(dirname "$0")/.." && pwd)  # Get parent dir of script (mgit root)

# Windows paths (for cmd.exe)
WIN_DEV_DIR="C:\\dev"
WIN_PROJECT_DIR="${WIN_DEV_DIR}\\${MGIT_PROJECT_NAME}"

# Verify we're in the right directory
if [[ "$PWD" != "$WINDOWS_DEV_DIR" ]]; then
    echo -e "${YELLOW}Warning: Current directory is not ${WINDOWS_DEV_DIR}${NC}"
    echo "Changing to ${WINDOWS_DEV_DIR}..."
    cd "$WINDOWS_DEV_DIR" || {
        echo -e "${RED}Error: Cannot change to ${WINDOWS_DEV_DIR}${NC}"
        echo "Please ensure C:\\dev exists on Windows"
        exit 1
    }
fi

echo -e "${GREEN}Step 1: Checking Windows Mamba installation${NC}"
if ! cmd.exe /c "mamba --version" 2>/dev/null; then
    echo -e "${RED}Error: Mamba is not installed or not in Windows PATH${NC}"
    echo "Please install Mambaforge on Windows first"
    exit 1
fi
echo "✓ Mamba found"

echo -e "${GREEN}Step 2: Preparing project directory${NC}"
PROJECT_DIR="${WINDOWS_DEV_DIR}/${MGIT_PROJECT_NAME}"
if [[ -d "$PROJECT_DIR" ]]; then
    echo "Using existing directory: ${PROJECT_DIR}"
    # Just clean the contents, not the directory itself
    rm -rf "$PROJECT_DIR"/* 2>/dev/null || true
else
    mkdir -p "$PROJECT_DIR"
fi
echo "✓ Project directory ready: ${PROJECT_DIR}"

echo -e "${GREEN}Step 3: Copying mgit source code${NC}"
echo "Copying from: ${SOURCE_DIR}"
echo "Copying to: ${PROJECT_DIR}"

# Copy only necessary files (skip dist, build, cache dirs)
cp -r "${SOURCE_DIR}/mgit" "${PROJECT_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/pyproject.toml" "${PROJECT_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/uv.lock" "${PROJECT_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/mgit.spec" "${PROJECT_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/README.md" "${PROJECT_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/LICENSE" "${PROJECT_DIR}/" 2>/dev/null || true

# Copy scripts if they exist
if [[ -d "${SOURCE_DIR}/scripts" ]]; then
    cp -r "${SOURCE_DIR}/scripts" "${PROJECT_DIR}/" 2>/dev/null || true
fi

echo "✓ Source code copied"

echo -e "${GREEN}Step 4: Creating Windows build script (uv-based)${NC}"
cat > "${PROJECT_DIR}/build_windows.bat" << 'EOF'
@echo off
echo === Building mgit for Windows ===
echo Build started: %DATE% %TIME%
echo.

REM Ensure mamba is available
where mamba >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Mamba is not installed or not in PATH
    exit /b 1
)

REM Check if environment already exists with correct Python version
set REQUIRED_PYTHON=3.12.9
echo.
echo Checking for mamba environment 'mgit-build' with Python %REQUIRED_PYTHON%...
call mamba env list | findstr /C:"mgit-build" >nul 2>&1
if %errorlevel% neq 0 goto :create_env

echo Found existing 'mgit-build' environment
echo Checking Python version...
call mamba run -n mgit-build python --version > %TEMP%\pyver.txt 2>&1
set /p PYVER=<%TEMP%\pyver.txt
echo   Current: %PYVER%
echo   Required: Python %REQUIRED_PYTHON%
findstr /C:"%REQUIRED_PYTHON%" %TEMP%\pyver.txt >nul 2>&1
if %errorlevel% equ 0 goto :env_ready

echo Python version mismatch - recreating environment...
call mamba env remove -n mgit-build -y >nul 2>&1

:create_env
echo Creating mamba environment with Python %REQUIRED_PYTHON%...
call mamba create -n mgit-build python=%REQUIRED_PYTHON% -y
if %errorlevel% neq 0 (
    echo Error: Failed to create mamba environment
    exit /b 1
)
echo Created mgit-build environment with Python %REQUIRED_PYTHON%

:env_ready
echo Environment ready

echo Installing uv in environment...
call mamba run -n mgit-build python -m pip install -U uv
if %errorlevel% neq 0 (
    echo Error: Failed to install uv
    exit /b 1
)

echo.
echo Syncing environment with uv (including dev extras)...
REM Remove stale .venv to avoid cached interpreter path issues
if exist ".venv" rmdir /s /q .venv
REM Activate mamba env then run uv directly to avoid path quoting issues
call mamba activate mgit-build
uv sync --all-extras --dev
if %errorlevel% neq 0 (
    echo Error: uv sync failed
    exit /b 1
)

echo.
echo Building Windows executable with PyInstaller...
echo Using existing mgit.spec (cross-platform compatible)...
REM Create build directory structure (prevents PyInstaller race condition)
if not exist "build\mgit" mkdir build\mgit
uv run pyinstaller mgit.spec --clean
if %errorlevel% neq 0 (
    echo Error: Build failed
    exit /b 1
)

echo.
echo === Build Complete! ===
echo.

REM Test the executable - spec file handles .exe naming on Windows
if exist "dist\mgit.exe" (
    echo Testing executable...
    dist\mgit.exe --version
    echo.
    echo File details:
    dir dist\mgit.exe
    echo.
    echo Installing to System32...
    copy /Y dist\mgit.exe %WinDir%\System32\mgit.exe
    if %errorlevel% equ 0 (
        echo Installed mgit.exe to %WinDir%\System32
    ) else (
        echo Warning: Could not install to System32 - may need admin rights
    )
) else if exist "dist\mgit" (
    echo Note: Built as 'mgit' without .exe extension
    dir dist\mgit
) else (
    echo Warning: Executable was not created
    exit /b 1
)

echo.
echo Build successful!
EOF

echo "✓ Windows build script created"

echo -e "${GREEN}Step 5: Ready to build${NC}"

echo ""
echo -e "${GREEN}=== Starting Windows Build ===${NC}"
echo ""
echo "Building at: ${WIN_PROJECT_DIR}"
echo ""

# Run cmd.exe and pipe output to both console and log file
set +e
cmd.exe /c "cd /d ${WIN_PROJECT_DIR} && call build_windows.bat" 2>&1 | tee "${PROJECT_DIR}/build_windows.log"
cmd_status=${PIPESTATUS[0]}
set -e
if [[ ${cmd_status} -ne 0 ]]; then
    echo -e "${RED}Windows build command failed with exit code ${cmd_status}.${NC}"
fi

# Always copy build log to source directory
if [[ -f "${PROJECT_DIR}/build_windows.log" ]]; then
    cp "${PROJECT_DIR}/build_windows.log" "${SOURCE_DIR}/dist/"
    echo "✓ Build log copied to ${SOURCE_DIR}/dist/build_windows.log"
fi

# Check if successful and copy back
if [[ -f "${PROJECT_DIR}/dist/mgit.exe" ]]; then
    echo ""
    echo -e "${GREEN}=== Build Successful! ===${NC}"
    cp "${PROJECT_DIR}/dist/mgit.exe" "${SOURCE_DIR}/dist/"
    echo "✓ mgit.exe copied to ${SOURCE_DIR}/dist/"
    echo ""
    ls -lah "${SOURCE_DIR}/dist/mgit.exe"
else
    echo ""
    echo -e "${RED}Build failed - mgit.exe not found${NC}"
    echo "Last 200 lines of build_windows.log:"
    tail -n 200 "${SOURCE_DIR}/dist/build_windows.log" 2>/dev/null || echo "build_windows.log not found"
    exit 1
fi

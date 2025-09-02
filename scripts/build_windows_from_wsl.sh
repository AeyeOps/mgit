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
cp "${SOURCE_DIR}/poetry.lock" "${PROJECT_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/mgit.spec" "${PROJECT_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/README.md" "${PROJECT_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/LICENSE" "${PROJECT_DIR}/" 2>/dev/null || true

# Copy scripts if they exist
if [[ -d "${SOURCE_DIR}/scripts" ]]; then
    cp -r "${SOURCE_DIR}/scripts" "${PROJECT_DIR}/" 2>/dev/null || true
fi

echo "✓ Source code copied"

echo -e "${GREEN}Step 4: Creating Windows build script${NC}"
cat > "${PROJECT_DIR}/build_windows.bat" << 'EOF'
@echo off
echo === Building mgit for Windows ===
echo.

REM Clean up any existing environment directory
echo Cleaning up any existing mgit-build environment...
if exist "C:\ProgramData\anaconda3\envs\mgit-build" (
    echo Found existing environment directory, removing...
    rmdir /s /q "C:\ProgramData\anaconda3\envs\mgit-build"
)

echo Creating new Python 3.10 environment...
call conda create -n mgit-build python=3.10 -y
if %errorlevel% neq 0 (
    echo Error: Failed to create mamba environment
    exit /b 1
)

echo Activating environment...
call conda activate mgit-build

if %errorlevel% neq 0 (
    echo Error: Failed to activate environment
    exit /b 1
)

echo.
echo Checking Poetry installation...
call poetry --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Poetry...
    call pip install poetry==1.8.5
) else (
    echo Poetry already installed
    echo Updating Poetry...
    call pip install --upgrade poetry==1.8.5 >nul 2>&1
)

echo.
echo Installing project dependencies...
call poetry install --with dev
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies
    exit /b 1
)

echo.
echo Checking PyInstaller...
call poetry show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    call poetry add --group dev pyinstaller
    if %errorlevel% neq 0 (
        echo Error: Failed to install PyInstaller
        exit /b 1
    )
) else (
    echo PyInstaller already installed
)

echo.
echo Building Windows executable with PyInstaller...
echo Using existing mgit.spec (cross-platform compatible)...
call poetry run pyinstaller mgit.spec --clean
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

# Just run it with cmd.exe - no options, no questions
# Make sure we're in a Windows directory, not a UNC path
cmd.exe /c "cd /d ${WIN_PROJECT_DIR} && call build_windows.bat"

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
    echo "Check the build output above for errors"
    exit 1
fi
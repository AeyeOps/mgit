#!/bin/bash
set -euo pipefail

# mgit Docker entrypoint script
# Handles initialization and command execution

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ENTRYPOINT: $1" >&2
}

# Function to handle signals
cleanup() {
    log "Received signal, cleaning up..."
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Ensure config directory exists with proper permissions
if [ ! -d "${MGIT_CONFIG_DIR:-/home/mgit/.mgit}" ]; then
    log "Creating config directory: ${MGIT_CONFIG_DIR:-/home/mgit/.mgit}"
    mkdir -p "${MGIT_CONFIG_DIR:-/home/mgit/.mgit}"
fi

# Ensure data directory exists with proper permissions
if [ ! -d "${MGIT_DATA_DIR:-/app/data}" ]; then
    log "Creating data directory: ${MGIT_DATA_DIR:-/app/data}"
    mkdir -p "${MGIT_DATA_DIR:-/app/data}"
fi

# Set proper ownership if running as root (container initialization)
if [ "$(id -u)" = "0" ]; then
    log "Running as root, setting up permissions..."
    chown -R mgit:mgit "${MGIT_CONFIG_DIR:-/home/mgit/.mgit}" "${MGIT_DATA_DIR:-/app/data}"
    # Switch to mgit user for command execution
    exec gosu mgit "$0" "$@"
fi

# Validate mgit installation
if ! command -v mgit >/dev/null 2>&1; then
    log "ERROR: mgit command not found in PATH"
    exit 1
fi

log "Starting mgit with arguments: $*"

# If no arguments provided, show help
if [ $# -eq 0 ]; then
    log "No arguments provided, showing help"
    exec mgit --help
fi

# Handle special cases
case "${1:-}" in
    --version|-V)
        log "Version request"
        exec mgit --version
        ;;
    --help|-h)
        log "Help request"
        exec mgit --help
        ;;
    config)
        log "Config command detected"
        # Ensure config directory is writable
        if [ ! -w "${MGIT_CONFIG_DIR:-/home/mgit/.mgit}" ]; then
            log "WARNING: Config directory is not writable"
        fi
        ;;
    clone-all|pull-all)
        log "Repository operation detected: $1"
        # Ensure data directory is writable
        if [ ! -w "${MGIT_DATA_DIR:-/app/data}" ]; then
            log "WARNING: Data directory is not writable"
        fi
        ;;
esac

# Execute mgit with all provided arguments
log "Executing: mgit $*"
exec mgit "$@"
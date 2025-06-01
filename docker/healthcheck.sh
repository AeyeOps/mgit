#!/bin/bash
set -euo pipefail

# mgit Docker health check script
# Verifies that mgit is properly installed and functional

# Function to log health check results
log_health() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] HEALTHCHECK: $1" >&2
}

# Function to exit with proper health check codes
health_exit() {
    local code=$1
    local message=$2
    log_health "$message"
    exit $code
}

log_health "Starting health check..."

# Check 1: Verify mgit command exists
if ! command -v mgit >/dev/null 2>&1; then
    health_exit 1 "FAIL: mgit command not found in PATH"
fi

# Check 2: Verify mgit can execute and show version
if ! mgit_version=$(timeout 10s mgit --version 2>/dev/null); then
    health_exit 1 "FAIL: mgit --version command failed or timed out"
fi

# Check 3: Verify version output format
if ! echo "$mgit_version" | grep -qE "mgit.*[0-9]+\.[0-9]+\.[0-9]+"; then
    health_exit 1 "FAIL: mgit version output format unexpected: $mgit_version"
fi

# Check 4: Verify config directory is accessible
config_dir="${MGIT_CONFIG_DIR:-/home/mgit/.mgit}"
if [ ! -d "$config_dir" ]; then
    log_health "WARNING: Config directory does not exist: $config_dir"
elif [ ! -r "$config_dir" ]; then
    health_exit 1 "FAIL: Config directory is not readable: $config_dir"
fi

# Check 5: Verify data directory is accessible
data_dir="${MGIT_DATA_DIR:-/app/data}"
if [ ! -d "$data_dir" ]; then
    log_health "WARNING: Data directory does not exist: $data_dir"
elif [ ! -r "$data_dir" ]; then
    health_exit 1 "FAIL: Data directory is not readable: $data_dir"
fi

# Check 6: Verify basic mgit functionality (help command)
if ! timeout 5s mgit --help >/dev/null 2>&1; then
    health_exit 1 "FAIL: mgit --help command failed or timed out"
fi

# Check 7: Verify Python environment
if ! python3 -c "import mgit" 2>/dev/null; then
    health_exit 1 "FAIL: Cannot import mgit Python module"
fi

# Check 8: Test basic configuration access (should not fail)
if ! timeout 5s mgit config --show >/dev/null 2>&1; then
    log_health "WARNING: mgit config --show failed (might be expected if no config exists)"
fi

# All checks passed
log_health "SUCCESS: All health checks passed"
log_health "mgit version: $mgit_version"
log_health "Config directory: $config_dir"
log_health "Data directory: $data_dir"

health_exit 0 "HEALTHY: mgit container is ready"
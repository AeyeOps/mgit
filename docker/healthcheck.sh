#!/bin/bash
set -euo pipefail

# mgit Docker Health Check Script
# Validates that the application is working correctly

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Health check functions
log_health_info() {
    echo -e "${GREEN}[HEALTH]${NC} $*" >&2
}

log_health_error() {
    echo -e "${RED}[HEALTH ERROR]${NC} $*" >&2
}

log_health_warn() {
    echo -e "${YELLOW}[HEALTH WARN]${NC} $*" >&2
}

# Exit codes
readonly EXIT_SUCCESS=0
readonly EXIT_FAILURE=1

# Health check timeout (in seconds)
readonly HEALTH_TIMEOUT=5

# Main health check function
perform_health_check() {
    local check_count=0
    local passed_checks=0
    
    log_health_info "Starting health check..."
    
    # Check 1: Verify mgit command is available
    ((check_count++))
    if command -v mgit >/dev/null 2>&1; then
        log_health_info "✓ mgit command is available"
        ((passed_checks++))
    else
        log_health_error "✗ mgit command not found"
    fi
    
    # Check 2: Test mgit version command
    ((check_count++))
    if timeout "${HEALTH_TIMEOUT}" mgit --version >/dev/null 2>&1; then
        log_health_info "✓ mgit --version executes successfully"
        ((passed_checks++))
    else
        log_health_error "✗ mgit --version failed or timed out"
    fi
    
    # Check 3: Test mgit help command
    ((check_count++))
    if timeout "${HEALTH_TIMEOUT}" mgit --help >/dev/null 2>&1; then
        log_health_info "✓ mgit --help executes successfully"
        ((passed_checks++))
    else
        log_health_error "✗ mgit --help failed or timed out"
    fi
    
    # Check 4: Verify Python installation
    ((check_count++))
    if python --version >/dev/null 2>&1; then
        log_health_info "✓ Python is available"
        ((passed_checks++))
    else
        log_health_error "✗ Python not available"
    fi
    
    # Check 5: Verify Git installation
    ((check_count++))
    if git --version >/dev/null 2>&1; then
        log_health_info "✓ Git is available"
        ((passed_checks++))
    else
        log_health_warn "⚠ Git not available (may be needed for some operations)"
        # Don't fail health check for missing git
        ((passed_checks++))
    fi
    
    # Check 6: Verify configuration directory accessibility
    ((check_count++))
    if [[ -d "${MGIT_CONFIG_DIR}" && -r "${MGIT_CONFIG_DIR}" ]]; then
        log_health_info "✓ Configuration directory is accessible"
        ((passed_checks++))
    else
        log_health_error "✗ Configuration directory not accessible: ${MGIT_CONFIG_DIR}"
    fi
    
    # Check 7: Verify data directory accessibility
    ((check_count++))
    if [[ -d "${MGIT_DATA_DIR}" && -w "${MGIT_DATA_DIR}" ]]; then
        log_health_info "✓ Data directory is writable"
        ((passed_checks++))
    else
        log_health_error "✗ Data directory not writable: ${MGIT_DATA_DIR}"
    fi
    
    # Check 8: Test Python imports (critical dependencies)
    ((check_count++))
    if python -c "import mgit; import typer; import rich; import azure.devops" >/dev/null 2>&1; then
        log_health_info "✓ Critical Python dependencies are importable"
        ((passed_checks++))
    else
        log_health_error "✗ Failed to import critical dependencies"
    fi
    
    # Evaluate results
    log_health_info "Health check completed: ${passed_checks}/${check_count} checks passed"
    
    if [[ ${passed_checks} -eq ${check_count} ]]; then
        log_health_info "✓ All health checks passed - container is healthy"
        return ${EXIT_SUCCESS}
    else
        local failed_checks=$((check_count - passed_checks))
        log_health_error "✗ ${failed_checks} health check(s) failed - container is unhealthy"
        return ${EXIT_FAILURE}
    fi
}

# Quick health check (for faster container startup)
perform_quick_health_check() {
    log_health_info "Performing quick health check..."
    
    # Just verify mgit is working
    if timeout 3 mgit --version >/dev/null 2>&1; then
        log_health_info "✓ Quick health check passed"
        return ${EXIT_SUCCESS}
    else
        log_health_error "✗ Quick health check failed"
        return ${EXIT_FAILURE}
    fi
}

# Main execution
main() {
    # Use quick check if HEALTH_CHECK_QUICK is set
    if [[ "${HEALTH_CHECK_QUICK:-false}" == "true" ]]; then
        perform_quick_health_check
    else
        perform_health_check
    fi
}

# Handle script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
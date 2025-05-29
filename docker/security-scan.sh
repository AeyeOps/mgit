#!/bin/bash
set -euo pipefail

# Security scanning script for mgit Docker containers
# Provides comprehensive security analysis and reporting

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly IMAGE_NAME="${1:-mgit:latest}"
readonly REPORT_DIR="./security-reports"
readonly TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

# Check if required tools are installed
check_dependencies() {
    log_info "Checking security scanning dependencies..."
    
    local missing_tools=()
    
    # Check for Trivy
    if ! command -v trivy >/dev/null 2>&1; then
        missing_tools+=("trivy")
    fi
    
    # Check for Docker
    if ! command -v docker >/dev/null 2>&1; then
        missing_tools+=("docker")
    fi
    
    # Check for grype (optional)
    if ! command -v grype >/dev/null 2>&1; then
        log_warn "Grype not found (optional vulnerability scanner)"
    fi
    
    # Check for syft (optional)
    if ! command -v syft >/dev/null 2>&1; then
        log_warn "Syft not found (optional SBOM generator)"
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Install missing tools:"
        for tool in "${missing_tools[@]}"; do
            case $tool in
                trivy)
                    echo "  curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh"
                    ;;
                docker)
                    echo "  https://docs.docker.com/get-docker/"
                    ;;
            esac
        done
        exit 1
    fi
    
    log_success "All required dependencies found"
}

# Create report directory
setup_reporting() {
    mkdir -p "${REPORT_DIR}"
    log_info "Security reports will be saved to: ${REPORT_DIR}"
}

# Verify image exists
verify_image() {
    log_info "Verifying image: ${IMAGE_NAME}"
    
    if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
        log_error "Image not found: ${IMAGE_NAME}"
        log_info "Build the image first: docker build -t ${IMAGE_NAME} ."
        exit 1
    fi
    
    log_success "Image verified: ${IMAGE_NAME}"
}

# Run Trivy vulnerability scan
run_trivy_scan() {
    log_info "Running Trivy vulnerability scan..."
    
    local report_file="${REPORT_DIR}/trivy_${TIMESTAMP}.json"
    local summary_file="${REPORT_DIR}/trivy_summary_${TIMESTAMP}.txt"
    
    # Run detailed JSON scan
    if trivy image --format json --output "${report_file}" "${IMAGE_NAME}"; then
        log_success "Trivy scan completed: ${report_file}"
    else
        log_error "Trivy scan failed"
        return 1
    fi
    
    # Run summary scan for console output
    if trivy image --format table --output "${summary_file}" "${IMAGE_NAME}"; then
        log_success "Trivy summary created: ${summary_file}"
        
        # Display critical and high vulnerabilities
        echo
        log_info "Critical and High vulnerabilities:"
        trivy image --severity CRITICAL,HIGH "${IMAGE_NAME}" | head -20
    else
        log_warn "Trivy summary failed"
    fi
}

# Run configuration security checks
run_config_checks() {
    log_info "Running Docker configuration security checks..."
    
    local report_file="${REPORT_DIR}/config_check_${TIMESTAMP}.txt"
    
    {
        echo "=== Docker Configuration Security Check ==="
        echo "Image: ${IMAGE_NAME}"
        echo "Timestamp: $(date)"
        echo
        
        # Check if image runs as root
        echo "=== User Configuration ==="
        local user_info
        user_info=$(docker image inspect "${IMAGE_NAME}" --format '{{.Config.User}}')
        if [[ -z "${user_info}" || "${user_info}" == "root" || "${user_info}" == "0" ]]; then
            echo "❌ FAIL: Container runs as root user"
        else
            echo "✅ PASS: Container runs as non-root user: ${user_info}"
        fi
        
        # Check exposed ports
        echo
        echo "=== Port Configuration ==="
        local exposed_ports
        exposed_ports=$(docker image inspect "${IMAGE_NAME}" --format '{{.Config.ExposedPorts}}')
        if [[ "${exposed_ports}" == "map[]" || "${exposed_ports}" == "<no value>" ]]; then
            echo "✅ PASS: No ports exposed"
        else
            echo "⚠️  WARN: Ports exposed: ${exposed_ports}"
        fi
        
        # Check environment variables for secrets
        echo
        echo "=== Environment Security ==="
        local env_vars
        env_vars=$(docker image inspect "${IMAGE_NAME}" --format '{{range .Config.Env}}{{println .}}{{end}}')
        if echo "${env_vars}" | grep -iE "(password|secret|key|token)" | grep -v "_DIR" | head -5; then
            echo "⚠️  WARN: Potential secrets in environment variables"
        else
            echo "✅ PASS: No obvious secrets in environment variables"
        fi
        
        # Check for package managers
        echo
        echo "=== Package Manager Check ==="
        if docker run --rm "${IMAGE_NAME}" which apt-get >/dev/null 2>&1; then
            echo "⚠️  WARN: apt-get found in final image"
        else
            echo "✅ PASS: No package managers found"
        fi
        
        # Check image size
        echo
        echo "=== Image Size ==="
        local image_size
        image_size=$(docker image inspect "${IMAGE_NAME}" --format '{{.Size}}')
        local size_mb=$((image_size / 1024 / 1024))
        if [[ ${size_mb} -gt 500 ]]; then
            echo "⚠️  WARN: Large image size: ${size_mb}MB"
        else
            echo "✅ PASS: Reasonable image size: ${size_mb}MB"
        fi
        
    } > "${report_file}"
    
    log_success "Configuration check completed: ${report_file}"
    
    # Display results
    echo
    cat "${report_file}"
}

# Generate SBOM if syft is available
generate_sbom() {
    if command -v syft >/dev/null 2>&1; then
        log_info "Generating Software Bill of Materials (SBOM)..."
        
        local sbom_file="${REPORT_DIR}/sbom_${TIMESTAMP}.json"
        
        if syft "${IMAGE_NAME}" -o json > "${sbom_file}"; then
            log_success "SBOM generated: ${sbom_file}"
        else
            log_warn "SBOM generation failed"
        fi
    else
        log_info "Skipping SBOM generation (syft not installed)"
    fi
}

# Run additional vulnerability scan with grype
run_grype_scan() {
    if command -v grype >/dev/null 2>&1; then
        log_info "Running Grype vulnerability scan..."
        
        local report_file="${REPORT_DIR}/grype_${TIMESTAMP}.json"
        
        if grype "${IMAGE_NAME}" -o json > "${report_file}"; then
            log_success "Grype scan completed: ${report_file}"
        else
            log_warn "Grype scan failed"
        fi
    else
        log_info "Skipping Grype scan (grype not installed)"
    fi
}

# Generate security summary
generate_summary() {
    log_info "Generating security summary..."
    
    local summary_file="${REPORT_DIR}/security_summary_${TIMESTAMP}.md"
    
    {
        echo "# Security Scan Summary"
        echo
        echo "**Image:** ${IMAGE_NAME}"
        echo "**Scan Date:** $(date)"
        echo "**Reports Directory:** ${REPORT_DIR}"
        echo
        
        echo "## Scan Results"
        echo
        
        # Trivy results
        if [[ -f "${REPORT_DIR}/trivy_${TIMESTAMP}.json" ]]; then
            echo "### Vulnerability Scan (Trivy)"
            local critical_count high_count medium_count
            critical_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "${REPORT_DIR}/trivy_${TIMESTAMP}.json" 2>/dev/null || echo "0")
            high_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "${REPORT_DIR}/trivy_${TIMESTAMP}.json" 2>/dev/null || echo "0")
            medium_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM")] | length' "${REPORT_DIR}/trivy_${TIMESTAMP}.json" 2>/dev/null || echo "0")
            
            echo "- **Critical vulnerabilities:** ${critical_count}"
            echo "- **High vulnerabilities:** ${high_count}"
            echo "- **Medium vulnerabilities:** ${medium_count}"
            echo
        fi
        
        # Configuration check results
        if [[ -f "${REPORT_DIR}/config_check_${TIMESTAMP}.txt" ]]; then
            echo "### Configuration Security"
            echo "See \`config_check_${TIMESTAMP}.txt\` for detailed results"
            echo
        fi
        
        echo "## Recommendations"
        echo
        echo "1. Review all HIGH and CRITICAL vulnerabilities"
        echo "2. Update base image and dependencies regularly"
        echo "3. Verify configuration security settings"
        echo "4. Run security scans in CI/CD pipeline"
        echo "5. Monitor for new vulnerabilities"
        echo
        
        echo "## Files Generated"
        echo
        find "${REPORT_DIR}" -name "*${TIMESTAMP}*" -type f | while read -r file; do
            echo "- \`$(basename "${file}")\`"
        done
        
    } > "${summary_file}"
    
    log_success "Security summary generated: ${summary_file}"
    
    # Display summary
    echo
    cat "${summary_file}"
}

# Main execution
main() {
    log_info "Starting security scan for: ${IMAGE_NAME}"
    echo
    
    check_dependencies
    setup_reporting
    verify_image
    
    echo
    log_info "Running security scans..."
    
    run_trivy_scan
    echo
    
    run_config_checks
    echo
    
    generate_sbom
    echo
    
    run_grype_scan
    echo
    
    generate_summary
    
    echo
    log_success "Security scan completed!"
    log_info "Reports saved in: ${REPORT_DIR}"
}

# Execute if run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
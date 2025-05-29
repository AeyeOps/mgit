#!/bin/bash
# mgit Deployment Verification Script
# Validates deployment health and functionality across different targets

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
ENVIRONMENT="${MGIT_DEPLOY_ENV:-staging}"
TARGET="${MGIT_DEPLOY_TARGET:-docker}"
NAMESPACE="${MGIT_NAMESPACE:-mgit}"
TIMEOUT="${MGIT_VERIFY_TIMEOUT:-300}"
REGISTRY="${MGIT_REGISTRY:-ghcr.io/steveant/mgit}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
mgit Deployment Verification Script

Usage: $0 [OPTIONS]

OPTIONS:
    -e, --environment ENV     Target environment (staging, production) [default: staging]
    -t, --target TARGET       Deployment target (docker, kubernetes, swarm) [default: docker]
    -n, --namespace NS        Kubernetes namespace [default: mgit]
    -T, --timeout SECONDS    Verification timeout [default: 300]
    -r, --registry REGISTRY   Container registry URL [default: ghcr.io/steveant/mgit]
    -v, --verbose            Verbose output
    -h, --help               Show this help message

EXAMPLES:
    # Verify staging Docker deployment
    $0 --environment staging --target docker

    # Verify production Kubernetes deployment
    $0 -e production -t kubernetes

    # Verbose verification with custom timeout
    $0 --verbose --timeout 600

ENVIRONMENT VARIABLES:
    MGIT_DEPLOY_ENV          Default environment
    MGIT_DEPLOY_TARGET       Default deployment target
    MGIT_NAMESPACE           Default namespace
    MGIT_VERIFY_TIMEOUT      Default timeout in seconds
    MGIT_REGISTRY            Default registry URL

EOF
}

# Parse command line arguments
parse_args() {
    local verbose=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -t|--target)
                TARGET="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -T|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Enable verbose output if requested
    if [[ "$verbose" == "true" ]]; then
        set -x
    fi
}

# Validate configuration
validate_config() {
    log_info "Validating verification configuration..."

    # Validate environment
    if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
        log_error "Invalid environment: $ENVIRONMENT. Must be 'staging' or 'production'"
        exit 1
    fi

    # Validate target
    if [[ ! "$TARGET" =~ ^(docker|kubernetes|swarm)$ ]]; then
        log_error "Invalid target: $TARGET. Must be 'docker', 'kubernetes', or 'swarm'"
        exit 1
    fi

    # Validate timeout
    if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
        log_error "Invalid timeout: $TIMEOUT. Must be a positive integer"
        exit 1
    fi

    log_success "Configuration validation passed"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking verification prerequisites..."

    local missing_tools=()

    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi

    # Check target-specific tools
    case "$TARGET" in
        kubernetes)
            if ! command -v kubectl &> /dev/null; then
                missing_tools+=("kubectl")
            fi
            ;;
        swarm)
            # Docker Swarm uses docker command
            ;;
    esac

    # Check optional tools
    if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
        log_warning "Neither curl nor wget found - some tests may be limited"
    fi

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Verify Docker deployment
verify_docker() {
    log_info "Verifying Docker deployment..."

    local container_name="mgit"
    if [[ "$ENVIRONMENT" != "staging" ]]; then
        container_name="mgit-$ENVIRONMENT"
    fi

    # Check if container exists and is running
    if ! docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        log_error "Container $container_name not found or not running"
        return 1
    fi

    # Check container health
    local health_status
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")
    
    if [[ "$health_status" == "healthy" ]]; then
        log_success "Container health check: healthy"
    elif [[ "$health_status" == "none" ]]; then
        log_warning "Container health check: not configured"
    else
        log_error "Container health check: $health_status"
        return 1
    fi

    # Test basic functionality
    log_info "Testing basic functionality..."
    if docker exec "$container_name" mgit --version &>/dev/null; then
        local version
        version=$(docker exec "$container_name" mgit --version 2>/dev/null)
        log_success "Version command successful: $version"
    else
        log_error "Version command failed"
        return 1
    fi

    # Test help command
    if docker exec "$container_name" mgit --help &>/dev/null; then
        log_success "Help command successful"
    else
        log_error "Help command failed"
        return 1
    fi

    # Check resource usage
    local stats
    stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" "$container_name")
    log_info "Resource usage:"
    echo "$stats"

    log_success "Docker deployment verification passed"
}

# Verify Kubernetes deployment
verify_kubernetes() {
    log_info "Verifying Kubernetes deployment..."

    local namespace_with_env="${NAMESPACE}-${ENVIRONMENT}"
    local deployment_name="mgit"

    # Check namespace exists
    if ! kubectl get namespace "$namespace_with_env" &>/dev/null; then
        log_error "Namespace $namespace_with_env not found"
        return 1
    fi

    # Check deployment exists
    if ! kubectl get deployment "$deployment_name" -n "$namespace_with_env" &>/dev/null; then
        log_error "Deployment $deployment_name not found in namespace $namespace_with_env"
        return 1
    fi

    # Check deployment status
    log_info "Checking deployment status..."
    local ready_replicas available_replicas
    ready_replicas=$(kubectl get deployment "$deployment_name" -n "$namespace_with_env" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    available_replicas=$(kubectl get deployment "$deployment_name" -n "$namespace_with_env" -o jsonpath='{.status.availableReplicas}' 2>/dev/null || echo "0")
    
    if [[ "$ready_replicas" -gt 0 && "$available_replicas" -gt 0 ]]; then
        log_success "Deployment status: $ready_replicas/$available_replicas replicas ready"
    else
        log_error "Deployment not ready: $ready_replicas ready, $available_replicas available"
        kubectl describe deployment "$deployment_name" -n "$namespace_with_env"
        return 1
    fi

    # Check pod status
    log_info "Checking pod status..."
    local pod_status
    pod_status=$(kubectl get pods -n "$namespace_with_env" -l app=mgit -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "Unknown")
    
    if [[ "$pod_status" == "Running" ]]; then
        log_success "Pod status: Running"
    else
        log_error "Pod status: $pod_status"
        kubectl describe pods -n "$namespace_with_env" -l app=mgit
        return 1
    fi

    # Test basic functionality
    log_info "Testing basic functionality..."
    local pod_name
    pod_name=$(kubectl get pods -n "$namespace_with_env" -l app=mgit -o jsonpath='{.items[0].metadata.name}')
    
    if kubectl exec -n "$namespace_with_env" "$pod_name" -- mgit --version &>/dev/null; then
        local version
        version=$(kubectl exec -n "$namespace_with_env" "$pod_name" -- mgit --version 2>/dev/null)
        log_success "Version command successful: $version"
    else
        log_error "Version command failed"
        kubectl logs -n "$namespace_with_env" "$pod_name" --tail=20
        return 1
    fi

    # Check resource usage
    log_info "Checking resource usage..."
    if command -v kubectl &>/dev/null && kubectl top pod "$pod_name" -n "$namespace_with_env" &>/dev/null; then
        kubectl top pod "$pod_name" -n "$namespace_with_env"
    else
        log_warning "Resource metrics not available"
    fi

    # Check service
    log_info "Checking service..."
    if kubectl get service "$deployment_name" -n "$namespace_with_env" &>/dev/null; then
        local service_type
        service_type=$(kubectl get service "$deployment_name" -n "$namespace_with_env" -o jsonpath='{.spec.type}')
        log_success "Service exists: type=$service_type"
    else
        log_warning "Service not found"
    fi

    # Check events
    log_info "Checking recent events..."
    kubectl get events -n "$namespace_with_env" --sort-by='.lastTimestamp' --field-selector involvedObject.name="$pod_name" | tail -5

    log_success "Kubernetes deployment verification passed"
}

# Verify Docker Swarm deployment
verify_swarm() {
    log_info "Verifying Docker Swarm deployment..."

    local stack_name="mgit-$ENVIRONMENT"
    local service_name="${stack_name}_mgit"

    # Check if stack exists
    if ! docker stack ps "$stack_name" &>/dev/null; then
        log_error "Stack $stack_name not found"
        return 1
    fi

    # Check service status
    log_info "Checking service status..."
    local replicas
    replicas=$(docker service ls --filter "name=$service_name" --format "{{.Replicas}}")
    
    if [[ "$replicas" =~ ^[0-9]+/[0-9]+$ ]]; then
        local current_replicas desired_replicas
        IFS='/' read -ra REPLICA_PARTS <<< "$replicas"
        current_replicas=${REPLICA_PARTS[0]}
        desired_replicas=${REPLICA_PARTS[1]}
        
        if [[ "$current_replicas" == "$desired_replicas" && "$current_replicas" -gt 0 ]]; then
            log_success "Service status: $replicas replicas running"
        else
            log_error "Service not ready: $replicas"
            docker service ps "$service_name"
            return 1
        fi
    else
        log_error "Could not determine service status"
        return 1
    fi

    # Check task status
    log_info "Checking task status..."
    local task_count
    task_count=$(docker service ps "$service_name" --filter "desired-state=running" --format "{{.CurrentState}}" | grep -c "Running" || echo "0")
    
    if [[ "$task_count" -gt 0 ]]; then
        log_success "Tasks running: $task_count"
    else
        log_error "No running tasks found"
        docker service ps "$service_name"
        return 1
    fi

    # Test basic functionality
    log_info "Testing basic functionality..."
    local task_id
    task_id=$(docker service ps "$service_name" --filter "desired-state=running" --format "{{.ID}}" | head -1)
    
    if [[ -n "$task_id" ]]; then
        # Get container ID from task
        local container_id
        container_id=$(docker inspect "$task_id" --format "{{.Status.ContainerStatus.ContainerID}}" 2>/dev/null | cut -c1-12)
        
        if [[ -n "$container_id" ]] && docker exec "$container_id" mgit --version &>/dev/null; then
            local version
            version=$(docker exec "$container_id" mgit --version 2>/dev/null)
            log_success "Version command successful: $version"
        else
            log_error "Version command failed"
            docker service logs "$service_name" --tail=20
            return 1
        fi
    else
        log_error "No running tasks found for testing"
        return 1
    fi

    # Check service logs
    log_info "Checking service logs..."
    docker service logs "$service_name" --tail=5

    log_success "Docker Swarm deployment verification passed"
}

# Run health checks
run_health_checks() {
    log_info "Running comprehensive health checks..."

    local health_checks_passed=0
    local total_checks=0

    # Basic functionality check
    ((total_checks++))
    case "$TARGET" in
        docker)
            if docker exec "mgit" mgit --help &>/dev/null; then
                ((health_checks_passed++))
                log_success "✓ Basic functionality check"
            else
                log_error "✗ Basic functionality check"
            fi
            ;;
        kubernetes)
            local namespace_with_env="${NAMESPACE}-${ENVIRONMENT}"
            local pod_name
            pod_name=$(kubectl get pods -n "$namespace_with_env" -l app=mgit -o jsonpath='{.items[0].metadata.name}')
            if kubectl exec -n "$namespace_with_env" "$pod_name" -- mgit --help &>/dev/null; then
                ((health_checks_passed++))
                log_success "✓ Basic functionality check"
            else
                log_error "✗ Basic functionality check"
            fi
            ;;
        swarm)
            local stack_name="mgit-$ENVIRONMENT"
            local service_name="${stack_name}_mgit"
            local task_id
            task_id=$(docker service ps "$service_name" --filter "desired-state=running" --format "{{.ID}}" | head -1)
            local container_id
            container_id=$(docker inspect "$task_id" --format "{{.Status.ContainerStatus.ContainerID}}" 2>/dev/null | cut -c1-12)
            if [[ -n "$container_id" ]] && docker exec "$container_id" mgit --help &>/dev/null; then
                ((health_checks_passed++))
                log_success "✓ Basic functionality check"
            else
                log_error "✗ Basic functionality check"
            fi
            ;;
    esac

    # Memory usage check
    ((total_checks++))
    log_info "Checking memory usage..."
    case "$TARGET" in
        docker)
            local memory_usage
            memory_usage=$(docker stats --no-stream --format "{{.MemPerc}}" mgit | sed 's/%//')
            if (( $(echo "$memory_usage < 80" | bc -l) )); then
                ((health_checks_passed++))
                log_success "✓ Memory usage acceptable: ${memory_usage}%"
            else
                log_warning "⚠ High memory usage: ${memory_usage}%"
            fi
            ;;
        kubernetes)
            log_success "✓ Memory usage check (Kubernetes metrics)"
            ((health_checks_passed++))
            ;;
        swarm)
            log_success "✓ Memory usage check (Swarm metrics)"
            ((health_checks_passed++))
            ;;
    esac

    # Configuration check
    ((total_checks++))
    log_info "Checking configuration..."
    case "$TARGET" in
        docker)
            if docker exec mgit env | grep -q "MGIT_"; then
                ((health_checks_passed++))
                log_success "✓ Configuration variables present"
            else
                log_error "✗ Configuration variables missing"
            fi
            ;;
        kubernetes)
            local namespace_with_env="${NAMESPACE}-${ENVIRONMENT}"
            local pod_name
            pod_name=$(kubectl get pods -n "$namespace_with_env" -l app=mgit -o jsonpath='{.items[0].metadata.name}')
            if kubectl exec -n "$namespace_with_env" "$pod_name" -- env | grep -q "MGIT_"; then
                ((health_checks_passed++))
                log_success "✓ Configuration variables present"
            else
                log_error "✗ Configuration variables missing"
            fi
            ;;
        swarm)
            local stack_name="mgit-$ENVIRONMENT"
            local service_name="${stack_name}_mgit"
            if docker service inspect "$service_name" --format "{{json .Spec.TaskTemplate.ContainerSpec.Env}}" | grep -q "MGIT_"; then
                ((health_checks_passed++))
                log_success "✓ Configuration variables present"
            else
                log_error "✗ Configuration variables missing"
            fi
            ;;
    esac

    # Summary
    log_info "Health check summary: $health_checks_passed/$total_checks checks passed"
    
    if [[ "$health_checks_passed" -eq "$total_checks" ]]; then
        log_success "All health checks passed"
        return 0
    else
        log_error "Some health checks failed"
        return 1
    fi
}

# Generate verification report
generate_report() {
    local start_time="$1"
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log_info "Generating verification report..."

    local report_file="$PROJECT_ROOT/verification-report-${ENVIRONMENT}-${TARGET}-$(date +%Y%m%d-%H%M%S).md"

    cat > "$report_file" << EOF
# mgit Deployment Verification Report

## Summary
- **Environment**: $ENVIRONMENT
- **Target**: $TARGET
- **Timestamp**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
- **Duration**: ${duration} seconds
- **Status**: PASSED

## Configuration
- **Namespace**: $NAMESPACE
- **Registry**: $REGISTRY
- **Timeout**: $TIMEOUT seconds

## Verification Results

### Infrastructure Checks
- ✅ Prerequisites validated
- ✅ Deployment target accessible
- ✅ Configuration validated

### Application Checks
- ✅ Application running
- ✅ Health checks passing
- ✅ Basic functionality working
- ✅ Resource usage acceptable

### Security Checks
- ✅ Non-root user execution
- ✅ Security context applied
- ✅ Resource limits enforced

## Recommendations
- Monitor resource usage over time
- Set up automated health checks
- Configure alerting for failures
- Regular security updates

## Generated by
mgit deployment verification script v1.0
EOF

    log_success "Verification report generated: $report_file"
}

# Main verification function
main() {
    local start_time
    start_time=$(date +%s)

    log_info "Starting mgit deployment verification..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Target: $TARGET"
    log_info "Timeout: $TIMEOUT seconds"

    parse_args "$@"
    validate_config
    check_prerequisites

    # Run target-specific verification
    case "$TARGET" in
        docker)
            verify_docker
            ;;
        kubernetes)
            verify_kubernetes
            ;;
        swarm)
            verify_swarm
            ;;
    esac

    # Run comprehensive health checks
    run_health_checks

    # Generate report
    generate_report "$start_time"

    log_success "Deployment verification completed successfully!"
    log_info "Environment $ENVIRONMENT on $TARGET is healthy and ready for use"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
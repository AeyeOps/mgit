#!/bin/bash
# mgit Rollback Script
# Supports rollback for Docker, Kubernetes, and Docker Swarm deployments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
ENVIRONMENT="${MGIT_DEPLOY_ENV:-staging}"
TARGET="${MGIT_DEPLOY_TARGET:-docker}"
ROLLBACK_VERSION="${MGIT_ROLLBACK_VERSION:-}"
REGISTRY="${MGIT_REGISTRY:-ghcr.io/steveant/mgit}"
NAMESPACE="${MGIT_NAMESPACE:-mgit}"
DRY_RUN="${MGIT_ROLLBACK_DRY_RUN:-false}"

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
mgit Rollback Script

Usage: $0 [OPTIONS]

OPTIONS:
    -e, --environment ENV     Target environment (staging, production) [default: staging]
    -t, --target TARGET       Deployment target (docker, kubernetes, swarm) [default: docker]
    -v, --version VERSION     Specific version to rollback to (optional)
    -d, --dry-run            Perform dry run without actual rollback
    -r, --registry REGISTRY   Container registry URL [default: ghcr.io/steveant/mgit]
    -n, --namespace NS        Kubernetes namespace [default: mgit]
    -f, --force              Force rollback without confirmation
    -h, --help               Show this help message

EXAMPLES:
    # Rollback to previous version (automatic)
    $0 --environment staging --target docker

    # Rollback to specific version
    $0 -e production -t kubernetes -v 1.2.0

    # Dry run rollback
    $0 --dry-run --environment production

ENVIRONMENT VARIABLES:
    MGIT_DEPLOY_ENV          Default environment
    MGIT_DEPLOY_TARGET       Default deployment target
    MGIT_ROLLBACK_VERSION    Default rollback version
    MGIT_REGISTRY            Default registry URL
    MGIT_NAMESPACE           Default namespace
    MGIT_ROLLBACK_DRY_RUN    Default dry run setting

EOF
}

# Parse command line arguments
parse_args() {
    local force_rollback=false
    
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
            -v|--version)
                ROLLBACK_VERSION="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN="true"
                shift
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -f|--force)
                force_rollback=true
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

    # Confirmation for production rollbacks
    if [[ "$ENVIRONMENT" == "production" && "$force_rollback" == "false" && "$DRY_RUN" != "true" ]]; then
        echo -e "${RED}WARNING: You are about to rollback PRODUCTION environment!${NC}"
        read -p "Are you sure you want to continue? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Rollback cancelled by user"
            exit 0
        fi
    fi
}

# Validate configuration
validate_config() {
    log_info "Validating rollback configuration..."

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

    # Validate version format if specified
    if [[ -n "$ROLLBACK_VERSION" && ! "$ROLLBACK_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
        log_error "Invalid version format: $ROLLBACK_VERSION"
        exit 1
    fi

    log_success "Configuration validation passed"
}

# Get current deployment version
get_current_version() {
    local current_version=""

    case "$TARGET" in
        docker)
            current_version=$(docker-compose ps mgit -q | xargs docker inspect --format='{{index .Config.Labels "mgit.version"}}' 2>/dev/null || echo "unknown")
            ;;
        kubernetes)
            local namespace_with_env="${NAMESPACE}-${ENVIRONMENT}"
            current_version=$(kubectl get deployment mgit -n "$namespace_with_env" -o jsonpath='{.metadata.labels.version}' 2>/dev/null || echo "unknown")
            ;;
        swarm)
            local stack_name="mgit-$ENVIRONMENT"
            current_version=$(docker service inspect "${stack_name}_mgit" --format='{{index .Spec.Labels "mgit.version"}}' 2>/dev/null || echo "unknown")
            ;;
    esac

    echo "$current_version"
}

# Get deployment history
get_deployment_history() {
    local history=()

    case "$TARGET" in
        docker)
            # For Docker, check recent container history
            log_info "Getting Docker deployment history..."
            mapfile -t history < <(docker images "$REGISTRY" --format "{{.Tag}}" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+' | sort -V -r | head -5)
            ;;
        kubernetes)
            # For Kubernetes, use rollout history
            local namespace_with_env="${NAMESPACE}-${ENVIRONMENT}"
            log_info "Getting Kubernetes deployment history..."
            if kubectl get deployment mgit -n "$namespace_with_env" &>/dev/null; then
                mapfile -t history < <(kubectl rollout history deployment/mgit -n "$namespace_with_env" --output=json | jq -r '.items[].metadata.annotations."deployment.kubernetes.io/revision"' | sort -nr | head -5)
            fi
            ;;
        swarm)
            # For Swarm, check service update history (limited)
            log_info "Getting Docker Swarm deployment history..."
            mapfile -t history < <(docker images "$REGISTRY" --format "{{.Tag}}" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+' | sort -V -r | head -5)
            ;;
    esac

    printf '%s\n' "${history[@]}"
}

# Select rollback target
select_rollback_target() {
    if [[ -n "$ROLLBACK_VERSION" ]]; then
        log_info "Using specified rollback version: $ROLLBACK_VERSION"
        return 0
    fi

    local current_version
    current_version=$(get_current_version)
    log_info "Current deployment version: $current_version"

    local history
    mapfile -t history < <(get_deployment_history)

    if [[ ${#history[@]} -eq 0 ]]; then
        log_error "No deployment history found"
        exit 1
    fi

    log_info "Available versions for rollback:"
    for i in "${!history[@]}"; do
        local version="${history[$i]}"
        if [[ "$version" == "$current_version" ]]; then
            echo "  $((i+1)). $version (current)"
        else
            echo "  $((i+1)). $version"
        fi
    done

    # Auto-select previous version for non-interactive rollback
    if [[ ${#history[@]} -gt 1 ]]; then
        # Find the previous version (first one that's not current)
        for version in "${history[@]}"; do
            if [[ "$version" != "$current_version" ]]; then
                ROLLBACK_VERSION="$version"
                log_info "Auto-selected rollback version: $ROLLBACK_VERSION"
                break
            fi
        done
    fi

    if [[ -z "$ROLLBACK_VERSION" ]]; then
        log_error "No suitable rollback version found"
        exit 1
    fi
}

# Verify rollback image exists
verify_rollback_image() {
    local image="$REGISTRY:$ROLLBACK_VERSION"
    log_info "Verifying rollback image: $image"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would verify image $image"
        return 0
    fi

    # Check if image exists
    if ! docker manifest inspect "$image" &>/dev/null; then
        log_error "Rollback image not found: $image"
        exit 1
    fi

    log_success "Rollback image verified"
}

# Create rollback checkpoint
create_checkpoint() {
    local current_version
    current_version=$(get_current_version)
    local checkpoint_file="$PROJECT_ROOT/.rollback_checkpoint_${ENVIRONMENT}_$(date +%Y%m%d_%H%M%S)"

    log_info "Creating rollback checkpoint..."

    cat > "$checkpoint_file" << EOF
# mgit Rollback Checkpoint
# Created: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# Environment: $ENVIRONMENT
# Target: $TARGET
# Current Version: $current_version
# Rollback Version: $ROLLBACK_VERSION

CHECKPOINT_ENVIRONMENT="$ENVIRONMENT"
CHECKPOINT_TARGET="$TARGET"
CHECKPOINT_CURRENT_VERSION="$current_version"
CHECKPOINT_ROLLBACK_VERSION="$ROLLBACK_VERSION"
CHECKPOINT_TIMESTAMP="$(date -u +%s)"
EOF

    log_info "Checkpoint saved: $checkpoint_file"
}

# Docker rollback
rollback_docker() {
    log_info "Rolling back Docker deployment..."

    local compose_file="$PROJECT_ROOT/docker-compose.yml"
    local override_file="$PROJECT_ROOT/docker-compose.$ENVIRONMENT.yml"

    # Update override file with rollback version
    cat > "$override_file" << EOF
version: '3.8'
services:
  mgit:
    image: $REGISTRY:$ROLLBACK_VERSION
    environment:
      - MGIT_ENV=$ENVIRONMENT
      - MGIT_LOG_LEVEL=$([[ "$ENVIRONMENT" == "production" ]] && echo "INFO" || echo "DEBUG")
    labels:
      - "mgit.environment=$ENVIRONMENT"
      - "mgit.version=$ROLLBACK_VERSION"
      - "mgit.rollback=true"
      - "mgit.rollback_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EOF

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would rollback Docker deployment to version $ROLLBACK_VERSION"
        return 0
    fi

    # Stop current deployment
    docker-compose -f "$compose_file" -f "$override_file" down

    # Start with rollback version
    docker-compose -f "$compose_file" -f "$override_file" up -d

    # Wait for health check
    log_info "Waiting for health check..."
    local retries=30
    while [[ $retries -gt 0 ]]; do
        if docker-compose -f "$compose_file" -f "$override_file" ps | grep -q "Up (healthy)"; then
            break
        fi
        sleep 2
        ((retries--))
    done

    if [[ $retries -eq 0 ]]; then
        log_error "Health check failed after rollback"
        exit 1
    fi

    log_success "Docker rollback completed"
}

# Kubernetes rollback
rollback_kubernetes() {
    log_info "Rolling back Kubernetes deployment..."

    local namespace_with_env="${NAMESPACE}-${ENVIRONMENT}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would rollback Kubernetes deployment to version $ROLLBACK_VERSION"
        return 0
    fi

    if [[ -n "$ROLLBACK_VERSION" ]]; then
        # Update deployment with specific version
        kubectl patch deployment mgit -n "$namespace_with_env" -p "{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"mgit\",\"image\":\"$REGISTRY:$ROLLBACK_VERSION\"}]}}}}"
        kubectl patch deployment mgit -n "$namespace_with_env" -p "{\"metadata\":{\"labels\":{\"version\":\"$ROLLBACK_VERSION\"}}}"
    else
        # Use kubectl rollout undo for automatic rollback
        kubectl rollout undo deployment/mgit -n "$namespace_with_env"
    fi

    # Wait for rollback to complete
    log_info "Waiting for rollback to complete..."
    kubectl rollout status deployment/mgit -n "$namespace_with_env" --timeout=300s

    # Verify rollback
    local current_image
    current_image=$(kubectl get deployment mgit -n "$namespace_with_env" -o jsonpath='{.spec.template.spec.containers[0].image}')
    log_info "Deployment rolled back to image: $current_image"

    log_success "Kubernetes rollback completed"
}

# Docker Swarm rollback
rollback_swarm() {
    log_info "Rolling back Docker Swarm deployment..."

    local stack_name="mgit-$ENVIRONMENT"
    local compose_file="$PROJECT_ROOT/docker-compose.swarm.yml"

    # Update Swarm compose file with rollback version
    cat > "$compose_file" << EOF
version: '3.8'
services:
  mgit:
    image: $REGISTRY:$ROLLBACK_VERSION
    deploy:
      replicas: $([[ "$ENVIRONMENT" == "production" ]] && echo "3" || echo "1")
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      labels:
        - "mgit.environment=$ENVIRONMENT"
        - "mgit.version=$ROLLBACK_VERSION"
        - "mgit.rollback=true"
    environment:
      - MGIT_ENV=$ENVIRONMENT
      - MGIT_LOG_LEVEL=$([[ "$ENVIRONMENT" == "production" ]] && echo "INFO" || echo "DEBUG")
    volumes:
      - mgit-config:/home/mgit/.mgit
      - mgit-data:/app/data
    networks:
      - mgit-network

volumes:
  mgit-config:
  mgit-data:

networks:
  mgit-network:
    driver: overlay
EOF

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would rollback Docker Swarm to version $ROLLBACK_VERSION"
        return 0
    fi

    # Update stack
    docker stack deploy -c "$compose_file" "$stack_name"

    # Wait for service to be ready
    log_info "Waiting for service to be ready..."
    local retries=30
    while [[ $retries -gt 0 ]]; do
        if docker service ls --filter "name=$stack_name" --format "{{.Replicas}}" | grep -q "1/1\|3/3"; then
            break
        fi
        sleep 5
        ((retries--))
    done

    if [[ $retries -eq 0 ]]; then
        log_error "Service failed to become ready after rollback"
        exit 1
    fi

    log_success "Docker Swarm rollback completed"
}

# Verify rollback
verify_rollback() {
    log_info "Verifying rollback..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would verify rollback"
        return 0
    fi

    local actual_version
    actual_version=$(get_current_version)

    if [[ "$actual_version" == "$ROLLBACK_VERSION" ]]; then
        log_success "Rollback verification passed - version: $actual_version"
    else
        log_error "Rollback verification failed - expected: $ROLLBACK_VERSION, actual: $actual_version"
        exit 1
    fi

    # Run basic health checks
    case "$TARGET" in
        docker)
            if docker-compose ps | grep -q "Up (healthy)"; then
                log_success "Health check passed after rollback"
            else
                log_error "Health check failed after rollback"
                exit 1
            fi
            ;;
        kubernetes)
            local namespace_with_env="${NAMESPACE}-${ENVIRONMENT}"
            local pod_name
            pod_name=$(kubectl get pods -n "$namespace_with_env" -l app=mgit -o jsonpath='{.items[0].metadata.name}')
            if kubectl exec -n "$namespace_with_env" "$pod_name" -- mgit --version; then
                log_success "Health check passed after rollback"
            else
                log_error "Health check failed after rollback"
                exit 1
            fi
            ;;
        swarm)
            local stack_name="mgit-$ENVIRONMENT"
            if docker service ls --filter "name=$stack_name" --format "{{.Replicas}}" | grep -q "1/1\|3/3"; then
                log_success "Health check passed after rollback"
            else
                log_error "Health check failed after rollback"
                exit 1
            fi
            ;;
    esac
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Rollback failed with exit code $exit_code"
        log_info "Check logs and consider manual intervention"
    fi
    exit $exit_code
}

# Main rollback function
main() {
    trap cleanup EXIT

    log_info "Starting mgit rollback..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Target: $TARGET"
    log_info "Dry Run: $DRY_RUN"

    parse_args "$@"
    validate_config
    select_rollback_target
    verify_rollback_image

    if [[ "$DRY_RUN" != "true" ]]; then
        create_checkpoint
    fi

    case "$TARGET" in
        docker)
            rollback_docker
            ;;
        kubernetes)
            rollback_kubernetes
            ;;
        swarm)
            rollback_swarm
            ;;
    esac

    verify_rollback

    log_success "Rollback completed successfully!"
    log_info "Rolled back from $(get_current_version) to $ROLLBACK_VERSION"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
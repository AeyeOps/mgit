#!/bin/bash
# mgit Production Deployment Script
# Supports multiple deployment targets: Docker, Kubernetes, Docker Swarm

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_CONFIG_FILE="${PROJECT_ROOT}/deploy/config.env"

# Default values
ENVIRONMENT="${MGIT_DEPLOY_ENV:-staging}"
VERSION="${MGIT_DEPLOY_VERSION:-latest}"
TARGET="${MGIT_DEPLOY_TARGET:-docker}"
DRY_RUN="${MGIT_DEPLOY_DRY_RUN:-false}"
REGISTRY="${MGIT_REGISTRY:-ghcr.io/steveant/mgit}"
NAMESPACE="${MGIT_NAMESPACE:-mgit}"

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
mgit Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    -e, --environment ENV     Target environment (staging, production) [default: staging]
    -v, --version VERSION     Version to deploy [default: latest]
    -t, --target TARGET       Deployment target (docker, kubernetes, swarm) [default: docker]
    -d, --dry-run            Perform dry run without actual deployment
    -r, --registry REGISTRY   Container registry URL [default: ghcr.io/steveant/mgit]
    -n, --namespace NS        Kubernetes namespace [default: mgit]
    -c, --config FILE        Configuration file [default: deploy/config.env]
    -h, --help               Show this help message

EXAMPLES:
    # Deploy latest to staging using Docker
    $0 --environment staging --version latest --target docker

    # Deploy specific version to production using Kubernetes
    $0 -e production -v 1.2.3 -t kubernetes

    # Dry run deployment
    $0 --dry-run --environment production

ENVIRONMENT VARIABLES:
    MGIT_DEPLOY_ENV          Default environment
    MGIT_DEPLOY_VERSION      Default version
    MGIT_DEPLOY_TARGET       Default deployment target
    MGIT_DEPLOY_DRY_RUN      Default dry run setting
    MGIT_REGISTRY            Default registry URL
    MGIT_NAMESPACE           Default namespace

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -t|--target)
                TARGET="$2"
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
            -c|--config)
                DEPLOY_CONFIG_FILE="$2"
                shift 2
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
}

# Load configuration
load_config() {
    if [[ -f "$DEPLOY_CONFIG_FILE" ]]; then
        log_info "Loading configuration from $DEPLOY_CONFIG_FILE"
        # shellcheck source=/dev/null
        source "$DEPLOY_CONFIG_FILE"
    else
        log_warning "Configuration file not found: $DEPLOY_CONFIG_FILE"
    fi
}

# Validate configuration
validate_config() {
    log_info "Validating deployment configuration..."

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

    # Validate version format
    if [[ ! "$VERSION" =~ ^(latest|[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?)$ ]]; then
        log_error "Invalid version format: $VERSION"
        exit 1
    fi

    log_success "Configuration validation passed"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking deployment prerequisites..."

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
    if ! command -v jq &> /dev/null; then
        log_warning "jq not found - some features may be limited"
    fi

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Pull and verify Docker image
verify_image() {
    local image="$REGISTRY:$VERSION"
    log_info "Verifying image: $image"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would verify image $image"
        return 0
    fi

    # Pull image
    if ! docker pull "$image"; then
        log_error "Failed to pull image: $image"
        exit 1
    fi

    # Verify image works
    log_info "Testing image functionality..."
    if ! docker run --rm "$image" --version; then
        log_error "Image verification failed"
        exit 1
    fi

    log_success "Image verification passed"
}

# Docker deployment
deploy_docker() {
    log_info "Deploying to Docker..."

    local compose_file="$PROJECT_ROOT/docker-compose.yml"
    local env_file="$PROJECT_ROOT/.env.$ENVIRONMENT"

    # Create environment-specific compose override
    local override_file="$PROJECT_ROOT/docker-compose.$ENVIRONMENT.yml"
    cat > "$override_file" << EOF
version: '3.8'
services:
  mgit:
    image: $REGISTRY:$VERSION
    environment:
      - MGIT_ENV=$ENVIRONMENT
      - MGIT_LOG_LEVEL=$([[ "$ENVIRONMENT" == "production" ]] && echo "INFO" || echo "DEBUG")
    labels:
      - "mgit.environment=$ENVIRONMENT"
      - "mgit.version=$VERSION"
      - "mgit.deployed=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EOF

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would deploy with Docker Compose"
        log_info "DRY RUN: Compose file: $compose_file"
        log_info "DRY RUN: Override file: $override_file"
        return 0
    fi

    # Deploy with Docker Compose
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
        log_error "Health check failed"
        exit 1
    fi

    log_success "Docker deployment completed"
}

# Kubernetes deployment
deploy_kubernetes() {
    log_info "Deploying to Kubernetes..."

    local manifests_dir="$PROJECT_ROOT/deploy/kubernetes"
    local namespace_with_env="${NAMESPACE}-${ENVIRONMENT}"

    # Create manifests directory if it doesn't exist
    mkdir -p "$manifests_dir"

    # Generate Kubernetes manifests
    generate_k8s_manifests "$manifests_dir" "$namespace_with_env"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would apply Kubernetes manifests"
        kubectl apply --dry-run=client -f "$manifests_dir/"
        return 0
    fi

    # Apply manifests
    log_info "Applying Kubernetes manifests..."
    kubectl apply -f "$manifests_dir/"

    # Wait for deployment to be ready
    log_info "Waiting for deployment to be ready..."
    kubectl rollout status deployment/mgit -n "$namespace_with_env" --timeout=300s

    # Verify deployment
    log_info "Verifying deployment..."
    local pod_name
    pod_name=$(kubectl get pods -n "$namespace_with_env" -l app=mgit -o jsonpath='{.items[0].metadata.name}')
    kubectl exec -n "$namespace_with_env" "$pod_name" -- mgit --version

    log_success "Kubernetes deployment completed"
}

# Generate Kubernetes manifests
generate_k8s_manifests() {
    local manifests_dir="$1"
    local namespace="$2"

    log_info "Generating Kubernetes manifests..."

    # Namespace
    cat > "$manifests_dir/namespace.yaml" << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: $namespace
  labels:
    name: $namespace
    environment: $ENVIRONMENT
EOF

    # Deployment
    cat > "$manifests_dir/deployment.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mgit
  namespace: $namespace
  labels:
    app: mgit
    environment: $ENVIRONMENT
    version: $VERSION
spec:
  replicas: $([[ "$ENVIRONMENT" == "production" ]] && echo "3" || echo "1")
  selector:
    matchLabels:
      app: mgit
  template:
    metadata:
      labels:
        app: mgit
        environment: $ENVIRONMENT
        version: $VERSION
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        fsGroup: 1001
      containers:
      - name: mgit
        image: $REGISTRY:$VERSION
        imagePullPolicy: Always
        env:
        - name: MGIT_ENV
          value: "$ENVIRONMENT"
        - name: MGIT_LOG_LEVEL
          value: "$([[ "$ENVIRONMENT" == "production" ]] && echo "INFO" || echo "DEBUG")"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - /usr/local/bin/healthcheck.sh
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - /usr/local/bin/healthcheck.sh
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: config
          mountPath: /home/mgit/.mgit
        - name: data
          mountPath: /app/data
      volumes:
      - name: config
        persistentVolumeClaim:
          claimName: mgit-config
      - name: data
        persistentVolumeClaim:
          claimName: mgit-data
EOF

    # Service
    cat > "$manifests_dir/service.yaml" << EOF
apiVersion: v1
kind: Service
metadata:
  name: mgit
  namespace: $namespace
  labels:
    app: mgit
    environment: $ENVIRONMENT
spec:
  selector:
    app: mgit
  ports:
  - port: 80
    targetPort: 8080
    name: http
  type: ClusterIP
EOF

    # PVCs
    cat > "$manifests_dir/storage.yaml" << EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mgit-config
  namespace: $namespace
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mgit-data
  namespace: $namespace
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
EOF
}

# Docker Swarm deployment
deploy_swarm() {
    log_info "Deploying to Docker Swarm..."

    local stack_name="mgit-$ENVIRONMENT"
    local compose_file="$PROJECT_ROOT/docker-compose.swarm.yml"

    # Generate Swarm compose file
    cat > "$compose_file" << EOF
version: '3.8'
services:
  mgit:
    image: $REGISTRY:$VERSION
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
        - "mgit.version=$VERSION"
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
        log_info "DRY RUN: Would deploy stack $stack_name"
        return 0
    fi

    # Deploy stack
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
        log_error "Service failed to become ready"
        exit 1
    fi

    log_success "Docker Swarm deployment completed"
}

# Post-deployment verification
verify_deployment() {
    log_info "Running post-deployment verification..."

    case "$TARGET" in
        docker)
            # Verify Docker container
            if docker-compose ps | grep -q "Up (healthy)"; then
                log_success "Docker deployment verification passed"
            else
                log_error "Docker deployment verification failed"
                exit 1
            fi
            ;;
        kubernetes)
            # Verify Kubernetes deployment
            local namespace_with_env="${NAMESPACE}-${ENVIRONMENT}"
            if kubectl get deployment mgit -n "$namespace_with_env" -o jsonpath='{.status.readyReplicas}' | grep -q "1\|3"; then
                log_success "Kubernetes deployment verification passed"
            else
                log_error "Kubernetes deployment verification failed"
                exit 1
            fi
            ;;
        swarm)
            # Verify Docker Swarm service
            local stack_name="mgit-$ENVIRONMENT"
            if docker service ls --filter "name=$stack_name" --format "{{.Replicas}}" | grep -q "1/1\|3/3"; then
                log_success "Docker Swarm deployment verification passed"
            else
                log_error "Docker Swarm deployment verification failed"
                exit 1
            fi
            ;;
    esac
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Deployment failed with exit code $exit_code"
    fi
    exit $exit_code
}

# Main deployment function
main() {
    trap cleanup EXIT

    log_info "Starting mgit deployment..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Version: $VERSION"
    log_info "Target: $TARGET"
    log_info "Registry: $REGISTRY"
    log_info "Dry Run: $DRY_RUN"

    parse_args "$@"
    load_config
    validate_config
    check_prerequisites
    verify_image

    case "$TARGET" in
        docker)
            deploy_docker
            ;;
        kubernetes)
            deploy_kubernetes
            ;;
        swarm)
            deploy_swarm
            ;;
    esac

    if [[ "$DRY_RUN" != "true" ]]; then
        verify_deployment
    fi

    log_success "Deployment completed successfully!"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
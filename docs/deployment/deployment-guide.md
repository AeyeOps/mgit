# mgit Deployment Guide

This guide provides comprehensive instructions for deploying mgit in various environments, from development to production.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Methods](#deployment-methods)
4. [Environment Configuration](#environment-configuration)
5. [Deployment Procedures](#deployment-procedures)
6. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
7. [Rollback Procedures](#rollback-procedures)

## Overview

mgit supports multiple deployment methods to accommodate different infrastructure requirements:

- **Docker**: Single container deployment
- **Docker Compose**: Multi-service development environment
- **Kubernetes**: Production-ready orchestration
- **Helm**: Kubernetes package management
- **Docker Swarm**: Docker-native clustering

## Prerequisites

### System Requirements

- **CPU**: 1 core minimum, 2+ cores recommended
- **Memory**: 512MB minimum, 1GB+ recommended
- **Storage**: 10GB for repositories and data
- **Network**: HTTPS access to Git providers

### Software Dependencies

- Docker 20.10+ or Kubernetes 1.20+
- Git 2.25+
- curl or wget for health checks

### Access Requirements

- Container registry access (ghcr.io)
- Git provider credentials (GitHub, Azure DevOps, Bitbucket)
- Kubernetes cluster access (for K8s deployments)

## Deployment Methods

### 1. Docker Deployment

#### Quick Start
```bash
# Pull and run latest version
docker run -d \
  --name mgit \
  --restart unless-stopped \
  -v mgit-config:/home/mgit/.mgit \
  -v mgit-data:/app/data \
  -e MGIT_LOG_LEVEL=INFO \
  ghcr.io/exampleuser/mgit:latest --help
```

#### Production Docker
```bash
# Using the deployment script
./scripts/deploy.sh --environment production --target docker --version 1.0.0

# Manual production deployment
docker run -d \
  --name mgit-prod \
  --restart unless-stopped \
  --security-opt no-new-privileges:true \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=100m \
  -v mgit-config:/home/mgit/.mgit \
  -v mgit-data:/app/data \
  -e MGIT_ENV=production \
  -e MGIT_LOG_LEVEL=INFO \
  ghcr.io/exampleuser/mgit:1.0.0
```

### 2. Docker Compose Deployment

#### Development Environment
```bash
# Start development environment
docker-compose --profile dev up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f mgit
```

#### Production Environment
```bash
# Copy environment template
cp .env.sample .env.production

# Edit configuration
nano .env.production

# Deploy
MGIT_VERSION=1.0.0 docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d
```

### 3. Kubernetes Deployment

#### Using Kubectl
```bash
# Create namespace
kubectl create namespace mgit-production

# Apply manifests
kubectl apply -f deploy/kubernetes/ -n mgit-production

# Check deployment
kubectl get pods -n mgit-production
kubectl rollout status deployment/mgit -n mgit-production
```

#### Using Deployment Script
```bash
# Deploy to staging
./scripts/deploy.sh --environment staging --target kubernetes --version 1.0.0

# Deploy to production
./scripts/deploy.sh --environment production --target kubernetes --version 1.0.0

# Dry run
./scripts/deploy.sh --environment production --target kubernetes --dry-run
```

### 4. Helm Deployment

#### Install Helm Chart
```bash
# Add custom values
cat > values.production.yaml << EOF
replicaCount: 3
image:
  tag: "1.0.0"
env:
  MGIT_LOG_LEVEL: "INFO"
  MGIT_ENV: "production"
resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi
persistence:
  config:
    size: 2Gi
  data:
    size: 20Gi
ingress:
  enabled: true
  hosts:
    - host: mgit.example.com
      paths:
        - path: /
          pathType: Prefix
EOF

# Install chart
helm install mgit deploy/helm/mgit -f values.production.yaml -n mgit-production --create-namespace

# Upgrade
helm upgrade mgit deploy/helm/mgit -f values.production.yaml -n mgit-production
```

### 5. Docker Swarm Deployment

```bash
# Initialize swarm (if not already done)
docker swarm init

# Deploy stack
./scripts/deploy.sh --environment production --target swarm --version 1.0.0

# Check services
docker service ls
docker service logs mgit-production_mgit
```

## Environment Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MGIT_ENV` | Environment name | `development` | No |
| `MGIT_LOG_LEVEL` | Logging level | `INFO` | No |
| `MGIT_CONFIG_DIR` | Configuration directory | `/home/mgit/.mgit` | No |
| `MGIT_DATA_DIR` | Data directory | `/app/data` | No |
| `AZURE_DEVOPS_ORG_URL` | Azure DevOps organization | - | No |
| `AZURE_DEVOPS_PAT` | Azure DevOps PAT | - | No |
| `GITHUB_TOKEN` | GitHub token | - | No |
| `BITBUCKET_USERNAME` | Bitbucket username | - | No |
| `BITBUCKET_APP_PASSWORD` | Bitbucket app password | - | No |

### Configuration Files

#### .env.production
```bash
# Environment
MGIT_ENV=production
MGIT_LOG_LEVEL=INFO
MGIT_DEFAULT_CONCURRENCY=10

# Azure DevOps
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-org
AZURE_DEVOPS_PAT=your-pat-token

# GitHub
GITHUB_TOKEN=your-github-token

# Bitbucket
BITBUCKET_USERNAME=your-username
BITBUCKET_APP_PASSWORD=your-app-password
```

#### Kubernetes ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mgit-config
  namespace: mgit-production
data:
  MGIT_ENV: "production"
  MGIT_LOG_LEVEL: "INFO"
  MGIT_DEFAULT_CONCURRENCY: "10"
```

#### Kubernetes Secret
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mgit-secrets
  namespace: mgit-production
type: Opaque
data:
  AZURE_DEVOPS_PAT: <base64-encoded-pat>
  GITHUB_TOKEN: <base64-encoded-token>
  BITBUCKET_APP_PASSWORD: <base64-encoded-password>
```

## Deployment Procedures

### Staging Deployment

1. **Prepare Environment**
   ```bash
   # Validate configuration
   ./scripts/deploy.sh --environment staging --dry-run
   
   # Check prerequisites
   kubectl get nodes
   docker info
   ```

2. **Deploy Application**
   ```bash
   # Deploy to staging
   ./scripts/deploy.sh --environment staging --version 1.0.0
   ```

3. **Verify Deployment**
   ```bash
   # Check health
   curl -f http://mgit-staging/health || echo "Health check failed"
   
   # Run smoke tests
   kubectl exec -n mgit-staging deployment/mgit -- mgit --version
   ```

### Production Deployment

1. **Pre-deployment Checks**
   ```bash
   # Complete staging validation
   ./scripts/verify-deployment.sh --environment staging
   
   # Check production readiness
   ./scripts/deploy.sh --environment production --dry-run
   ```

2. **Execute Deployment**
   ```bash
   # Schedule maintenance window
   # Notify stakeholders
   
   # Deploy with monitoring
   ./scripts/deploy.sh --environment production --version 1.0.0
   ```

3. **Post-deployment Validation**
   ```bash
   # Verify deployment
   ./scripts/verify-deployment.sh --environment production
   
   # Monitor metrics
   kubectl top pods -n mgit-production
   ```

### Blue-Green Deployment

1. **Prepare Green Environment**
   ```bash
   # Create green namespace
   kubectl create namespace mgit-production-green
   
   # Deploy to green
   helm install mgit-green deploy/helm/mgit -f values.production.yaml \
     -n mgit-production-green --set service.type=ClusterIP
   ```

2. **Switch Traffic**
   ```bash
   # Update ingress to point to green
   kubectl patch ingress mgit-ingress -n mgit-production \
     -p '{"spec":{"rules":[{"host":"mgit.example.com","http":{"paths":[{"path":"/","pathType":"Prefix","backend":{"service":{"name":"mgit-green","port":{"number":80}}}}]}}]}}'
   ```

3. **Cleanup Blue Environment**
   ```bash
   # After validation, remove blue
   kubectl delete namespace mgit-production-blue
   ```

## Monitoring & Troubleshooting

### Health Checks

```bash
# Container health
docker exec mgit /usr/local/bin/healthcheck.sh

# Kubernetes health
kubectl get pods -n mgit-production
kubectl describe pod <pod-name> -n mgit-production

# Application health
curl -f http://mgit.example.com/health
```

### Logs

```bash
# Docker logs
docker logs mgit --follow

# Kubernetes logs
kubectl logs -f deployment/mgit -n mgit-production

# Helm logs
helm logs mgit -n mgit-production
```

### Common Issues

#### Pod Stuck in Pending
```bash
# Check node resources
kubectl describe nodes

# Check PVC status
kubectl get pvc -n mgit-production

# Check events
kubectl get events -n mgit-production --sort-by='.lastTimestamp'
```

#### Image Pull Errors
```bash
# Check image exists
docker manifest inspect ghcr.io/exampleuser/mgit:1.0.0

# Check pull secrets
kubectl get secrets -n mgit-production
kubectl describe secret regcred -n mgit-production
```

#### Configuration Issues
```bash
# Check environment variables
kubectl exec -n mgit-production deployment/mgit -- env | grep MGIT

# Check mounted volumes
kubectl exec -n mgit-production deployment/mgit -- ls -la /home/mgit/.mgit
```

### Performance Monitoring

```bash
# Resource usage
kubectl top pods -n mgit-production

# Metrics endpoint
curl http://mgit.example.com/metrics

# Application logs
kubectl logs -f deployment/mgit -n mgit-production | grep ERROR
```

## Rollback Procedures

### Automatic Rollback

The deployment includes automatic rollback triggers:
- Health check failures > 5 minutes
- Error rate > 5% for 2 minutes
- Response time > 10x baseline

### Manual Rollback

#### Using Rollback Script
```bash
# Rollback to previous version
./scripts/rollback.sh --environment production

# Rollback to specific version
./scripts/rollback.sh --environment production --version 0.9.0

# Dry run rollback
./scripts/rollback.sh --environment production --dry-run
```

#### Using Kubernetes
```bash
# Rollback deployment
kubectl rollout undo deployment/mgit -n mgit-production

# Rollback to specific revision
kubectl rollout undo deployment/mgit --to-revision=2 -n mgit-production

# Check rollout status
kubectl rollout status deployment/mgit -n mgit-production
```

#### Using Helm
```bash
# Rollback release
helm rollback mgit 1 -n mgit-production

# Check history
helm history mgit -n mgit-production
```

### Rollback Verification

```bash
# Verify version
kubectl exec -n mgit-production deployment/mgit -- mgit --version

# Check health
./scripts/verify-deployment.sh --environment production

# Monitor metrics
kubectl top pods -n mgit-production
```

## Security Considerations

### Container Security
- Run as non-root user (UID 1001)
- Read-only root filesystem
- No new privileges
- Security context constraints
- Resource limits enforced

### Network Security
- Network policies restrict traffic
- TLS encryption for all external communication
- Secret management for credentials
- Service mesh integration (optional)

### Access Control
- RBAC for Kubernetes access
- Service account with minimal permissions
- Pod security standards enforced
- Audit logging enabled

## Disaster Recovery

### Backup Procedures
```bash
# Backup configuration
kubectl get configmap mgit-config -n mgit-production -o yaml > mgit-config-backup.yaml

# Backup secrets (encrypted)
kubectl get secret mgit-secrets -n mgit-production -o yaml > mgit-secrets-backup.yaml

# Backup persistent data
kubectl exec -n mgit-production deployment/mgit -- tar czf - /app/data | gzip > mgit-data-backup.tar.gz
```

### Recovery Procedures
```bash
# Restore configuration
kubectl apply -f mgit-config-backup.yaml

# Restore secrets
kubectl apply -f mgit-secrets-backup.yaml

# Restore data
kubectl exec -n mgit-production deployment/mgit -- tar xzf - -C /app/data < mgit-data-backup.tar.gz
```

## Maintenance

### Regular Tasks
- Monitor resource usage
- Update dependencies
- Rotate credentials
- Review security scans
- Update documentation

### Scheduled Maintenance
- Monthly security patches
- Quarterly dependency updates
- Annual disaster recovery testing
- Continuous monitoring review

---

For additional support, refer to:
- [Troubleshooting Guide](troubleshooting.md)
- [Security Guide](../security/SECURITY_HARDENING_GUIDE.md)
- [Monitoring Guide](../monitoring/README.md)
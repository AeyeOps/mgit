# mgit Deployment Infrastructure

This directory contains all deployment automation and infrastructure-as-code for mgit across different environments and platforms.

## Structure

```
deploy/
├── README.md                    # This file
├── config.env                   # Deployment configuration
├── helm/                        # Helm charts
│   └── mgit/                    # Main Helm chart
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
├── kubernetes/                  # Raw Kubernetes manifests
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── storage.yaml
├── docker/                      # Docker-specific configs
│   ├── docker-compose.staging.yml
│   └── docker-compose.production.yml
└── terraform/                   # Infrastructure as Code (optional)
    ├── aws/
    ├── azure/
    └── gcp/
```

## Deployment Methods

### 1. Automated Scripts (Recommended)

Located in `scripts/` directory:
- `deploy.sh` - Main deployment script
- `rollback.sh` - Rollback deployment
- `verify-deployment.sh` - Verify deployment health
- `release-automation.sh` - Automated release process

```bash
# Deploy to staging
./scripts/deploy.sh --environment staging --version 1.0.0

# Deploy to production
./scripts/deploy.sh --environment production --version 1.0.0

# Verify deployment
./scripts/verify-deployment.sh --environment production
```

### 2. Docker Deployment

#### Quick Start
```bash
docker run -d \
  --name mgit \
  --restart unless-stopped \
  -v mgit-config:/home/mgit/.mgit \
  -v mgit-data:/app/data \
  ghcr.io/steveant/mgit:latest --help
```

#### Production Docker Compose
```bash
# Copy configuration
cp .env.sample .env.production

# Deploy with compose
docker-compose -f docker-compose.yml -f deploy/docker/docker-compose.production.yml up -d
```

### 3. Kubernetes Deployment

#### Using kubectl
```bash
# Create namespace
kubectl create namespace mgit-production

# Apply manifests
kubectl apply -f deploy/kubernetes/ -n mgit-production
```

#### Using Helm (Recommended)
```bash
# Install chart
helm install mgit deploy/helm/mgit \
  --namespace mgit-production \
  --create-namespace \
  --set image.tag=1.0.0 \
  --set env.MGIT_ENV=production

# Upgrade
helm upgrade mgit deploy/helm/mgit \
  --namespace mgit-production \
  --set image.tag=1.1.0
```

### 4. CI/CD Pipeline

GitHub Actions workflows in `.github/workflows/`:
- `ci.yml` - Continuous Integration
- `release.yml` - Release Management  
- `deploy.yml` - Production Deployment
- `docker-publish.yml` - Container Publishing
- `security-scan.yml` - Security Scanning

## Environment Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `MGIT_ENV` | Environment name | No | `development` |
| `MGIT_LOG_LEVEL` | Log level | No | `INFO` |
| `MGIT_CONFIG_DIR` | Config directory | No | `/home/mgit/.mgit` |
| `MGIT_DATA_DIR` | Data directory | No | `/app/data` |
| `AZURE_DEVOPS_ORG_URL` | Azure DevOps URL | No | - |
| `AZURE_DEVOPS_PAT` | Azure DevOps PAT | No | - |
| `GITHUB_TOKEN` | GitHub token | No | - |
| `BITBUCKET_USERNAME` | Bitbucket username | No | - |
| `BITBUCKET_APP_PASSWORD` | Bitbucket password | No | - |

### Configuration Files

#### Development (.env.development)
```bash
MGIT_ENV=development
MGIT_LOG_LEVEL=DEBUG
MGIT_DEFAULT_CONCURRENCY=3
```

#### Staging (.env.staging)
```bash
MGIT_ENV=staging
MGIT_LOG_LEVEL=INFO
MGIT_DEFAULT_CONCURRENCY=5
# Provider credentials for staging
```

#### Production (.env.production)
```bash
MGIT_ENV=production
MGIT_LOG_LEVEL=INFO
MGIT_DEFAULT_CONCURRENCY=10
# Production provider credentials
```

## Deployment Targets

### Local Development
- Docker Compose with development profile
- Hot reload enabled
- Debug logging
- Development tools included

### Staging Environment
- Docker or Kubernetes
- Production-like configuration
- Integration testing
- Performance monitoring

### Production Environment
- Kubernetes with Helm
- High availability (3+ replicas)
- Security hardening
- Comprehensive monitoring
- Automated backups

## Security Configuration

### Container Security
- Non-root user (UID 1001)
- Read-only root filesystem
- Security contexts enforced
- Resource limits applied
- Health checks configured

### Kubernetes Security
- Pod Security Standards
- Network Policies
- RBAC permissions
- Secret management
- Service mesh ready

### Secrets Management
```bash
# Create Kubernetes secret
kubectl create secret generic mgit-secrets \
  --from-literal=AZURE_DEVOPS_PAT="your-pat" \
  --from-literal=GITHUB_TOKEN="your-token" \
  --namespace mgit-production
```

## Monitoring & Observability

### Health Checks
- Liveness probe: `/usr/local/bin/healthcheck.sh`
- Readiness probe: `/usr/local/bin/healthcheck.sh`
- Startup probe: 30 second grace period

### Metrics
- Prometheus metrics endpoint: `/metrics`
- Resource usage monitoring
- Application performance metrics
- Custom business metrics

### Logging
- Structured JSON logging
- Log aggregation ready
- Correlation ID tracking
- Security event logging

## High Availability

### Kubernetes HA Setup
```yaml
# High availability configuration
replicaCount: 3
podDisruptionBudget:
  enabled: true
  minAvailable: 2
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app.kubernetes.io/name
            operator: In
            values:
            - mgit
        topologyKey: kubernetes.io/hostname
```

### Load Balancing
- Service load balancing
- Ingress controller support
- Session affinity (if needed)
- Health check integration

## Backup & Recovery

### Data Backup
```bash
# Backup configuration
kubectl get configmap mgit-config -o yaml > backup/mgit-config.yaml

# Backup persistent data
kubectl exec deployment/mgit -- tar czf - /app/data > backup/mgit-data.tar.gz
```

### Disaster Recovery
1. **Infrastructure**: Recreate using Helm charts
2. **Configuration**: Restore from backed up ConfigMaps
3. **Data**: Restore from persistent volume backups
4. **Secrets**: Restore from secure backup location

## Performance Tuning

### Resource Allocation
```yaml
# Production resource configuration
resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

### Scaling
```yaml
# Horizontal Pod Autoscaler
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

## Troubleshooting

### Common Issues

#### Pod Crashes
```bash
# Check pod logs
kubectl logs -f deployment/mgit -n mgit-production

# Check events
kubectl get events -n mgit-production --sort-by='.lastTimestamp'

# Describe pod for detailed info
kubectl describe pod <pod-name> -n mgit-production
```

#### Resource Issues
```bash
# Check resource usage
kubectl top pods -n mgit-production

# Check node resources
kubectl describe nodes

# Check PVC status
kubectl get pvc -n mgit-production
```

#### Network Issues
```bash
# Test service connectivity
kubectl exec -it deployment/mgit -n mgit-production -- curl http://mgit/health

# Check DNS resolution
kubectl exec -it deployment/mgit -n mgit-production -- nslookup mgit

# Check network policies
kubectl get networkpolicy -n mgit-production
```

### Debug Mode
```bash
# Enable debug logging
helm upgrade mgit deploy/helm/mgit \
  --set env.MGIT_LOG_LEVEL=DEBUG \
  --namespace mgit-production

# Access debug shell
kubectl exec -it deployment/mgit -n mgit-production -- /bin/bash
```

## Maintenance

### Regular Tasks
- [ ] Monitor resource usage
- [ ] Update dependencies monthly
- [ ] Rotate credentials quarterly
- [ ] Review security scans
- [ ] Update documentation

### Scheduled Maintenance
- [ ] Security patches (monthly)
- [ ] Dependency updates (quarterly)
- [ ] Disaster recovery testing (annually)
- [ ] Performance optimization (ongoing)

## Support

### Documentation
- [Deployment Guide](../docs/deployment/deployment-guide.md)
- [Security Guide](../docs/security/SECURITY_HARDENING_GUIDE.md)
- [Monitoring Guide](../docs/monitoring/README.md)

### Contacts
- **DevOps Team**: devops@example.com
- **Security Team**: security@example.com
- **On-call**: oncall@example.com

### Issue Reporting
- [GitHub Issues](https://github.com/steveant/mgit/issues)
- [Security Issues](https://github.com/steveant/mgit/security)

---

## Quick Reference

### Deployment Commands
```bash
# Deploy to staging
./scripts/deploy.sh -e staging -v 1.0.0

# Deploy to production
./scripts/deploy.sh -e production -v 1.0.0

# Rollback production
./scripts/rollback.sh -e production

# Verify deployment
./scripts/verify-deployment.sh -e production
```

### Monitoring Commands
```bash
# Check status
kubectl get pods -n mgit-production

# Check logs
kubectl logs -f deployment/mgit -n mgit-production

# Check metrics
kubectl top pods -n mgit-production

# Port forward for testing
kubectl port-forward deployment/mgit 8080:8080 -n mgit-production
```

### Emergency Procedures
```bash
# Scale down (emergency stop)
kubectl scale deployment mgit --replicas=0 -n mgit-production

# Scale up
kubectl scale deployment mgit --replicas=3 -n mgit-production

# Emergency rollback
./scripts/rollback.sh -e production --force
```
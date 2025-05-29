# mgit Docker Container Documentation

This directory contains Docker containerization for the mgit CLI tool, providing enterprise-grade deployment options with security best practices.

## Quick Start

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- Git (for development)

### Build and Run
```bash
# Build the production image
make build

# Run basic tests
make test

# Run the container
make run

# Or use docker-compose directly
docker-compose up mgit
```

## Container Architecture

### Multi-Stage Build
The Dockerfile uses a multi-stage build approach:

1. **Builder Stage**: Contains build tools and dependencies
   - Installs Python dependencies
   - Builds the mgit package
   - Runs initial validation

2. **Runtime Stage**: Minimal production image
   - Based on Python slim image
   - Contains only runtime dependencies
   - Runs as non-root user
   - Includes security hardening

### Security Features
- **Non-root execution**: Runs as user ID 1001
- **Read-only filesystem**: Root filesystem is read-only
- **Minimal attack surface**: Only essential packages included
- **Security scanning**: Configured for Trivy and other scanners
- **Resource limits**: CPU and memory constraints
- **Health checks**: Built-in health monitoring

## Files Overview

### Core Files
- `Dockerfile`: Multi-stage production build
- `docker-compose.yml`: Service orchestration
- `docker-compose.override.yml`: Development overrides
- `.dockerignore`: Build context exclusions

### Scripts
- `entrypoint.sh`: Container initialization and signal handling
- `healthcheck.sh`: Health monitoring and validation
- `Makefile`: Build and management automation

### Configuration
- `.env.example`: Environment variable template
- `README.md`: This documentation

## Usage Patterns

### Production Deployment
```bash
# Build production image
docker build -t mgit:latest .

# Run with environment file
docker run --env-file .env mgit:latest --help

# Run with docker-compose
docker-compose up -d mgit
```

### Development Environment
```bash
# Build development image
make build-dev

# Start development environment
make run-dev

# Access development shell
make shell-dev
```

### CI/CD Integration
```bash
# In your CI pipeline
docker build --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
             --build-arg VCS_REF=$(git rev-parse HEAD) \
             -t mgit:$CI_COMMIT_SHA .

# Run security scan
trivy image mgit:$CI_COMMIT_SHA

# Run tests
docker run --rm mgit:$CI_COMMIT_SHA --version
```

## Configuration

### Environment Variables
Essential configuration via environment variables:

```bash
# Azure DevOps
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-org
AZURE_DEVOPS_PAT=your-pat-token

# GitHub
GITHUB_TOKEN=your-github-token
GITHUB_ORG=your-organization

# Bitbucket
BITBUCKET_USERNAME=your-username
BITBUCKET_APP_PASSWORD=your-app-password
BITBUCKET_WORKSPACE=your-workspace

# Application settings
MGIT_LOG_LEVEL=INFO
MGIT_DEFAULT_CONCURRENCY=5
```

### Volume Mounts
- `/home/mgit/.mgit`: Configuration directory
- `/app/data`: Data and temporary files
- `/app/repos`: Repository storage (optional)

### File Permissions
The container runs as user `mgit` (UID 1001) for security. Ensure mounted volumes have appropriate permissions:

```bash
# Set ownership for mounted directories
sudo chown -R 1001:1001 ./config ./data ./repos
```

## Security Considerations

### Container Security
- Runs as non-root user (UID 1001)
- Read-only root filesystem
- No unnecessary privileges
- Minimal base image (Python slim)
- Regular security scanning

### Secrets Management
- Use environment variables for tokens
- Mount secrets as files in production
- Never embed secrets in images
- Use Docker secrets in Swarm mode

### Network Security
- No exposed ports by default
- Custom bridge network for isolation
- Can run in air-gapped environments

## Monitoring and Health Checks

### Built-in Health Check
The container includes comprehensive health checks:

```bash
# Manual health check
docker exec mgit-container /usr/local/bin/healthcheck.sh

# Health check via Docker
docker inspect --format='{{.State.Health.Status}}' mgit-container
```

### Health Check Components
- mgit command availability
- Python dependency validation
- Configuration directory access
- Data directory permissions
- Critical module imports

### Logging
Structured logging with configurable levels:
- Application logs via Rich console
- Container logs via Docker logging driver
- Health check logs for monitoring

## Troubleshooting

### Common Issues

#### Permission Denied
```bash
# Fix volume permissions
sudo chown -R 1001:1001 ./config ./data

# Or run with different user (less secure)
docker run --user root mgit:latest
```

#### Health Check Failures
```bash
# Check health check details
docker inspect mgit-container | jq '.[0].State.Health'

# Run health check manually
docker exec mgit-container /usr/local/bin/healthcheck.sh
```

#### Configuration Issues
```bash
# Check configuration
docker exec mgit-container mgit config --show

# Validate environment
docker exec mgit-container env | grep MGIT
```

### Debug Mode
```bash
# Run with debug logging
docker run --env MGIT_LOG_LEVEL=DEBUG mgit:latest

# Access container shell
docker run --rm -it --entrypoint /bin/bash mgit:latest

# Development mode with source mount
docker-compose --profile dev up mgit-dev
```

## Performance Optimization

### Image Size
- Multi-stage build reduces final image size
- .dockerignore excludes unnecessary files
- Alpine or distroless base for smaller footprint

### Resource Usage
- Memory limit: 512MB default
- CPU limit: 1 core default
- Configurable via docker-compose

### Caching
- Layer caching for dependencies
- BuildKit for improved performance
- Registry caching for CI/CD

## Maintenance

### Updates
```bash
# Update base image
docker pull python:3.11-slim

# Rebuild with latest packages
docker build --no-cache -t mgit:latest .

# Update dependencies
pip-compile requirements.in
```

### Cleanup
```bash
# Remove unused images
make clean

# Full cleanup
make clean-all

# System cleanup
docker system prune -a
```

### Monitoring
- Container resource usage
- Health check status
- Log analysis
- Security scan results

## Best Practices

### Development
- Use development compose profile
- Mount source code for live reload
- Use tagged versions in production
- Regular dependency updates

### Production
- Use specific image tags
- Implement proper secrets management
- Regular security scanning
- Resource monitoring and limits
- Backup configuration and data

### CI/CD
- Multi-stage security scanning
- Automated testing pipeline
- Vulnerability assessments
- Registry security policies

## Support

For issues and questions:
1. Check health check output
2. Review container logs
3. Validate configuration
4. Consult mgit documentation
5. Open GitHub issue with container details
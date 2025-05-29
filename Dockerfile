# Multi-stage Dockerfile for mgit CLI tool
# Security-focused with minimal attack surface

# Build stage - Install dependencies and build the application
FROM python:3.11-slim as builder

# Set build arguments
ARG MGIT_VERSION=0.2.1
ARG BUILD_DATE
ARG VCS_REF

# Add labels for metadata
LABEL org.opencontainers.image.title="mgit" \
      org.opencontainers.image.description="Multi-provider Git management tool" \
      org.opencontainers.image.version="${MGIT_VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.authors="Steve Antonakakis <steve.antonakakis@gmail.com>" \
      org.opencontainers.image.source="https://github.com/steveant/mgit"

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for building
RUN groupadd -r mgit && useradd -r -g mgit mgit

# Set working directory
WORKDIR /app

# Copy dependency files first (for better caching)
COPY pyproject.toml README.md ./
COPY --chown=mgit:mgit setup.py ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir build

# Copy application source code
COPY --chown=mgit:mgit . .

# Build the application
RUN python -m build --wheel && \
    pip install --no-cache-dir dist/*.whl

# Verify installation
RUN python -m mgit --version

# Runtime stage - Minimal production image
FROM python:3.11-slim as runtime

# Set runtime arguments
ARG MGIT_VERSION=0.2.1
ARG BUILD_DATE
ARG VCS_REF

# Add runtime labels
LABEL org.opencontainers.image.title="mgit" \
      org.opencontainers.image.description="Multi-provider Git management tool" \
      org.opencontainers.image.version="${MGIT_VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.licenses="MIT"

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user and groups
RUN groupadd -r -g 1001 mgit && \
    useradd -r -u 1001 -g mgit -d /home/mgit -s /bin/bash mgit && \
    mkdir -p /home/mgit/.mgit /app/data && \
    chown -R mgit:mgit /home/mgit /app

# Set working directory
WORKDIR /app

# Copy built application from builder stage
COPY --from=builder --chown=mgit:mgit /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=mgit:mgit /usr/local/bin/mgit /usr/local/bin/mgit

# Copy entrypoint and health check scripts
COPY --chown=mgit:mgit docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chown=mgit:mgit docker/healthcheck.sh /usr/local/bin/healthcheck.sh

# Make scripts executable
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh

# Set up configuration directory
ENV MGIT_CONFIG_DIR=/home/mgit/.mgit \
    MGIT_DATA_DIR=/app/data \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create directories with proper permissions
RUN mkdir -p ${MGIT_CONFIG_DIR} ${MGIT_DATA_DIR} && \
    chown -R mgit:mgit ${MGIT_CONFIG_DIR} ${MGIT_DATA_DIR}

# Set read-only filesystem for security (except specific writable directories)
VOLUME ["${MGIT_CONFIG_DIR}", "${MGIT_DATA_DIR}"]

# Switch to non-root user
USER mgit

# Expose no ports (CLI tool)
# EXPOSE statement intentionally omitted

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command
CMD ["--help"]
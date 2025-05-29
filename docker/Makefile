# Makefile for mgit Docker operations
# Provides convenient commands for building, running, and managing containers

# Configuration
IMAGE_NAME := mgit
IMAGE_TAG := $(shell grep 'version = ' pyproject.toml | cut -d'"' -f2)
BUILD_DATE := $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF := $(shell git rev-parse HEAD 2>/dev/null || echo "unknown")

# Docker configuration
DOCKER_REPO := mgit
DOCKERFILE := Dockerfile
DOCKER_CONTEXT := .

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help build build-dev run run-dev test clean push security-scan lint check-deps stop logs shell

# Default target
help: ## Show this help message
	@echo "mgit Docker Management"
	@echo "====================="
	@echo
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Build targets
build: ## Build the production Docker image
	@echo -e "$(GREEN)Building production image...$(NC)"
	docker build \
		--build-arg BUILD_DATE="$(BUILD_DATE)" \
		--build-arg VCS_REF="$(VCS_REF)" \
		--build-arg MGIT_VERSION="$(IMAGE_TAG)" \
		--tag $(IMAGE_NAME):$(IMAGE_TAG) \
		--tag $(IMAGE_NAME):latest \
		--file $(DOCKERFILE) \
		$(DOCKER_CONTEXT)
	@echo -e "$(GREEN)Build complete: $(IMAGE_NAME):$(IMAGE_TAG)$(NC)"

build-dev: ## Build the development Docker image
	@echo -e "$(GREEN)Building development image...$(NC)"
	docker build \
		--build-arg BUILD_DATE="$(BUILD_DATE)" \
		--build-arg VCS_REF="$(VCS_REF)" \
		--build-arg MGIT_VERSION="$(IMAGE_TAG)" \
		--target builder \
		--tag $(IMAGE_NAME):dev-$(IMAGE_TAG) \
		--tag $(IMAGE_NAME):dev-latest \
		--file $(DOCKERFILE) \
		$(DOCKER_CONTEXT)
	@echo -e "$(GREEN)Development build complete: $(IMAGE_NAME):dev-$(IMAGE_TAG)$(NC)"

# Run targets
run: ## Run the production container
	@echo -e "$(GREEN)Running production container...$(NC)"
	docker-compose up mgit

run-dev: ## Run the development container
	@echo -e "$(GREEN)Running development container...$(NC)"
	docker-compose --profile dev up mgit-dev

run-detached: ## Run the production container in background
	@echo -e "$(GREEN)Running production container in background...$(NC)"
	docker-compose up -d mgit

# Testing and validation
test: ## Run tests in container
	@echo -e "$(GREEN)Running tests...$(NC)"
	docker run --rm $(IMAGE_NAME):$(IMAGE_TAG) --version
	docker run --rm $(IMAGE_NAME):$(IMAGE_TAG) --help
	@echo -e "$(GREEN)Basic tests passed$(NC)"

health-check: ## Check container health
	@echo -e "$(GREEN)Checking container health...$(NC)"
	docker run --rm $(IMAGE_NAME):$(IMAGE_TAG) /usr/local/bin/healthcheck.sh

security-scan: ## Run security scan on the image
	@echo -e "$(GREEN)Running security scan...$(NC)"
	@if command -v trivy >/dev/null 2>&1; then \
		trivy image $(IMAGE_NAME):$(IMAGE_TAG); \
	else \
		echo -e "$(YELLOW)Trivy not installed. Install with: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh$(NC)"; \
	fi

lint-docker: ## Lint Dockerfile
	@echo -e "$(GREEN)Linting Dockerfile...$(NC)"
	@if command -v hadolint >/dev/null 2>&1; then \
		hadolint $(DOCKERFILE); \
	else \
		echo -e "$(YELLOW)Hadolint not installed. Install from: https://github.com/hadolint/hadolint$(NC)"; \
	fi

# Container management
stop: ## Stop all running containers
	@echo -e "$(GREEN)Stopping containers...$(NC)"
	docker-compose down

logs: ## Show container logs
	docker-compose logs -f mgit

logs-dev: ## Show development container logs
	docker-compose logs -f mgit-dev

shell: ## Open shell in production container
	@echo -e "$(GREEN)Opening shell in production container...$(NC)"
	docker run --rm -it \
		--entrypoint /bin/bash \
		$(IMAGE_NAME):$(IMAGE_TAG)

shell-dev: ## Open shell in development container
	@echo -e "$(GREEN)Opening shell in development container...$(NC)"
	docker-compose exec mgit-dev /bin/bash

# Cleanup targets
clean: ## Remove built images and containers
	@echo -e "$(GREEN)Cleaning up...$(NC)"
	docker-compose down --volumes --remove-orphans
	docker image rm $(IMAGE_NAME):$(IMAGE_TAG) $(IMAGE_NAME):latest 2>/dev/null || true
	docker image rm $(IMAGE_NAME):dev-$(IMAGE_TAG) $(IMAGE_NAME):dev-latest 2>/dev/null || true
	docker system prune -f

clean-all: ## Remove everything (images, containers, volumes)
	@echo -e "$(RED)WARNING: This will remove ALL mgit containers, images, and volumes$(NC)"
	@echo -e "$(YELLOW)Continue? [y/N]$(NC)" && read ans && [ $${ans:-N} = y ]
	docker-compose down --volumes --remove-orphans
	docker image rm $$(docker images $(IMAGE_NAME) -q) 2>/dev/null || true
	docker volume rm $$(docker volume ls -q | grep mgit) 2>/dev/null || true

# Registry operations
push: ## Push image to registry
	@echo -e "$(GREEN)Pushing to registry...$(NC)"
	docker push $(DOCKER_REPO)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push $(DOCKER_REPO)/$(IMAGE_NAME):latest

# Development helpers
check-deps: ## Check if required tools are installed
	@echo -e "$(GREEN)Checking dependencies...$(NC)"
	@command -v docker >/dev/null 2>&1 || { echo -e "$(RED)Docker is not installed$(NC)"; exit 1; }
	@command -v docker-compose >/dev/null 2>&1 || { echo -e "$(RED)Docker Compose is not installed$(NC)"; exit 1; }
	@echo -e "$(GREEN)All required dependencies are installed$(NC)"

info: ## Show image information
	@echo -e "$(GREEN)Image Information:$(NC)"
	@echo "Image Name: $(IMAGE_NAME)"
	@echo "Image Tag: $(IMAGE_TAG)"
	@echo "Build Date: $(BUILD_DATE)"
	@echo "VCS Ref: $(VCS_REF)"
	@echo "Dockerfile: $(DOCKERFILE)"
	@echo
	@docker images $(IMAGE_NAME) 2>/dev/null | head -n 5 || echo "No images found"

# Complete workflow
all: check-deps build test ## Run complete build and test workflow
	@echo -e "$(GREEN)Complete workflow finished successfully$(NC)"

dev-setup: check-deps build-dev ## Set up development environment
	@echo -e "$(GREEN)Development environment ready$(NC)"
	@echo "Run 'make run-dev' to start development container"
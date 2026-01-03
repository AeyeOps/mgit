.PHONY: help test test-e2e lint format build build-linux build-windows build-install install clean version test-binary

# Show this help menu
help:
	@uv run python scripts/make.py

# Run pytest test suite
test:
	@uv run python scripts/make.py test $(ARGS)

# Run e2e tests against real provider APIs
test-e2e:
	@uv run python scripts/make.py test-e2e $(ARGS)

# Test the standalone binary with real network calls
test-binary:
	@uv run python scripts/make.py test-binary $(ARGS)

# Run ruff linter to check code quality
lint:
	@uv run python scripts/make.py lint $(ARGS)

# Run ruff formatter on codebase
format:
	@uv run python scripts/make.py format $(ARGS)

# Build standalone executable (default target)
build:
	@uv run python scripts/make.py build $(ARGS)

# Build Linux standalone binary
build-linux:
	@uv run python scripts/make_build.py --target linux --install

# Build Windows standalone binary
build-windows:
	@uv run python scripts/make_build.py --target windows

# Build Linux binary and install to /opt/bin/mgit
build-install:
	@uv run python scripts/make_build.py --target linux --install

# Alias for build-install
install: build-install

# Remove build artifacts and caches
clean:
	@uv run python scripts/make.py clean

# Bump project version (use ARGS="--bump patch|minor|major")
version:
	@if [ -z "$(ARGS)" ]; then \
		echo "Usage: make version ARGS=\"--bump patch|minor|major\""; \
	else \
		uv run python scripts/make.py version $(ARGS); \
	fi

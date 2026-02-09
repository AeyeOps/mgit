.PHONY: help validate test test-standalone-linux test-flat-layout-e2e build-standalone-linux build-standalone-windows clean version release install-hooks

# Show this help menu
help:
	@uv run python scripts/make.py

# Run all validation: format + lint + ty + bandit
validate:
	@uv run python scripts/make_validate.py $(ARGS)

# Run pytest test suite (all tests including e2e)
test:
	@uv run python scripts/make_test.py $(ARGS)

# Test the standalone Linux binary with real network calls
test-standalone-linux:
	@uv run python scripts/test_binary.py $(ARGS)
	@uv run python scripts/make_test_flat_layout_e2e.py $(ARGS)

# Test flat layout E2E with standalone binary
test-flat-layout-e2e:
	@uv run python scripts/make_test_flat_layout_e2e.py $(ARGS)

# Build Linux standalone binary and install to /usr/local/bin
build-standalone-linux:
	@uv run python scripts/make_build.py --target linux --install $(ARGS)

# Build Windows standalone binary
build-standalone-windows:
	@uv run python scripts/make_build.py --target windows $(ARGS)

# Install git pre-commit hook (ruff format + lint on staged files)
install-hooks:
	@cp scripts/pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed."

# Remove build artifacts and caches
clean:
	@uv run python scripts/make_clean.py

# Bump project version (use ARGS="--bump patch|minor|major") — runs validate first
version:
	@if [ -z "$(ARGS)" ]; then \
		echo "Usage: make version ARGS=\"--bump patch|minor|major\""; \
	else \
		uv run python scripts/make_version.py $(ARGS); \
	fi

# Validate, bump version, commit, and push (use ARGS="--bump patch|minor|major")
release:
	@if [ -z "$(ARGS)" ]; then \
		echo "Usage: make release ARGS=\"--bump patch|minor|major\""; \
	else \
		uv run python scripts/make_version.py $(ARGS) && \
		git add -A && \
		git commit -m "chore(release): bump version to $$(grep -m1 '^version' pyproject.toml | sed 's/.*\"\(.*\)\".*/\1/')" && \
		git push; \
	fi

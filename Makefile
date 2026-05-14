.PHONY: help validate test test-standalone-linux test-standalone-macos test-flat-layout-e2e build-standalone-linux build-standalone-macos install-standalone-linux install-standalone-macos build-standalone-windows clean version release install-hooks

BUILD_ARGS ?= $(ARGS)

# Show this help menu
help:
	@uv run python scripts/make.py

# Run all validation: format + lint + ty + bandit + dependency audit
validate:
	@uv run python scripts/make_validate.py $(ARGS)

# Run pytest test suite (all tests including e2e)
test:
	@uv run python scripts/make_test.py $(ARGS)

test-standalone-linux: BUILD_ARGS :=
# Validate, build, and test a fresh standalone Linux binary
test-standalone-linux: build-standalone-linux
	@uv run python scripts/test_binary.py --binary dist/mgit $(ARGS)

# Test flat layout E2E with standalone binary
test-flat-layout-e2e:
	@uv run python scripts/make_test_flat_layout_e2e.py $(ARGS)

# Validate and build Linux standalone binary
build-standalone-linux: validate
	@uv run python scripts/make_build.py --target linux $(BUILD_ARGS)

# Validate, build, test, and install Linux standalone binary to /usr/local/bin
install-standalone-linux: test-standalone-linux
	@INSTALL_TO_OPT_BIN=1 SKIP_BUILD=1 bash scripts/build_mac_and_linux.sh

test-standalone-macos: BUILD_ARGS :=
# Validate, build, and test a fresh standalone macOS binary
test-standalone-macos: build-standalone-macos
	@uv run python scripts/test_binary.py --binary dist/mgit $(ARGS)
	@file dist/mgit | grep -qE 'Mach-O.*(arm64|x86_64)' || (echo "ERROR: dist/mgit is not a Mach-O binary"; exit 1)

# Validate and build macOS standalone binary
build-standalone-macos: validate
	@uv run python scripts/make_build.py --target macos $(BUILD_ARGS)

# Validate, build, test, and install macOS standalone binary to ~/.local/bin
install-standalone-macos: test-standalone-macos
	@INSTALL_TO_OPT_BIN=1 INSTALL_DIR="$$HOME/.local/bin" SKIP_BUILD=1 bash scripts/build_mac_and_linux.sh

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

# Validate, bump version, run standalone build/test/install chain, commit, and push (use ARGS="--bump patch|minor|major")
release:
	@if [ -z "$(ARGS)" ]; then \
		echo "Usage: make release ARGS=\"--bump patch|minor|major\""; \
	else \
		uv run python scripts/make_version.py $(ARGS) && \
		if [ "$$(uname -s)" = "Darwin" ]; then \
			$(MAKE) install-standalone-macos ARGS=; \
		else \
			$(MAKE) install-standalone-linux ARGS=; \
		fi && \
		git add -A && \
		git commit -m "chore(release): bump version to $$(grep -m1 '^version' pyproject.toml | sed 's/.*\"\(.*\)\".*/\1/')" && \
		git push; \
	fi

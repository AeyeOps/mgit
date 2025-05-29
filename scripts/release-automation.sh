#!/bin/bash
# mgit Release Automation Script
# Automates version bumping, changelog generation, and release preparation

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
RELEASE_TYPE="${MGIT_RELEASE_TYPE:-patch}"
VERSION="${MGIT_RELEASE_VERSION:-}"
DRY_RUN="${MGIT_RELEASE_DRY_RUN:-false}"
SKIP_TESTS="${MGIT_RELEASE_SKIP_TESTS:-false}"
SKIP_BUILD="${MGIT_RELEASE_SKIP_BUILD:-false}"
BRANCH="${MGIT_RELEASE_BRANCH:-main}"

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
mgit Release Automation Script

Usage: $0 [OPTIONS]

OPTIONS:
    -t, --type TYPE          Release type (major, minor, patch) [default: patch]
    -v, --version VERSION    Specific version to release (overrides type)
    -d, --dry-run           Perform dry run without making changes
    -s, --skip-tests        Skip running tests before release
    -b, --skip-build        Skip building packages
    -r, --branch BRANCH     Release branch [default: main]
    -h, --help              Show this help message

RELEASE TYPES:
    major    Increment major version (X.0.0)
    minor    Increment minor version (0.X.0)
    patch    Increment patch version (0.0.X)

EXAMPLES:
    # Create a patch release
    $0 --type patch

    # Create a minor release
    $0 --type minor

    # Create a specific version release
    $0 --version 2.1.0

    # Dry run release
    $0 --dry-run --type minor

ENVIRONMENT VARIABLES:
    MGIT_RELEASE_TYPE        Default release type
    MGIT_RELEASE_VERSION     Specific version to release
    MGIT_RELEASE_DRY_RUN     Default dry run setting
    MGIT_RELEASE_SKIP_TESTS  Skip tests
    MGIT_RELEASE_SKIP_BUILD  Skip build
    MGIT_RELEASE_BRANCH      Release branch

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--type)
                RELEASE_TYPE="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN="true"
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS="true"
                shift
                ;;
            -b|--skip-build)
                SKIP_BUILD="true"
                shift
                ;;
            -r|--branch)
                BRANCH="$2"
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

# Validate configuration
validate_config() {
    log_info "Validating release configuration..."

    # Validate release type
    if [[ ! "$RELEASE_TYPE" =~ ^(major|minor|patch)$ ]]; then
        log_error "Invalid release type: $RELEASE_TYPE. Must be 'major', 'minor', or 'patch'"
        exit 1
    fi

    # Validate version format if specified
    if [[ -n "$VERSION" && ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+(\.[0-9]+)?)?$ ]]; then
        log_error "Invalid version format: $VERSION"
        exit 1
    fi

    # Check if we're on the right branch
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [[ "$current_branch" != "$BRANCH" ]]; then
        log_error "Not on release branch. Current: $current_branch, Expected: $BRANCH"
        exit 1
    fi

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        log_error "Working directory has uncommitted changes"
        exit 1
    fi

    log_success "Configuration validation passed"
}

# Get current version from pyproject.toml
get_current_version() {
    if [[ -f "$PROJECT_ROOT/pyproject.toml" ]]; then
        grep '^version = ' "$PROJECT_ROOT/pyproject.toml" | sed 's/version = "\([^"]*\)"/\1/'
    else
        echo "0.0.0"
    fi
}

# Calculate next version
calculate_next_version() {
    if [[ -n "$VERSION" ]]; then
        echo "$VERSION"
        return 0
    fi

    local current_version
    current_version=$(get_current_version)
    
    # Remove any pre-release suffix
    current_version=$(echo "$current_version" | sed 's/-.*$//')
    
    local major minor patch
    IFS='.' read -ra VERSION_PARTS <<< "$current_version"
    major=${VERSION_PARTS[0]}
    minor=${VERSION_PARTS[1]}
    patch=${VERSION_PARTS[2]}

    case "$RELEASE_TYPE" in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
    esac

    echo "$major.$minor.$patch"
}

# Update version in files
update_version() {
    local new_version="$1"
    log_info "Updating version to $new_version"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would update version to $new_version"
        return 0
    fi

    # Update pyproject.toml
    if [[ -f "$PROJECT_ROOT/pyproject.toml" ]]; then
        sed -i "s/version = \".*\"/version = \"$new_version\"/" "$PROJECT_ROOT/pyproject.toml"
        log_info "Updated pyproject.toml"
    fi

    # Update __init__.py if it exists
    if [[ -f "$PROJECT_ROOT/mgit/__init__.py" ]]; then
        sed -i "s/__version__ = \".*\"/__version__ = \"$new_version\"/" "$PROJECT_ROOT/mgit/__init__.py"
        log_info "Updated mgit/__init__.py"
    fi

    # Update constants.py if it exists
    if [[ -f "$PROJECT_ROOT/mgit/constants.py" ]]; then
        sed -i "s/__version__ = \".*\"/__version__ = \"$new_version\"/" "$PROJECT_ROOT/mgit/constants.py"
        log_info "Updated mgit/constants.py"
    fi

    log_success "Version updated to $new_version"
}

# Generate changelog
generate_changelog() {
    local new_version="$1"
    local current_version
    current_version=$(get_current_version)
    
    log_info "Generating changelog for $new_version"

    local changelog_file="$PROJECT_ROOT/CHANGELOG.md"
    local temp_changelog=$(mktemp)

    # Get commit range
    local commit_range
    if git tag -l | grep -q "^v$current_version$"; then
        commit_range="v$current_version..HEAD"
    else
        # If no tag exists, get all commits
        commit_range="HEAD"
    fi

    # Generate changelog entry
    cat > "$temp_changelog" << EOF
# Changelog

## [$new_version] - $(date +%Y-%m-%d)

### Added
$(git log $commit_range --pretty=format:"- %s" --grep="feat\|add" | head -10)

### Changed
$(git log $commit_range --pretty=format:"- %s" --grep="change\|update\|improve" | head -10)

### Fixed
$(git log $commit_range --pretty=format:"- %s" --grep="fix\|bug" | head -10)

### Removed
$(git log $commit_range --pretty=format:"- %s" --grep="remove\|delete" | head -5)

### Security
$(git log $commit_range --pretty=format:"- %s" --grep="security\|vuln" | head -5)

EOF

    # Append existing changelog if it exists
    if [[ -f "$changelog_file" ]]; then
        echo "" >> "$temp_changelog"
        tail -n +2 "$changelog_file" >> "$temp_changelog"
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Generated changelog:"
        head -20 "$temp_changelog"
        rm "$temp_changelog"
        return 0
    fi

    # Clean up empty sections
    sed -i '/^### [A-Za-z]*$/N;/^### [A-Za-z]*\n$/d' "$temp_changelog"
    
    mv "$temp_changelog" "$changelog_file"
    log_success "Changelog updated"
}

# Run tests
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "Skipping tests"
        return 0
    fi

    log_info "Running test suite..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would run test suite"
        return 0
    fi

    cd "$PROJECT_ROOT"

    # Install development dependencies
    if [[ -f "pyproject.toml" ]]; then
        pip install -e ".[dev]" || {
            log_error "Failed to install development dependencies"
            exit 1
        }
    fi

    # Run tests
    if command -v pytest &> /dev/null; then
        pytest tests/ -v || {
            log_error "Tests failed"
            exit 1
        }
    else
        python -m unittest discover tests/ || {
            log_error "Tests failed"
            exit 1
        }
    fi

    log_success "All tests passed"
}

# Build packages
build_packages() {
    if [[ "$SKIP_BUILD" == "true" ]]; then
        log_warning "Skipping package build"
        return 0
    fi

    log_info "Building packages..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would build packages"
        return 0
    fi

    cd "$PROJECT_ROOT"

    # Install build dependencies
    pip install build twine || {
        log_error "Failed to install build dependencies"
        exit 1
    }

    # Clean previous builds
    rm -rf build/ dist/ *.egg-info/

    # Build packages
    python -m build || {
        log_error "Package build failed"
        exit 1
    }

    # Verify packages
    python -m twine check dist/* || {
        log_error "Package verification failed"
        exit 1
    }

    log_success "Packages built successfully"
}

# Create git tag and commit
create_release_commit() {
    local new_version="$1"
    
    log_info "Creating release commit and tag..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would create commit and tag for v$new_version"
        return 0
    fi

    cd "$PROJECT_ROOT"

    # Add changed files
    git add pyproject.toml CHANGELOG.md mgit/__init__.py mgit/constants.py 2>/dev/null || true

    # Create release commit
    git commit -m "chore: release v$new_version

- Update version to $new_version
- Update changelog
- Prepare for release

🤖 Generated with mgit release automation" || {
        log_error "Failed to create release commit"
        exit 1
    }

    # Create annotated tag
    git tag -a "v$new_version" -m "Release v$new_version

$(head -20 CHANGELOG.md | tail -15)

🤖 Generated with mgit release automation" || {
        log_error "Failed to create release tag"
        exit 1
    }

    log_success "Release commit and tag created"
}

# Push changes
push_release() {
    local new_version="$1"
    
    log_info "Pushing release..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would push commit and tag for v$new_version"
        return 0
    fi

    cd "$PROJECT_ROOT"

    # Push commit
    git push origin "$BRANCH" || {
        log_error "Failed to push release commit"
        exit 1
    }

    # Push tag
    git push origin "v$new_version" || {
        log_error "Failed to push release tag"
        exit 1
    }

    log_success "Release pushed to remote"
}

# Generate release notes
generate_release_notes() {
    local new_version="$1"
    local release_notes_file="$PROJECT_ROOT/RELEASE_NOTES_v$new_version.md"

    log_info "Generating release notes..."

    cat > "$release_notes_file" << EOF
# Release Notes - mgit v$new_version

## Summary
This release includes the following changes and improvements to mgit.

## Installation

### PyPI
\`\`\`bash
pip install mgit==$new_version
\`\`\`

### Docker
\`\`\`bash
docker pull ghcr.io/steveant/mgit:$new_version
\`\`\`

### Binary Releases
Download from the [releases page](https://github.com/steveant/mgit/releases/tag/v$new_version).

## What's Changed

$(head -30 CHANGELOG.md | tail -25)

## Upgrade Notes

### Breaking Changes
- None in this release

### Deprecations
- None in this release

### Migration Guide
No migration required for this release.

## Verification

To verify the release:

\`\`\`bash
# Check version
mgit --version

# Verify functionality
mgit --help
\`\`\`

## Support

- 📖 [Documentation](https://github.com/steveant/mgit/blob/main/README.md)
- 🐛 [Issues](https://github.com/steveant/mgit/issues)
- 💬 [Discussions](https://github.com/steveant/mgit/discussions)

---

**Full Changelog**: https://github.com/steveant/mgit/compare/v$(get_current_version)...v$new_version
EOF

    if [[ "$DRY_RUN" != "true" ]]; then
        log_success "Release notes generated: $release_notes_file"
    else
        log_info "DRY RUN: Would generate release notes"
        rm -f "$release_notes_file"
    fi
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Release automation failed with exit code $exit_code"
        log_info "You may need to manually clean up any partial changes"
    fi
    exit $exit_code
}

# Main release function
main() {
    trap cleanup EXIT

    log_info "Starting mgit release automation..."

    parse_args "$@"
    validate_config

    local current_version new_version
    current_version=$(get_current_version)
    new_version=$(calculate_next_version)

    log_info "Current version: $current_version"
    log_info "New version: $new_version"
    log_info "Release type: $RELEASE_TYPE"
    log_info "Branch: $BRANCH"
    log_info "Dry run: $DRY_RUN"

    # Confirm release in production
    if [[ "$DRY_RUN" != "true" ]]; then
        echo -e "${YELLOW}Are you ready to release v$new_version? (yes/no):${NC}"
        read -r confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Release cancelled by user"
            exit 0
        fi
    fi

    # Execute release steps
    run_tests
    update_version "$new_version"
    generate_changelog "$new_version"
    build_packages
    create_release_commit "$new_version"
    generate_release_notes "$new_version"
    
    if [[ "$DRY_RUN" != "true" ]]; then
        push_release "$new_version"
        
        log_success "Release v$new_version completed successfully!"
        log_info "Next steps:"
        log_info "1. Monitor the GitHub Actions release workflow"
        log_info "2. Verify Docker images are published"
        log_info "3. Check PyPI package is available"
        log_info "4. Update documentation if needed"
    else
        log_success "Dry run completed successfully!"
        log_info "No changes were made to the repository"
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
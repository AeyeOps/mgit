# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2025-09-02

### Added
- **Sync Command**: New `sync` command for unified repository management
- **Pattern Matching Enhancements**: Improved multi-provider pattern matching
- **Security Updates**: Enhanced credential management and token handling

### Changed
- **Version Management**: Updated version synchronization across all files
- **Configuration**: Improved provider configuration handling
- **Documentation**: Updated README and version references

### Fixed
- **GitHub Token Management**: Improved token unset/clear functionality
- **Provider Authentication**: Enhanced authentication flow for all providers

## [0.4.9] - 2025-08-01

### Added
- **Multi-Provider Pattern Matching**: Revolutionary wildcard discovery across all configured providers
  - Pattern matching on leftmost query segment (e.g., `*/*/*`, `*abc/*/*`, `GITHUB*/*/*`)
  - Case-insensitive glob pattern matching with `*` and `?` wildcards
  - Concurrent processing of multiple providers with progress reporting
  - Extended to all bulk operations: `list`, `clone-all`, and `pull-all`
- **CLI Validation**: Prevents contradictory usage of wildcard patterns with explicit provider flags
  - Clear error messages guide users to correct usage patterns
  - Validates query consistency across all commands

### Changed
- **Directory Structure**: Standardized hierarchical directory structure (host/org/project/repo) for all operations
  - Removed `--hierarchical` flag from clone-all (now default behavior)
  - Consistent path structure across clone-all and pull-all operations
- **Bulk Operations Architecture**: Enhanced to support multi-provider workflows
  - `clone-all` and `pull-all` now support multi-provider pattern matching
  - Automatic detection of multi-provider patterns vs single-provider operations
  - Improved error handling and progress reporting across provider boundaries

### Removed
- **Hierarchical Flag**: Removed `--hierarchical` option from clone-all command
  - Hierarchical structure is now the default and only option
  - Simplifies CLI interface and ensures consistent behavior

### Fixed
- **Provider Discovery**: Multi-provider discovery now searches across all configured providers
  - Previously wildcard patterns only searched default provider
  - Now properly matches provider names using case-insensitive glob patterns
- **Query Validation**: Added comprehensive validation to prevent contradictory command usage
  - Blocks combining wildcard discovery (`*/*/*`) with explicit provider flags (`--provider`)
  - Provides helpful error messages with correct usage examples

## [0.4.5] - 2025-01-24

### Fixed
- Fixed GitHub Actions multiline output parsing by using artifacts
- Release notes are now passed via artifact upload/download
- Eliminated all output delimiter issues

## [0.4.4] - 2025-01-24

### Fixed
- Resolved YAML parsing issues with heredoc stdin syntax
- Used proper Python script execution in GitHub Actions

## [0.4.3] - 2025-01-24

### Fixed
- Fixed heredoc delimiter conflicts in workflow file
- Used unique delimiters to prevent parsing errors

## [0.4.2] - 2025-01-24

### Fixed
- Resolved GitHub Actions output parsing error for AI release notes generation
- Changed to file-based approach to avoid stdout interference
- Improved error handling for AI generation failures

## [0.4.1] - 2025-01-24

### Fixed
- Fixed variable expansion in release workflow
- Corrected import ordering and removed unused imports
- Adjusted Bandit security threshold
- Fixed Black formatting issues

## [0.4.0] - 2025-01-24

### Added
- Automated release workflow triggered by version changes in `pyproject.toml`
- AI-powered release notes generation using OpenAI API
- Quality and security checks in release pipeline (Black, Ruff, Bandit)
- Helper script for version updates (`scripts/update_version.py`)

### Changed
- **Version Management**: Consolidated version source to `pyproject.toml` only (removed duplicate in `constants.py`)
- **Workflow Simplification**: Removed unnecessary CI workflows, keeping only auto-release
- **Release Process**: Simplified from complex multi-job workflow to single automated flow

### Removed
- Excessive CI/CD workflows (`ci.yml`, `claude.yml`, `claude-code-review.yml`, `validate-version.yml`)
- Version constant from `mgit/constants.py` (now read from `pyproject.toml` at runtime)
- Sensitive files from git history (`ABSOLUTE_FINAL_VERIFICATION.md`, `SECURITY_INCIDENT_REPORT.md`)
- Four problematic auto-generated PRs (#131-134) with excessive changes

### Fixed
- Import statements in `monitoring/server.py` to use package-level `__version__`
- Git history to remove Azure DevOps tokens that were blocking pushes

## [0.3.2] - 2025-01-23

### Added
- Claude Code Review workflow for automated PR reviews
- Claude PR Assistant workflow for enhanced GitHub Actions automation
- Comprehensive end-to-end test suite for mgit CLI functionality

### Changed
- Enhanced Azure DevOps project parsing with synchronous method for improved reliability
- Unified provider configuration structure with complete legacy field name elimination
- Improved documentation for testing procedures and removed obsolete configuration files

### Removed
- Obsolete provider test scripts and configuration files
- Deprecated generate_env command functionality
- Legacy manager components replaced with unified structure

### Fixed
- Repository listing now uses synchronous method for more stable Azure DevOps operations
- Provider configuration field mapping now handles all legacy scenarios consistently

## [0.2.9] - 2025-06-01

### Added
- Enhanced AI-powered release notes generation with richer 80s pop culture references
- Structured release notes format with emojis and sections

### Fixed
- Restored full GenAI release content generation system
- Fixed workflow issues preventing automated releases

## [0.2.2] - 2025-05-30

### Changed
- **Documentation Overhaul**: Massive cleanup and reorganization of project documentation
  - Consolidated installation instructions into README.md
  - Added comprehensive 80s-themed configuration reference table
  - Removed 62+ transitional development artifacts
  - Streamlined root directory from 40+ files to 10 essential files
- **Improved Configuration Documentation**: Added clear dual-configuration system explanation
  - Environment variables vs config file precedence clearly documented
  - Complete reference table showing all configuration options
  - Fixed incorrect MGIT_ prefix references in migration guide
- **Project Structure**: Cleaned and organized for professional release
  - Removed unnecessary Docker orchestration files (kept only essential Dockerfile)
  - Archived all MAWEP sprint artifacts and internal development docs
  - Removed test artifacts and development scripts from root

### Removed
- Redundant installation documentation files (INSTALLATION_GUIDE.md, INSTALLATION_FROM_GITHUB.md)
- Docker Compose files and Helm charts (overkill for CLI tool)
- Development/release automation scripts (moved to archive)
- MAWEP workspace and sprint management artifacts
- Test environment and artifacts from root directory
- Migration guide for v0.2.0 to v0.2.1 (historical)
- Internal demo/example scripts with mock credentials

### Fixed
- Configuration documentation now correctly shows actual environment variable names
- Simplified .gitignore from 189 lines to 58 lines (removed irrelevant entries)
- README.md broken links to archived documentation

## [0.2.1] - 2025-01-29

### Added
- **Multi-Provider Support**: Complete transformation from Azure DevOps-only to multi-provider architecture
  - Full GitHub provider implementation with organization and user repository support
  - Complete BitBucket provider implementation with workspace management
  - Provider auto-detection from URLs for seamless workflow
  - Feature parity across all providers (login, clone-all, pull-all, config)
- **Provider Registry System**: Dynamic provider registration and discovery
- **Unified Authentication**: Consistent credential management across all providers
  - Azure DevOps: Personal Access Token (PAT)
  - GitHub: Personal Access Token
  - BitBucket: App Password
- **Enhanced Update Modes**: Support for skip/pull/force modes across all providers
- **Improved Error Handling**: Provider-specific error messages and retry logic
- **Rich Console Output**: Enhanced progress indicators for multi-provider operations
- **Comprehensive Documentation**: Complete docs for architecture, configuration, and CLI design

### Changed
- **Architecture Overhaul**: Refactored from monolithic to modular provider-based architecture
  - Abstract base provider class for consistent interface
  - Provider factory pattern for dynamic instantiation
  - Separated git operations from provider-specific logic
- **Configuration System**: Extended to support provider-specific settings
  - Provider-specific authentication storage
  - Per-provider concurrency settings
  - Hierarchical configuration (env vars → config file → defaults)
- **CLI Structure**: Reorganized commands for provider flexibility
  - Auto-detection of provider from URLs
  - Explicit provider specification with `--provider` flag
  - Consistent command interface across all providers
- **Project Rename**: Renamed from `ado-cli` to `mgit` to reflect multi-platform support
- **Package Structure**: Modernized with proper module separation
  - Dedicated modules for CLI, config, git, providers, and utilities
  - Clean dependency hierarchy to prevent circular imports

### Fixed
- Resolved provider initialization and registration issues
- Fixed provider naming warnings for aliases
- Corrected module import paths for package structure
- Enhanced error messages for authentication failures
- Improved handling of disabled/inaccessible repositories

### Breaking Changes
- **Configuration File Format**: Provider-specific sections now required
  - Old: Single flat configuration
  - New: Provider-scoped configuration sections
- **Environment Variables**: Provider-specific prefixes now used
  - Old: `AZURE_DEVOPS_PAT`
  - New: `MGIT_AZDEVOPS_PAT`, `MGIT_GITHUB_TOKEN`, `MGIT_BITBUCKET_APP_PASSWORD`
- **Login Command**: Now requires provider specification or URL
  - Old: `mgit login --org https://dev.azure.com/myorg --pat TOKEN`
  - New: `mgit login --provider github --pat TOKEN` or auto-detection from URL

### Fixed
- Corrected a Mypy type hint error related to `subprocess.CalledProcessError`.

## [0.2.0] - 2025-04-03

### Changed
- Refactored Azure DevOps interactions to use the `azure-devops` Python SDK instead of relying on the external `az` CLI. This removes the dependency on the Azure CLI being installed.

### Added
- `--version` flag to display the application version.

## [0.1.0] - YYYY-MM-DD

### Added
- Initial release with core functionality:
  - `clone-all`: Clone all repositories from a project.
  - `pull-all`: Pull updates for existing repositories.
  - `login`: Authenticate with Azure DevOps.
  - `config`: Manage global configuration.
  - `generate-env`: Create a sample environment file.
- Support for environment variables and global config file (`~/.config/mgit/config`).
- Concurrent repository operations using `asyncio`.
- Rich console output and logging with PAT masking.
- Handling of existing repositories via `update-mode` (`skip`, `pull`, `force`).

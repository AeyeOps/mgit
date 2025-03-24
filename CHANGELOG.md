# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet.

### Changed
- Nothing yet.

### Deprecated
- Nothing yet.

### Removed
- Nothing yet.

### Fixed
- Nothing yet.

### Security
- Nothing yet.

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
- Support for environment variables and global config file (`~/.config/ado-cli/config`).
- Concurrent repository operations using `asyncio`.
- Rich console output and logging with PAT masking.
- Handling of existing repositories via `update-mode` (`skip`, `pull`, `force`).

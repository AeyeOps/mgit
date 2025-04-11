# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Updated `requirements.txt` to use stable `azure-devops>=7.1.0` after resolving merge conflict.

### Deprecated
- Nothing yet.

### Removed
- Obsolete `pathlib` dependency from `requirements.txt` to resolve `pyinstaller` conflict.

### Fixed
- Resolved `PermissionError` in the bundled executable by changing the log file path to `~/.config/ado-cli/ado-cli.log`.

### Security
- Nothing yet.

## [0.2.1] - 2025-04-11

### Added
- Functionality to build a standalone executable using `pyinstaller`.
- Enhanced progress display using `rich.progress` for `clone-all` and `pull-all`, showing individual repository status.
- Interactive confirmation prompts using `rich.prompt.Confirm` for potentially destructive actions (`clone-all --force`, `login --store`).

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
- Support for environment variables and global config file (`~/.config/ado-cli/config`).
- Concurrent repository operations using `asyncio`.
- Rich console output and logging with PAT masking.
- Handling of existing repositories via `update-mode` (`skip`, `pull`, `force`).

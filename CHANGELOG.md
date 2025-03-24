# Changelog

All notable changes to this project will be documented in this file, following [common-changelog.org](https://common-changelog.org/) guidelines.

## [0.1.0] - 2025-03-23

### Added
- **Global Configuration System**
  - Added support for centralized configuration in `~/.config/ado-cli/config`
  - Added hierarchical configuration lookup: environment → global config → defaults
  - New `config` command to view and manage global settings
  - Added secure storage of credentials with proper permissions

### Changed
- **Configuration Management**
  - Improved configuration handling with better defaults and documentation
  - Enhanced credential management for better security
  - Added support for default concurrency and update mode in global config
  - Renamed `gen-env` command to `generate-env` with detailed documentation support
  - Improved console output formatting for better readability

### Enhanced
- **User Experience**
  - Added automatic help display when running the CLI with no arguments
  - Improved CLI name and description for better clarity
  - Built and packaged as a standalone executable with PyInstaller
  - Added detection and reporting of disabled repositories
  - Fixed handling of repository names with spaces and special characters
  - Enhanced log formatting for better display of long repository names

### Security
- **Improved Credential Handling**
  - Better masking of PAT tokens in display and logs
  - Secure permissions (600) for the config file
  - Improved error messaging for authentication issues

## [0.0.1] - 2025-02-03

### Added
- **Core Commands**  
  - `clone_all` command to clone all repositories in an Azure DevOps project (with concurrency support).  
  - `pull_all` command to update/pull all repositories in a local folder.  
- **Async & Concurrency**  
  - Asynchronous Git operations using `asyncio` and a configurable `--concurrency` option for cloning in parallel.
- **Update Modes**  
  - New `--update-mode` option (`skip`, `pull`, `force`) allows users to choose how to handle existing local folders:
    - `skip`: Leave existing folders untouched.  
    - `pull`: If an existing folder is a valid Git repo, perform `git pull`.  
    - `force`: Remove the folder entirely and clone again from scratch.
- **Environment File Generation**  
  - `gen_env` command to generate a `.env` file with default or existing values.
- **Rich Logging & Progress**  
  - **Rotating log file** (`ado-cli.log`) plus a **Rich** console logger with tracebacks.  
  - Progress bar display (via `rich.progress`) for repository cloning/pulling status.
- **Credential Handling**  
  - Automatic embedding of PAT in repository URLs to avoid repeated credentials prompts for `git clone`.  
  - Masking of the PAT from any logs or console output.

### Changed
- **Logging**  
  - Implemented a custom log formatter that strips out the actual PAT from logs to improve security.
- **Error Handling**  
  - Repositories that fail to clone or pull are no longer fatal; they are captured and summarized at the end.

### Fixed
- No previously documented bugs.

### Security
- **Redacted Personal Access Token (PAT) in logs** to ensure sensitive credentials are not exposed.

### Deprecated
- Nothing deprecated yet in this release.

### Removed
- Nothing removed yet in this release.
 
---

For more details on changes, see the source code or documentation.
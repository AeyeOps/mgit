# Changelog

All notable changes to this project will be documented in this file, following [common-changelog.org](https://common-changelog.org/) guidelines.

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
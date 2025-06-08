# Tech Context

## Core Technologies

*   **Python:** Version `>=3.9,<3.13` as defined in `pyproject.toml`.
    *   **Production Libraries:**
        *   `typer`: For the CLI framework.
        *   `rich`: For enhanced console output, tables, and progress bars.
        *   `ruamel.yaml`: For parsing and writing YAML configuration files while preserving comments.
        *   `aiohttp`: Asynchronous HTTP client, used by providers and the monitoring server.
        *   `azure-devops`: Official SDK for the Azure DevOps API.
        *   `python-dotenv`: For loading environment variables from `.env` files (used for legacy migration).
        *   `pyyaml`: Standard YAML library.
    *   **Development Libraries:**
        *   `pytest`, `pytest-cov`, `pytest-asyncio`, `pytest-benchmark`: For testing.
        *   `black`, `ruff`, `mypy`: For code formatting, linting, and static type checking.
        *   `poethepoet`: As a task runner for development workflows.
        *   `pyinstaller`: For building standalone executables.
        *   `bandit`, `safety`, `pip-audit`: For security analysis and dependency scanning.
        *   `memory-profiler`: For performance and memory analysis.
*   **Git:** The core version control system that `mgit` interacts with on the local machine.
*   **GitHub Actions:** Used for the CI/CD pipeline.

## Development Setup

*   **Prerequisites:**
    *   Python (version 3.9 to 3.12)
    *   Poetry (version >=1.0.0)
    *   Git
*   **Installation Steps:**
    1.  Clone the repository.
    2.  Run `poetry install` to create a virtual environment and install all dependencies.
*   **Running Locally:**
    *   `poetry run mgit --help`
    *   Or, activate the virtual environment with `poetry shell` and then run `mgit --help`.
*   **Running Tests, Formatting, and Linting (via Poe the Poet):**
    *   **Tests:** `poetry run poe test`
    *   **Linting:** `poetry run poe lint`
    *   **Formatting:** `poetry run poe format`

## Code Maturity & Implementation Notes

*   **Azure DevOps Provider:** This is the most mature and feature-complete provider, serving as the reference implementation.
*   **GitHub Provider:** This provider is also mature and fully functional.
*   **Bitbucket Provider:** This provider is functional for core tasks (listing, cloning) but is less complete than the others. It is missing implementations for `get_rate_limit_info`, `get_workspace_permissions`, and `list_repository_branches`.
*   **Advanced `asyncio` Usage:** The application makes advanced use of `asyncio` for high performance, not just for basic API calls. The `AsyncExecutor` provides a reusable framework for managing concurrent batch jobs.
*   **Advanced `rich` Usage:** The application uses `rich` extensively to create a polished user experience, including custom progress bar styles and columns managed by the `ProgressManager`.

## Tool Usage Patterns

*   **Poetry & Poe the Poet:** `poetry` is the single source of truth for dependency management. `poe` is used as a command runner for all common development tasks, ensuring consistency with the CI environment.
*   **Security Validator:** The `SecurityValidator` class is used by providers and other components to validate and sanitize user input, preventing common security vulnerabilities.

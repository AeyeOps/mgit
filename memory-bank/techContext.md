# Tech Context

## Core Technologies

*   **Python:** [Specify version, e.g., 3.9, 3.10, 3.11 - check `pyproject.toml` or CI setup]
    *   Key Libraries:
        *   **Typer:** For CLI argument parsing and command structure.
        *   **Requests (or similar HTTP client like `httpx`):** For API interactions by providers.
        *   **`ruamel.yaml`:** For YAML configuration parsing and writing, preserving comments.
        *   **Poetry:** For dependency management and packaging.
        *   **Black:** For code formatting.
        *   **Ruff:** For linting.
        *   **MyPy:** For static type checking.
        *   **Pytest:** For unit and integration testing.
        *   **`python-dotenv` (if used):** For managing environment variables.
        *   [User to add/verify other significant libraries from `pyproject.toml`]
*   **Git:** Core version control system. `mgit` interacts with local Git installations.
*   **GitHub Actions:** For CI/CD pipeline.
    *   Workflows defined in `.github/workflows/`.
*   **Docker (Optional):** If used for containerization (a `Dockerfile` exists).
    *   [User to specify Docker version and base images if relevant].

## Development Setup

*   **Prerequisites:**
    *   Python [version]
    *   Poetry [version]
    *   Git
*   **Installation Steps:**
    1.  Clone the repository.
    2.  `poetry install` (to install dependencies).
    3.  (Optional) `poetry shell` (to activate the virtual environment).
*   **Running Locally:**
    *   `poetry run python -m mgit --help` or `mgit --help` (if installed/aliased).
*   **Running Tests:**
    *   `poetry run pytest`
    *   `python -m pytest` (if venv is active)
*   **Formatting & Linting:**
    *   `poetry run black .`
    *   `poetry run ruff . --fix`
    *   `poetry run mypy .`

## Technical Constraints

*   [User to list any known technical constraints, e.g., "Must support Python 3.9+", "API rate limits for providers," "Compatibility with specific Git versions"].

## Key Dependencies & Integrations

*   **External APIs:**
    *   GitHub API
    *   Bitbucket API
    *   Azure DevOps API
*   **Local System:**
    *   Git executable
    *   Filesystem for configuration storage (`~/.config/mgit/config.yaml`)
*   **CI/CD:**
    *   GitHub Actions
    *   Codecov (for test coverage, if `Upload coverage to Codecov` step in CI is active)

## Tool Usage Patterns

*   **Poetry:** Used for all dependency management, virtual environment creation, and packaging. See `pyproject.toml` for configuration.
*   **GitHub CLI (`gh`):** Used for interacting with GitHub Actions in the CI pipeline and potentially for local development tasks.
*   [User to describe other specific tool usage patterns].

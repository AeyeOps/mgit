# Active Context: Azure DevOps CLI Tool (ado-cli) - Initialization

## Current Focus

-   Implementing UI/UX enhancements using `rich`.
-   Testing the implemented enhancements.

## Recent Changes

-   Confirmed `ado-cli.py` uses Azure DevOps SDK exclusively.
-   Modified `clone_all` and `pull_all` to display individual repository status updates within the `rich.progress` context.
-   Added `rich.prompt.Confirm` for user confirmation before potentially destructive actions (`clone-all --force` directory removal, `login --store` credential overwrite).
-   Fixed a Mypy type hint error related to `subprocess.CalledProcessError`.

## Next Steps

-   Update `progress.md` and `systemPatterns.md` in the Memory Bank.
-   Test the new progress display and confirmation prompts.
-   Await further instructions or tasks from the user.

## Active Decisions & Considerations

-   The Memory Bank structure is being established according to the standard defined in the custom instructions.
-   The content for the initial Memory Bank files is derived directly from the provided source code and documentation (`README.md`, `ARCHITECTURE.md`, `ado-cli.py`, `requirements.txt`).

## Important Patterns & Preferences (Observed)

-   **Modularity:** Code is organized into classes (`AzDevOpsManager`, `GitManager`).
-   **Asynchronous Programming:** `asyncio` is used for potentially long-running Git operations.
-   **Clear CLI:** `typer` provides a structured command-line interface.
-   **Enhanced UX:** `rich` is used for better console output and progress bars.
-   **Configuration Flexibility:** Supports environment variables, a global config file, and CLI arguments.
-   **Security:** PAT masking in logs is implemented.
-   **SDK Usage:** Leverages the official `azure-devops` SDK.
-   **Interactive Confirmation:** Uses `rich.prompt.Confirm` for safer operations.
-   **Detailed Progress:** Uses `rich.progress` with dynamic task updates for better feedback during concurrent operations.

## Learnings & Insights

-   The tool provides core functionality for bulk cloning and pulling Azure DevOps repositories.
-   Authentication relies heavily on PATs.
-   The architecture appears well-defined, separating concerns.
-   Future improvements are already documented in `ARCHITECTURE.md` (e.g., enhanced error handling, config profiles, testing).
-   **Confirmation:** The script successfully uses the `azure-devops` SDK exclusively for ADO interactions, with no remaining dependencies on the `az` CLI utility.

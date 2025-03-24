# Product Context: Azure DevOps CLI Tool (ado-cli)

## Problem Solved

Managing a large number of Git repositories within Azure DevOps projects can be cumbersome and time-consuming using standard Git commands or the Azure DevOps web UI. Tasks like cloning all repositories for a new team member or ensuring all local repositories are up-to-date require repetitive actions for each repository. This tool addresses the inefficiency and potential for errors in these manual processes.

## How It Works

The `ado-cli` tool provides a command-line interface that interacts with the Azure DevOps API (via the Python SDK) and local Git installations. Users authenticate using an Azure DevOps Personal Access Token (PAT). Key functionalities include:

-   **`clone-all`:** Fetches the list of repositories for a specified project from Azure DevOps and clones each one into a target directory. It handles existing directories based on user-defined modes (`skip`, `pull`, `force`) and skips disabled repositories.
-   **`pull-all`:** Iterates through local directories (expected to be Git repositories cloned previously, likely using `clone-all`) and performs a `git pull` operation for each, updating them to the latest version from the remote.
-   **`login`:** Validates Azure DevOps credentials (organization URL and PAT) and optionally stores them securely in a global configuration file (`~/.config/ado-cli/config`) for future use.
-   **`config`:** Allows viewing and setting global configuration defaults (like organization URL, concurrency level, update mode) to avoid specifying them repeatedly.
-   **`generate-env`:** Creates a sample `.env` file to guide users on setting up environment variables for configuration.

The tool uses asynchronous operations (`asyncio`) to perform network and Git operations concurrently, significantly speeding up bulk tasks. It provides informative console output using the `rich` library, including progress bars for long operations.

## User Experience Goals

-   **Simplicity:** Offer intuitive commands that map directly to common bulk repository management tasks.
-   **Speed:** Provide fast execution times for operations involving many repositories through concurrency.
-   **Clarity:** Give clear feedback on operations, including progress, successes, skips, and failures.
-   **Flexibility:** Support various configuration methods (env vars, config file, CLI args) and authentication approaches.
-   **Security:** Handle sensitive PATs responsibly.

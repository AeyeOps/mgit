# System Patterns: Azure DevOps CLI Tool (ado-cli)

## Core Architecture

The tool follows a modular architecture centered around manager classes and a CLI framework:

1.  **Configuration Loading:** Uses `python-dotenv` to load settings from environment variables and a global config file (`~/.config/ado-cli/config`), providing a hierarchical configuration system. Default values are defined within the script.
2.  **Logging:** Implements Python's `logging` module with `rich` for enhanced console output (colors, formatting) and a `RotatingFileHandler` for file logging. A custom formatter (`AdoCliFormatter`) sanitizes sensitive PATs from logs.
3.  **Azure DevOps Interaction (`AzDevOpsManager`):** Encapsulates interactions with the Azure DevOps REST API using the `azure-devops` Python SDK. Handles authentication (via PAT), connection initialization, and fetching project/repository data.
4.  **Git Operations (`GitManager`):** Manages local Git commands (`clone`, `pull`) using asynchronous subprocess execution (`asyncio.create_subprocess_exec`) for concurrency.
5.  **CLI Interface (`Typer`):** Uses the `typer` library to define commands (`clone-all`, `pull-all`, `login`, `config`, `generate-env`), arguments, and options, providing automatic help generation and type validation.
6.  **Asynchronous Execution (`asyncio`):** Leverages `asyncio` for concurrent execution of Git operations, controlled by a semaphore (`asyncio.Semaphore`) to limit the number of simultaneous tasks. `rich.progress` is used for visual feedback during concurrent operations.

## Key Technical Decisions & Patterns

-   **SDK over Direct API Calls:** Utilizes the official `azure-devops` Python SDK for interacting with Azure DevOps, simplifying API interactions and benefiting from SDK maintenance.
-   **PAT Authentication:** Primarily relies on Personal Access Tokens (PATs) for authentication, embedded securely into Git URLs for cloning/pulling.
-   **Asynchronous I/O:** Employs `asyncio` for Git operations to improve performance when dealing with multiple repositories. Subprocesses are used for executing `git` commands.
-   **Hierarchical Configuration:** Prioritizes environment variables, then a global config file, then hardcoded defaults, offering flexibility.
-   **Modular Design:** Separates concerns into distinct classes (`AzDevOpsManager`, `GitManager`) for better organization and testability.
-   **Rich CLI Output:** Uses `rich` for formatted console logs, enhanced progress bars (`rich.progress` with dynamic task updates for individual repo status), and interactive confirmation prompts (`rich.prompt.Confirm`), enhancing user experience and safety.
-   **Type Hinting:** Uses Python type hints for better code clarity and maintainability.
-   **Dependency Management:** Uses `requirements.txt` for managing Python dependencies.
-   **Executable Bundling:** Uses `pyinstaller` with a `.spec` file (`ado-cli.spec`) to create a standalone executable. The `.spec` file includes necessary `hiddenimports` (e.g., `azure.devops`, `msrest`, `dotenv`) to ensure required packages are bundled correctly.
-   **Error Handling:** Uses standard Python exceptions and logs errors. `subprocess.CalledProcessError` is caught for Git command failures. Basic SDK exceptions like `AzureDevOpsAuthenticationError` and `ClientRequestError` are handled. Added check for `None` return code in `_run_subprocess` to satisfy Mypy.

## Component Relationships & Flow

```mermaid
graph TD;
    subgraph CLI Interface (Typer)
        Cmd_Login[login]
        Cmd_Clone[clone-all]
        Cmd_Pull[pull-all]
        Cmd_Config[config]
        Cmd_GenEnv[generate-env]
    end

    subgraph Core Logic
        Cfg[Configuration (dotenv, file, defaults)]
        Log[Logging (logging, rich)]
        AzMgr[AzDevOpsManager (SDK)]
        GitMgr[GitManager (asyncio, subprocess)]
    end

    CLIInterface --> Cfg
    CLIInterface --> Log

    Cmd_Login --> AzMgr -- Test Connection --> Log
    Cmd_Login --> Cfg -- Store Credentials --> Log

    Cmd_Clone --> AzMgr -- Get Project/Repos --> Log
    Cmd_Clone --> GitMgr -- Async Clone --> Log
    AzMgr --> Cfg -- Get PAT/URL --> Log
    GitMgr --> Cfg -- Get PAT --> Log

    Cmd_Pull --> AzMgr -- Get Project/Repos --> Log
    Cmd_Pull --> GitMgr -- Async Pull --> Log

    Cmd_Config --> Cfg -- Read/Write Config --> Log

    Cmd_GenEnv --> Cfg -- Generate .env.sample --> Log

    AzMgr -->|Uses| AzureDevOpsSDK[azure-devops SDK]
    GitMgr -->|Runs| GitCLI[git CLI]
```

## Critical Implementation Paths

-   **Authentication (`AzDevOpsManager.__init__`, `login` command):** Correctly initializing the SDK connection with the PAT is crucial. The `test_connection` method verifies this.
-   **Concurrent Git Operations (`clone_all`, `pull_all`):** The `asyncio` implementation with the semaphore correctly manages concurrent `git clone` or `git pull` subprocesses. Error handling within the `async def process_one_repo` / `async def do_pulls` loops is important to prevent one failure from stopping the entire batch.
-   **Repository URL Handling:** Correctly embedding the PAT into the Git URL (`embed_pat_in_url`) and sanitizing repository names for filesystem paths (`sanitize_repo_name`) are key for successful cloning.
-   **Update Mode Logic (`clone_all`):** Correctly handling the `skip`, `pull`, and `force` modes when a local directory already exists.

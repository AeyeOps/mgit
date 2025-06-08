# System Patterns

## System Architecture Overview

`mgit` is a monolithic CLI application built with Python and the Typer library. Its architecture is designed to be extensible and maintainable through a clear separation of concerns into distinct subsystems: Provider Management, Commands, Security, Monitoring, and core Git interaction.

```mermaid
graph TD
    subgraph User Interface
        CLI[CLI Interface (Typer in __main__.py)]
    end

    subgraph Core Subsystems
        Cmd[Commands Subsystem (listing.py, monitoring.py)]
        ProviderMgmt[Provider Management Subsystem]
        SecuritySub[Security Subsystem]
        MonitorSub[Monitoring Subsystem]
        GitSub[Git Interaction Subsystem]
    end

    subgraph Provider Management Subsystem
        direction LR
        PM[ProviderManager]
        PF[ProviderFactory]
        PR[ProviderRegistry]
        ABC[GitProvider ABC]
    end
    
    subgraph Concrete Providers
        GitHub[GitHubProvider]
        AzDevOps[AzDevOpsProvider]
        Bitbucket[BitbucketProvider]
    end

    subgraph External Systems
        direction LR
        FS[config.yaml]
        GitCLI[Local Git CLI]
        APIs[Provider APIs]
    end

    CLI --> Cmd
    Cmd --> ProviderMgmt
    Cmd --> GitSub
    Cmd --> MonitorSub
    
    ProviderMgmt --> SecuritySub
    ProviderMgmt --> APIs
    ProviderMgmt --> FS
    
    ABC <|-- GitHub
    ABC <|-- AzDevOps
    ABC <|-- Bitbucket

    GitSub --> GitCLI
```

## Design Patterns in Use

*   **Factory Pattern:** The `ProviderFactory` (`providers/factory.py`) provides a centralized method (`create_provider`) for instantiating different provider classes without exposing the creation logic to the client (`ProviderManager`).
*   **Strategy Pattern:** The `GitProvider` abstract base class (`providers/base.py`) defines a common interface (a "strategy") for all Git providers. The `ProviderManager` is configured with a concrete strategy (e.g., `GitHubProvider`) at runtime, allowing it to use any provider interchangeably.
*   **Singleton Pattern:** Both the `ProviderRegistry` (`providers/registry.py`) and the `SecurityMonitor` (`security/monitor.py`) are implemented as singletons. This ensures a single, globally accessible instance for managing provider registration and security event logging, respectively.
*   **Facade Pattern:** The `GitManager` (`git/manager.py`) acts as a Facade, providing a simple, clean interface (`git_clone`, `git_pull`) over the more complex underlying `asyncio.subprocess` system for executing shell commands.
*   **Command Pattern:** The application's CLI commands (`list`, `monitoring`, etc.) are encapsulated in their own modules within the `commands/` directory. This decouples the action's implementation from the main CLI definition in `__main__.py`.

## Key Architectural Subsystems

### Provider Management
This is the core of `mgit`. It uses the **Registry** to auto-discover available providers, the **Factory** to instantiate them, and the **ProviderManager** to orchestrate operations. The **Strategy** pattern ensures all providers adhere to a common contract.

### Asynchronous Task Execution
The `AsyncExecutor` (`utils/async_executor.py`) is a generic, reusable component for managing concurrent batch operations. It uses `asyncio.Semaphore` for concurrency control and is tightly integrated with the `rich` library for progress display, providing a consistent UX for long-running tasks like `clone-all`.

### Security Model
The application features a multi-layered security model:
1.  **Prevention (`CredentialMasker`):** Proactively masks credentials in logs, URLs, and API responses using regex and keyword detection.
2.  **Validation (`SecurityValidator`):** Validates and sanitizes all user input (URLs, paths, names) to prevent common vulnerabilities like path traversal.
3.  **Detection (`SecurityMonitor`):** An event-driven singleton that tracks security-related events (e.g., auth failures), detects anomalies (e.g., rapid failures), and provides a security overview.

### Progress Display System
The `ProgressManager` (`utils/progress.py`) provides a high-level abstraction over the `rich` library, enabling styled, nested progress bars for a polished and informative user experience during complex operations.

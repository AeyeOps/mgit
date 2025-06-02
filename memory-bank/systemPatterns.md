# System Patterns

## System Architecture Overview

*   [User to describe the high-level architecture of `mgit`. For example, is it a monolithic CLI, or does it have distinct layers? What are the major components?]
    *   Example: `mgit` is a CLI application built with Python using the Typer library. It features a modular provider system to interact with different Git hosting services (GitHub, Bitbucket, Azure DevOps). Configuration is managed via a YAML file.

```mermaid
graph TD
    CLI_Interface[CLI Interface (Typer)] --> Command_Parser[Command Parser]
    Command_Parser --> Config_Manager[ConfigManager (yaml_manager.py)]
    Command_Parser --> Provider_Factory[ProviderFactory (factory.py)]
    
    Provider_Factory --> GitHub_Provider[GitHubProvider (github.py)]
    Provider_Factory --> Bitbucket_Provider[BitbucketProvider (bitbucket.py)]
    Provider_Factory --> AzureDevOps_Provider[AzureDevOpsProvider (azdevops.py)]
    
    GitHub_Provider --> GitHub_API[GitHub API]
    Bitbucket_Provider --> Bitbucket_API[Bitbucket API]
    AzureDevOps_Provider --> AzureDevOps_API[Azure DevOps API]
    
    Config_Manager --> Filesystem[config.yaml]
    
    CLI_Interface --> Git_Manager[GitManager (git/manager.py)]
    Git_Manager --> Local_Git_Commands[Local Git Commands]

    subgraph Providers
        direction LR
        GitHub_Provider
        Bitbucket_Provider
        AzureDevOps_Provider
    end

    subgraph CoreLogic
        direction TB
        Command_Parser
        Config_Manager
        Provider_Factory
        Git_Manager
    end
```
*(The above Mermaid diagram is an example based on the file structure. User should update/replace it to accurately reflect the system.)*

## Key Technical Decisions

*   **Language:** Python (version?)
*   **CLI Framework:** Typer
*   **Configuration:** YAML (`ruamel.yaml` for comment preservation)
*   **Concurrency:** [e.g., `asyncio` for I/O-bound operations with providers, if applicable]
*   **Testing:** `pytest`
*   **Formatting:** `black`
*   **Linting:** `ruff` (assumed from CI output)
*   **Type Checking:** `mypy` (assumed from CI output)
*   [User to add other key decisions]

## Design Patterns in Use

*   **Factory Pattern:** Used in `providers/factory.py` to create instances of different Git providers.
*   **Strategy Pattern:** (Potentially) Each provider class implements a common interface defined in `providers/base.py`, allowing different strategies for interacting with Git services.
*   **Singleton Pattern:** (Potentially) For managing global configuration or a shared resource.
*   [User to list and describe other patterns observed or intended].

## Component Relationships & Critical Implementation Paths

*   **Configuration Loading:** `yaml_manager.py` is critical for loading and saving provider configurations. It uses `ruamel.yaml` to preserve comments and structure.
*   **Provider Interaction:**
    *   `providers/manager_v2.py` (or a similar central manager) likely orchestrates operations across multiple configured providers.
    *   Each provider (`github.py`, `bitbucket.py`, `azdevops.py`) encapsulates the logic for communicating with its respective API.
    *   `providers/exceptions.py` defines custom exceptions for provider-related errors.
*   **Local Git Operations:** `git/manager.py` handles interactions with the local Git CLI.
*   **Command Handling:** `__main__.py` defines the Typer app and its commands, delegating to other modules for specific functionalities.
*   **Security:** `security/credentials.py` handles masking of sensitive data.
*   [User to detail other critical paths and component interactions].

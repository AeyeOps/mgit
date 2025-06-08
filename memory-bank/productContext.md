# Product Context

## Problem Statement

Developers and teams working with microservices or managing multiple projects often face significant challenges:
*   **Credential Complexity:** Managing, securing, and using different Personal Access Tokens (PATs) or App Passwords for multiple Git providers (Azure DevOps, GitHub, Bitbucket) is cumbersome and error-prone.
*   **Workflow Fragmentation:** Switching between different web UIs, CLIs, and contexts to perform common tasks like cloning or pulling updates across a fleet of repositories is inefficient and time-consuming.
*   **Lack of Unified View:** There is no single, simple way to get a status overview or perform bulk operations on repositories that are spread across different providers or organizations.
*   **Poor Observability:** Standard Git operations provide little insight into performance, error rates, or security events, making it difficult to troubleshoot issues in an automated or large-scale environment.

## Proposed Solution

`mgit` addresses these problems by providing a single, powerful command-line interface that acts as a unified management layer on top of multiple Git providers.
*   It provides a centralized and secure YAML-based configuration system for managing provider credentials.
*   It offers simple, intuitive commands (`clone-all`, `pull-all`, `list`) to perform bulk operations across all configured repositories, regardless of their provider.
*   It streamlines the developer workflow by abstracting away provider-specific details, allowing users to interact with all their repositories through one consistent tool.
*   It includes a comprehensive monitoring suite (`mgit monitoring`) that provides health checks, performance metrics, and security event logging.

## User Experience (UX) Goals

*   **Simplicity:** The CLI should be easy to learn and use, with clear, predictable commands and helpful feedback.
*   **Efficiency:** `mgit` must significantly reduce the time and manual effort required for common multi-repo workflows. Asynchronous operations are key to achieving this.
*   **Clarity:** The tool must provide clear output, detailed progress indicators for long-running tasks, and actionable error messages.
*   **Reliability:** Operations must be performed consistently and predictably, with robust error handling.
*   **Security & Observability:** The tool is designed with security as a first-class citizen, handling sensitive information securely and providing deep visibility into its operations.

## How It Should Work (Core Functionality)

1.  **Configuration (`mgit login`, `mgit config`):** The user first configures one or more Git providers by running `mgit login`. This command prompts for the necessary credentials (URL, token, etc.), tests the connection, and saves the configuration to a central YAML file (`~/.config/mgit/config.yaml`). The user can create multiple named configurations (e.g., `github_personal`, `ado_work`) and set a default.
2.  **Execution (`mgit clone-all`, `mgit pull-all`):** The user runs a command like `mgit clone-all <organization> <path>`. `mgit` uses the configured provider to fetch a list of all repositories in that organization. It then asynchronously clones each repository into the specified path, showing a detailed progress bar.
3.  **Discovery (`mgit list`):** The user can quickly list and filter repositories across all configured providers using a simple query syntax (`org/project/repo`), providing a unified view of all their projects.
4.  **Monitoring (`mgit monitoring`):** The user can start a monitoring server, perform health checks, and export performance metrics, providing deep insight into the application's behavior and security posture.

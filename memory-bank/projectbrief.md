# Project Brief: mgit (mgit)

## Core Purpose

To provide a powerful and user-friendly command-line interface (CLI) for managing Azure DevOps Git repositories, simplifying common bulk operations like cloning and pulling updates across an entire project.

## Key Goals

1.  **Simplify Bulk Repository Management:** Enable users to clone all repositories within an Azure DevOps project or pull updates for all local repositories associated with a project using single commands.
2.  **Improve Efficiency:** Leverage asynchronous operations (asyncio) to perform Git actions concurrently, speeding up tasks involving multiple repositories.
3.  **Provide Flexible Configuration:** Offer multiple ways to configure settings (environment variables, global config file, command-line arguments) and manage authentication (PAT).
4.  **Enhance User Experience:** Utilize libraries like Typer and Rich to create an intuitive CLI with clear commands, help messages, and informative progress indicators.
5.  **Ensure Security:** Handle Personal Access Tokens (PATs) securely by masking them in logs and output, and using secure file permissions for configuration.
6.  **Robustness:** Handle potential issues like disabled repositories gracefully and provide clear logging for diagnostics.
7.  **Extensibility:** Establish a clear architecture (AzDevOpsManager, GitManager) to facilitate future enhancements and new commands.

## Target Audience

Developers, DevOps Engineers, and anyone managing multiple Git repositories within Azure DevOps projects.

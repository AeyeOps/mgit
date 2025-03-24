# Tech Context: Azure DevOps CLI Tool (ado-cli)

## Core Technology

-   **Language:** Python (Version 3.7+ required, as per README)

## Key Libraries & Frameworks

-   **Azure DevOps SDK (`azure-devops`):** Primary library for interacting with the Azure DevOps REST API to fetch project and repository information. Version `>=7.1.0b` is specified.
-   **CLI Framework (`typer`):** Used to build the command-line interface, handle arguments, options, and generate help messages. Version `>=0.9.0`.
-   **Configuration (`python-dotenv`):** Loads environment variables from `.env` files and the global config file. Version `>=1.0.0`.
-   **Console Output (`rich`):** Enhances the CLI output with formatted text, colors, and progress bars. Version `>=13.6.0`.
-   **Asynchronous Operations (`asyncio`):** Python's built-in library for managing concurrent operations, used primarily for running Git commands in parallel. Version `>=3.4.3`.
-   **Filesystem Paths (`pathlib`):** Used for object-oriented filesystem path manipulation. Version `>=1.0.1`.

## Development & Build Tools

-   **Dependency Management:** `pip` and `requirements.txt`.
-   **Executable Bundling (`pyinstaller`):** Used optionally (as per README) to create a standalone executable from the Python script. Version `>=6.0.0`.

## Runtime Environment

-   **Operating System:** Designed to run on systems where Python 3.7+ and Git are installed. Tested implicitly on Linux (based on environment details).
-   **External Dependencies:** Requires a working `git` command-line executable available in the system's PATH.

## Technical Constraints

-   Requires network access to the specified Azure DevOps organization URL.
-   Requires a valid Azure DevOps Personal Access Token (PAT) with appropriate permissions (e.g., Code Read) to access project and repository data.
-   Performance of concurrent operations depends on network bandwidth, disk I/O, and the number of repositories.

# CLAUDE.md - mgit (Multi-Git CLI Tool) Guide

## Build/Test/Lint Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run the tool
python mgit.py [command] [arguments]

# Display help (running without arguments shows help)
python mgit.py
python mgit.py --help

# Common commands
python mgit.py login --org https://dev.azure.com/your-org --pat your-pat
python mgit.py clone-all [project-name] [destination-path] [-c concurrency] [-u update-mode]
python mgit.py pull-all [project-name] [repositories-path]
python mgit.py generate-env
python mgit.py config --show

# Package the application (PyInstaller)
pip install pyinstaller
pyinstaller --onefile mgit.py

# Run the packaged executable
./dist/mgit [command] [arguments]

# Run tests (when implemented)
python -m pytest tests/test_file.py::test_function -v
python -m pytest tests/ -v --cov=. --cov-report=term
```

## Project Structure
- **mgit.py**: Main application entry point
- **requirements.txt**: Dependencies list
- **ARCHITECTURE.md**: Technical design and future improvements
- **README.md**: User documentation and examples
- **CLAUDE.md**: Guidelines for agentic coding agents
- **dist/**: Built executable files
- **build/**: Temporary build files

## Code Style Guidelines
- **Imports**: Group in order of stdlib → third-party → local modules
- **Formatting**: Black (4-space indents, 88 char line length)
- **Types**: Type hints required for all functions and methods
- **Naming**:
  - Classes: CamelCase (e.g., `AzDevOpsManager`)
  - Functions/Methods: snake_case (e.g., `git_clone`)
  - Variables: snake_case (e.g., `repo_url`, `output_dir`)
  - Constants: UPPER_SNAKE_CASE (e.g., `DEFAULT_VALUES`)
- **Error Handling**: Use `typer.Exit(code=1)` for CLI failures with descriptive messages
- **Documentation**: Docstrings for all classes/functions, comments for complex logic
- **Logging**: Use structured logging with proper levels (debug, info, error)
- **Async**: Use asyncio and Semaphore for concurrent operations
- **Security**: Always sanitize PATs/credentials in logs and console output
- **Testing**: Write unit tests for core functionality, use pytest fixtures for common setup

## Best Practices
- Use Path objects from pathlib instead of string paths
- Validate inputs before performing operations
- Provide meaningful progress indicators for long-running operations
- Add retry logic for network operations
- Ensure proper exception handling and user-friendly error messages
- Follow the hierarchical configuration system (env vars → global config → defaults)
- Maintain backward compatibility with existing commands
- Adhere to the established authentication flow and security practices

## Key Components
- **AzDevOpsManager**: Handles Azure DevOps API interactions and authentication
- **GitManager**: Manages Git operations (clone, pull) with async support
- **Configuration**: Hierarchical system using env vars, config files, and defaults
- **Logging**: Rich console output with sanitized credentials
- **CLI Commands**: Typer-based command structure with help documentation
# CLAUDE.md - Azure DevOps CLI Tool Guide

## Build/Test/Lint Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run the tool
python ado-cli.py [command] [arguments]

# Display help (running without arguments shows help)
python ado-cli.py
python ado-cli.py --help

# Common commands
python ado-cli.py login --org https://dev.azure.com/your-org --pat your-pat
python ado-cli.py clone-all [project-name] [destination-path] [-c concurrency] [-u update-mode]
python ado-cli.py pull-all [project-name] [repositories-path]
python ado-cli.py generate-env
python ado-cli.py config --show

# Package the application (PyInstaller)
pip install pyinstaller
pyinstaller --onefile ado-cli.py

# Run the packaged executable
./dist/ado-cli [command] [arguments]

# Run tests (when implemented)
python -m pytest tests/test_file.py::test_function -v
python -m pytest tests/ -v --cov=. --cov-report=term
```

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
- Create custom exceptions for different error scenarios
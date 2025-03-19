# CLAUDE.md - Azure DevOps CLI Tool Guide

## Build/Test/Lint Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run the tool
python ado-cli.py [command] [arguments]

# Example: Clone all repositories from a project
python ado-cli.py clone-all [project-name] [destination-path]

# Example: Pull latest changes for all repositories
python ado-cli.py pull-all [project-name] [repositories-path]

# Example: Generate environment file
python ado-cli.py gen-env

# Run tests (when implemented)
pytest tests/ -v
```

## Code Style Guidelines
- **Imports**: Group in order of stdlib, third-party, local with stdlib first
- **Formatting**: Follow black conventions (4-space indents, 88 char line length)
- **Types**: Use type hints for all function parameters and return values
- **Naming**:
  - Classes: CamelCase (e.g., `AzDevOpsManager`)
  - Functions/Variables: snake_case (e.g., `git_clone`)
  - Constants: UPPER_SNAKE_CASE (e.g., `DEFAULT_VALUES`)
- **Error Handling**: Use custom exceptions and `typer.Exit(code=1)` for CLI failures
- **Documentation**: Include docstrings for classes and functions; add comments for complex logic
- **Logging**: Use the logger with appropriate levels (debug, info, error)
- **Async**: Use asyncio for concurrent operations when appropriate
- **Security**: Never expose PATs or sensitive info in logs or output
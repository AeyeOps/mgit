# CLAUDE.md - Azure DevOps CLI Tool Guide

## Build/Test/Lint Commands
```
# Install dependencies
pip install -r requirements.txt

# Run the tool
python ado-cli.py [command] [arguments]

# Execute a single test (example)
pytest tests/test_file.py::test_function -v
```

## Code Style Guidelines
- **Imports**: Group imports (stdlib, third-party, local) with stdlib first
- **Formatting**: Use black for formatting (4-space indents, 88 char line length)
- **Types**: Use type hints for all function parameters and return values
- **Naming**:
  - Classes: CamelCase (e.g., AzDevOpsManager)
  - Functions/Variables: snake_case (e.g., git_clone)
  - Constants: UPPER_SNAKE_CASE (e.g., DEFAULT_VALUES)
- **Error Handling**: Use custom exceptions and typer.Exit(code=1) for CLI failures
- **Documentation**: Docstrings for classes and functions; rich comments for complex operations
- **Logging**: Use the logger with appropriate levels (debug, info, error)
- **Security**: Never expose PATs or sensitive info in logs or output
# Contributing to mgit

Thank you for your interest in contributing to mgit! This guide will help you get started.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct: be respectful, inclusive, and constructive in all interactions.

## How to Contribute

### Reporting Issues

- Check existing issues first to avoid duplicates
- Use issue templates when available
- Include:
  - mgit version (`mgit --version`)
  - Python version (`python --version`)
  - Operating system
  - Steps to reproduce
  - Expected vs actual behavior
  - Error messages/logs

### Suggesting Features

- Open a discussion first for major features
- Explain the use case and benefits
- Consider implementation complexity
- Be open to feedback and alternatives

### Submitting Pull Requests

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR-USERNAME/mgit.git
   cd mgit
   ```

2. **Set Up Development Environment**
   ```bash
   # Install Poetry
   curl -sSL https://install.python-poetry.org | python3 -

   # Install dependencies
   poetry install --with dev

   # Activate virtual environment
   poetry shell
   ```

3. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make Changes**
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

5. **Run Tests and Checks**
   ```bash
   # Run all tests
   poetry run pytest

   # Run with coverage
   poetry run pytest --cov=mgit

   # Run linting
   poetry run ruff check .

   # Format code
   poetry run black .

   # Type checking
   poetry run mypy mgit/
   ```

6. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` New features
   - `fix:` Bug fixes
   - `docs:` Documentation changes
   - `test:` Test additions/changes
   - `refactor:` Code refactoring
   - `chore:` Maintenance tasks

7. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

## Development Guidelines

### Code Style

- **Python Style**: Follow PEP 8
- **Formatting**: Use Black (88 char line length)
- **Imports**: Use isort ordering
- **Type Hints**: Required for all public functions
- **Docstrings**: Google style for all public APIs

### Testing

- Write tests for all new functionality
- Maintain or improve code coverage
- Use pytest fixtures for common setups
- Mock external API calls
- Test both success and error cases

### Documentation

- Update README.md for user-facing changes
- Add/update docstrings for API changes
- Update relevant guides in docs/
- Include examples for new features

### Provider Development

When adding a new provider:

1. Inherit from `GitProvider` base class
2. Implement all required abstract methods
3. Add to provider registry
4. Create provider-specific tests
5. Document authentication requirements
6. Add usage guide in docs/providers/

## Project Structure

```
mgit/
├── mgit/               # Main package
│   ├── commands/       # CLI commands
│   ├── providers/      # Provider implementations
│   ├── config/         # Configuration management
│   ├── git/           # Git operations
│   ├── monitoring/    # Monitoring/metrics
│   ├── security/      # Security features
│   └── utils/         # Utilities
├── tests/             # Test suite
├── docs/              # Documentation
└── scripts/           # Build/utility scripts
```

## Testing

### Running Tests

```bash
# All tests
poetry run pytest

# Specific test file
poetry run pytest tests/unit/test_providers.py

# With coverage
poetry run pytest --cov=mgit --cov-report=html

# Specific test
poetry run pytest -k "test_github_auth"
```

### Writing Tests

```python
# Example test structure
def test_feature_behavior():
    """Test that feature behaves correctly."""
    # Arrange
    provider = MockProvider()
    
    # Act
    result = provider.list_repositories("pattern")
    
    # Assert
    assert len(result) == 5
    assert all(r.name.startswith("test-") for r in result)
```

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release PR
4. Tag release after merge
5. GitHub Actions builds and publishes

## Getting Help

- **Discord**: [Join our server](https://discord.gg/mgit)
- **Discussions**: Use GitHub Discussions
- **Issues**: For bugs and feature requests

## Recognition

Contributors are recognized in:
- CHANGELOG.md release notes
- GitHub contributors page
- Project documentation

Thank you for contributing to mgit!
CRUSH.md — mgit repo quick guide for agents

## Setup & Development
Install: poetry install --with dev
Run CLI: poetry run mgit --help | --version

## Testing Commands
Test all: poetry run poe test (or: poetry run pytest -v)
Unit only: poetry run pytest -m unit
Skip network: poetry run pytest -m "not requires_network"
Single test: poetry run pytest tests/unit/test_git.py::TestGitOperations::test_git_clone_success -v
By pattern: poetry run pytest -k "expr" -v

## Code Quality
Lint: poetry run poe lint (ruff check .)
Format: poetry run poe format (black .)
Format check: poetry run poe format-check
Types: poetry run mypy mgit/
Build: poetry run poe build-linux | build-windows | build-all
Security: poetry run bandit -r mgit/ -f txt; poetry run pip-audit

## Code Style Guidelines

### Formatting & Imports
- Black + Ruff, line-length 88, sorted imports enforced
- Group: stdlib/third-party/local, absolute within mgit
- No wildcard imports

### Types & Naming
- Annotate public defs, disallow untyped defs, prefer precise generics
- snake_case funcs/vars, PascalCase classes, UPPER_CASE constants

### Error Handling
- Raise specific mgit.exceptions, no bare except, preserve context with raise ... from e

## Architecture Guidelines

### Security & Async
- Never log secrets/tokens, use mgit.security.logging masking, rich console for CLI
- Async-first, new aiohttp session per op, don't cache provider instances across loops

### Architecture Patterns
- Keep provider code in mgit/providers, CLI uses provider interface only
- Config via mgit/config/yaml_manager (env > config > defaults)

## Testing Patterns
Mock network I/O, respect markers (unit/integration/e2e/slow/requires_network)

## Commit Hygiene
Run lint/format/types/tests before PRs

## Additional Commands
Clean: poetry run poe clean
Version sync: poetry run poe version-sync
Version bump: poetry run poe bump-patch | bump-minor | bump-major

## IDE Support
Cursor/Copilot: none found (.cursor/.cursorrules/.github/copilot-instructions.md); if added, follow them in addition to this file</content>
<parameter name="file_path">/opt/aeo/mgit/CRUSH.md
# Repository Guidelines

## Project Structure & Module Organization
- `mgit/`: Core Python package and Typer CLI entrypoint (`__main__.py`). Key submodules: `commands/`, `providers/`, `git/`, `pipeline/`, `utils/`, `security/`.
- `tests/`: Pytest suite with `unit/`, `integration/`, `e2e/`; shared fixtures in `tests/conftest.py`.
- `scripts/`: Maintenance utilities (e.g., `scripts/update_version.py`).
- Build & packaging: `mgit.spec`, `build/`, `dist/`. Supporting folders: `docs/`, `docker/`, `deploy/`.

## Build, Test, and Development Commands
- uv (preferred): `uv sync --all-extras --dev` then `uv run pyinstaller mgit.spec --clean`
- Run CLI: `./dist/mgit --help` (after build) or `uv run mgit --help`
- Poetry (legacy): `poetry run poe test|lint|format|build-linux`
- Clean caches: `find . -type d -name '__pycache__' -prune -exec rm -rf {} + && find . -type d -empty -delete`

## Coding Style & Naming Conventions
- Python 3.9–3.12. Use type hints; avoid untyped defs (mypy enforced).
- Formatting: Black, line length 88; 4-space indentation.
- Linting: Ruff (`E`, `F`, `I`; `E501` ignored). Keep imports sorted.
- Naming: `snake_case` for modules/functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- CLI stack: Typer 0.9.x and Click 8.1.x (pinned to avoid rich help issues in frozen builds). No autocompletion hooks.

## Testing Guidelines
- Framework: Pytest with markers: `unit`, `integration`, `e2e`, `slow`, `requires_network`, `asyncio`.
- Naming: files `test_*.py`; classes `Test*`; functions `test_*`.
- Examples: `poetry run pytest -m "unit and not slow"`; run all `poetry run poe test`.
- Aim for meaningful coverage of new/changed code; include edge cases and error paths.

## Commit & Pull Request Guidelines
- Commit style: Prefer Conventional Commits (e.g., `feat:`, `fix:`, `chore:`, `refactor:`). Example: `feat: add Azure DevOps repo discovery`
- Before PR: run `poe format`, `poe lint`, and `poe test` (via `poetry run ...`).
- PR description: what/why, breaking changes, usage notes; link issues (`Closes #123`).
- Include test updates and doc snippets (e.g., CLI example output) when relevant.

## Security & Configuration Tips
- Do not commit secrets. Use `.env` locally; common vars: `AZURE_DEVOPS_EXT_PAT`, `AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT`.
- Mark networked tests with `requires_network` and exclude by default.
- Default branch is `main`; keep changes minimal and focused.
- Windows build is done on the Windows side of WSL2; do not attempt mgit.exe build in Ubuntu/WSL.

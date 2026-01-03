# Repository Guidelines

## Project Structure & Module Organization
- `mgit/` is the main package. Key areas: `commands/` (CLI commands), `providers/` (GitHub/Azure DevOps/BitBucket implementations), `config/` (YAML config), `git/` (git ops), `security/`, `utils/`.
- `tests/` holds the pytest suite; `docs/` contains provider guides; `scripts/` has build helpers.
- `mgit.spec` drives PyInstaller builds; `dist/` and `build/` are build outputs.

## Architecture Decision Records
- ADRs in `docs/ADR/` document key design decisions (provider abstraction, config hierarchy, concurrency, pattern matching).
- Read relevant ADRs before modifying core architecture.

## Build, Test, and Development Commands
- Setup (preferred): `uv sync --all-extras --dev` (Poetry alternative: `poetry install --with dev`).
- Run locally: `uv run mgit --help` or `python -m mgit`.
- Tests: `uv run pytest` (or `poetry run pytest`). Use markers like `-m unit` or `-m "not requires_network"`.
- Lint/format/type-check: `uv run ruff check .`, `uv run black .`, `uv run mypy mgit/`.
- Build binaries: `uv run pyinstaller mgit.spec --clean` (Linux) and `bash scripts/build_windows_from_wsl.sh` (Windows). `poetry run poe build-linux` also works.

## Coding Style & Naming Conventions
- PEP 8 with Black formatting (88-char lines). Ruff handles linting and import order (E/F/I).
- Type hints are required for public functions; use Google-style docstrings for public APIs.
- Branch naming in CONTRIBUTING uses `feature/<short-name>`.

## Testing Guidelines
- Pytest is configured for `test_*.py` / `*_test.py` files and `test_*` functions.
- Use markers: `unit`, `integration`, `e2e`, `slow`, `requires_network`, `asyncio`.
- Coverage uses `pytest-cov` and outputs `htmlcov/` plus `coverage.xml` when enabled.

## Commit & Pull Request Guidelines
- Recent history uses short imperative summaries (e.g., “Fix …”, “Update …”) and allows merge commits.
- CONTRIBUTING recommends Conventional Commits for new work (`feat:`, `fix:`, `docs:` …).
- PRs should include: a concise summary, tests run, docs updates if applicable, and a linked issue when relevant. Add provider-specific tests and docs when changing a provider.

## Configuration & Security Tips
- Local config lives at `~/.config/mgit/config.yaml`. Use `mgit login` to store provider credentials and avoid committing tokens or config files.

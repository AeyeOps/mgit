# CLAUDE.md - mgit (Multi-Git CLI Tool) Guide

## Build/Test/Lint Commands
```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .  # Development installation for package structure

# Run the tool (package structure - Sprint 2+)
python -m mgit [command] [arguments]

# Display help (running without arguments shows help)
python -m mgit
python -m mgit --help

# Common commands
python -m mgit login --org https://dev.azure.com/your-org --pat your-pat
python -m mgit clone-all [project-name] [destination-path] [-c concurrency] [-u update-mode]
python -m mgit pull-all [project-name] [repositories-path]
python -m mgit generate-env
python -m mgit config --show

# Package the application (PyInstaller)
pip install pyinstaller
pyinstaller --onefile mgit/__main__.py

# Run the packaged executable
./dist/mgit [command] [arguments]

# Run tests (when implemented)
python -m pytest tests/test_file.py::test_function -v
python -m pytest tests/ -v --cov=. --cov-report=term

# Quick test after module extraction
python -m mgit --version  # Should display version
```

## Project Structure (Sprint 2+)
- **mgit/**: Package directory
  - **__init__.py**: Package initialization
  - **__main__.py**: Entry point (temporary location for remaining code)
  - **cli.py**: CLI setup and version callback (Sprint 2)
  - **constants.py**: DEFAULT_VALUES and __version__ (Sprint 2)
  - **logging.py**: MgitFormatter and ConsoleFriendlyRichHandler (Sprint 2)
  - **config/**: Configuration module
    - **manager.py**: get_config_value() function (Sprint 2 - CRITICAL PATH)
  - **utils/**: Utility functions
    - **helpers.py**: embed_pat_in_url(), sanitize_repo_name() (Sprint 2)
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

## Coding Memories
- don't style your Mermaid
- Before creating a visual, read @docs/kb/mermaid-syntax-reference.md

## MAWEP Framework (Multi-Agent Workflow Execution Process)

### ⚠️ Reality Check Protocol - READ FIRST ⚠️
**CRITICAL**: Before proposing or implementing any multi-agent coordination, ALWAYS review:
@~/.claude/reality-check-protocol.md

This prevents over-engineering and capability oversell. Remember: Simple solutions that work beat elegant solutions that don't.

### Complete MAWEP Framework - Single Entry Point
**All MAWEP documentation with verified referential integrity:**
@~/.claude/docs/prompt-packs/mawep/CLAUDE.md

*This single reference brings in the complete MAWEP framework context via internal relative paths. The pack includes:*
- *Core concepts and quick start guides*
- *All role-based instructions (orchestrator, agents, reviewers)*  
- *Framework architecture and patterns*
- *Progressive disclosure from basic to advanced usage*

### mgit-Specific MAWEP Implementation

#### Project Structure
- `mawep-workspace/` - Active MAWEP work directory
  - `sprint-2-assignments.md` - Current sprint assignments
  - `mawep-state.yaml` - Pod and issue tracking (uses "pod" terminology)
  - `worktrees/` - Pod working directories (persistent git worktrees)
- `mawep-simulation/` - Planning and analysis docs
  - `dependency-analysis.md` - Issue dependencies
  - `orchestration-plan.md` - Execution strategy

#### MAWEP Terminology for mgit
- **Agent**: Ephemeral Task tool execution (single message exchange)
- **Pod**: Persistent git worktree where multiple agents work over time on issues
- **Orchestrator**: Manages pods and assigns agent invocations to them

#### When to Use MAWEP
✅ **Use MAWEP when:**
- User provides 3+ related GitHub issues
- User explicitly requests parallel development
- Sprint work with independent issues (like Sprint 2 module extraction)
- User mentions "multiple agents" or "concurrent work"

❌ **Do NOT use MAWEP for:**
- Single issues or simple tasks
- Highly interdependent work requiring constant coordination
- When simple sequential work is sufficient

#### 🚨 Critical MAWEP Reality 🚨
**THE TASK TOOL DOES NOT CREATE BACKGROUND WORKERS**
- Task tool = Single message exchange only
- Invoked agents STOP immediately after responding
- Nothing happens between invocations
- You MUST continuously invoke agents every 30-60 seconds
- NEVER assume agents are "working in the background"

### Sprint 2: Module Extraction Guidelines

#### Import Hierarchy (Prevent Circular Imports)
```
constants.py → No imports from mgit modules
utils/helpers.py → Can import from constants
config/manager.py → Can import from constants, utils  
logging.py → Can import from config, constants
cli.py → Can import from constants
__main__.py → Can import from all modules
```

#### Module Extraction Checklist
- [ ] Copy code to new module location
- [ ] Add necessary imports to new module
- [ ] Add new module import to __main__.py (at TOP of section)
- [ ] Remove extracted code from __main__.py
- [ ] Run `python -m mgit --version` to test
- [ ] Check for import errors

#### Current Sprint Location
Check `mawep-workspace/sprint-2-assignments.md` for current tasks

#### Parallel Work Guidelines (MAWEP Context)
When multiple pods modify __main__.py:
- Each pod works on different modules to minimize conflicts
- Add imports at the TOP of their respective sections (stdlib/third-party/local)
- Use explicit imports: `from mgit.logging import setup_logging, MgitFormatter`
- Do NOT reorganize existing imports
- Make minimal changes - only add your module's imports
- Use coordination branch pattern for shared interfaces

#### Testing Requirements
Before creating PR:
- [ ] `python -m mgit --version` shows version
- [ ] `python -m mgit --help` displays help  
- [ ] No ImportError when running
- [ ] Original functionality preserved

### MAWEP Anti-Patterns (Critical)
❌ **DON'T** assume agents continue working between invocations
❌ **DON'T** over-engineer coordination when simple sequential work suffices
❌ **DON'T** modify other pods' worktrees
❌ **DON'T** reorganize files when make small changes
❌ **DON'T** continue when blocked - report immediately

### Starting MAWEP Orchestration
When ready to use MAWEP, reference the framework entry point above for complete instructions. Always get explicit user consent before starting multi-agent coordination.
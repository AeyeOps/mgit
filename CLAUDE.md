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

## Project Structure (Sprint 2+ COMPLETED)
- **mgit/**: Package directory
  - **__init__.py**: Package initialization
  - **__main__.py**: Entry point (746 lines - 28.7% reduction from Sprint 2 ✅)
  - **cli.py**: CLI setup and version callback (Sprint 2 ✅)
  - **constants.py**: DEFAULT_VALUES, __version__, CONFIG_DIR, CONFIG_FILE, UpdateMode (Sprint 2 ✅)
  - **logging.py**: MgitFormatter, ConsoleFriendlyRichHandler, setup_logging() (Sprint 2 ✅)
  - **config/**: Configuration module
    - **manager.py**: get_config_value(), load_config_file(), save_config_file() (Sprint 2 ✅)
  - **utils/**: Utility functions
    - **helpers.py**: embed_pat_in_url(), sanitize_repo_name() (Sprint 2 ✅)
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

#### Sprint 2 Success Metrics (Completed)
- **5 modules extracted** using proper MAWEP orchestration
- **301 lines removed** from __main__.py (28.7% reduction: 1,047 → 746 lines)
- **All tests passing** - version and help commands work perfectly
- **Clean dependency hierarchy** established and verified
- **Proper MAWEP integration** - all pod work successfully merged

### MAWEP Anti-Patterns (Critical)
❌ **DON'T** assume agents continue working between invocations
❌ **DON'T** over-engineer coordination when simple sequential work suffices
❌ **DON'T** modify other pods' worktrees
❌ **DON'T** reorganize files when make small changes
❌ **DON'T** continue when blocked - report immediately

## MAWEP Sprint Stages - Critical Process Framework

### ⚠️ ORCHESTRATOR WARNING: Read This First ⚠️
**The most common MAWEP failure is INCOMPLETE STAGE EXECUTION**. Agents will report "completed" but critical integration/verification steps get skipped. This section prevents those failures.

### Stage 1: Pre-Sprint Analysis 🔍
**REQUIRED OUTPUTS:**
- [ ] Dependency map showing which issues depend on others
- [ ] Foundation requirements analysis (what must be built first)
- [ ] File/code conflict assessment between parallel work
- [ ] Pod capability matching (assign issues to appropriate pods)
- [ ] Reality check: Is MAWEP actually needed vs sequential work?

**ORCHESTRATOR VERIFICATION:**
```bash
# Document your analysis - don't just think it
echo "Dependencies: Issue A → Issue B → Issue C" > sprint-analysis.md
echo "Foundation needed: [YES/NO]" >> sprint-analysis.md
echo "Conflicts identified: [list]" >> sprint-analysis.md
```

### Stage 2: Sprint Design & Orchestration 📋
**REQUIRED OUTPUTS:**
- [ ] Pod assignments documented
- [ ] Execution sequence defined (dependency order)
- [ ] Shared interfaces/constants planned
- [ ] Integration strategy documented
- [ ] Communication protocol established

**ORCHESTRATOR VERIFICATION:**
- Create sprint assignments file
- Document execution order with rationale
- Plan integration approach BEFORE starting

### Stage 3: Parallel Execution ⚡
**CRITICAL REALITIES:**
- **Agents are ephemeral** - Task tool = single message exchange only
- **No background processing** - Must continuously invoke agents every 30-60 seconds
- **Active orchestration required** - You manage ALL coordination

**EXECUTION PROTOCOL:**
```bash
# Phase 1: Foundation work (serial)
invoke pod-foundation with Issue-X
wait for completion + verification
mark foundation complete

# Phase 2: Dependent work (parallel)
invoke pod-1 with Issue-A &
invoke pod-2 with Issue-B &
invoke pod-3 with Issue-C &
monitor all progress
```

**⚠️ NEVER assume agents continue working between invocations**

### Stage 4: Integration & Convergence 🔗
**🚨 MOST CRITICAL STAGE - Where Most Failures Occur**

**INTEGRATION REALITY:**
- **Pods work in ISOLATION** - Each pod's work exists only in their worktree
- **Integration is MANUAL** - Changes don't automatically merge
- **Dependency order matters** - Must integrate in correct sequence

**INTEGRATION PROTOCOL:**
```bash
# 1. Choose integration base (usually main branch or active pod)
cd integration-workspace

# 2. Merge in dependency order
copy constants.py from pod-foundation
copy config/manager.py from pod-config  
copy utils/helpers.py from pod-utils
# etc.

# 3. Create unified imports in main files
add imports for all extracted modules
remove extracted code from main files

# 4. VERIFY integration works
python -m [tool] --version
python -m [tool] --help
```

**INTEGRATION CHECKLIST:**
- [ ] All pod changes copied to integration workspace
- [ ] Import statements added for new modules
- [ ] Extracted code removed from original files
- [ ] No circular imports created
- [ ] All dependencies resolve correctly

### Stage 5: Validation & Quality Assurance ✅
**🚨 CRITICAL: Never Trust Agent Reports Without Independent Verification**

**VERIFICATION PROTOCOL:**
```bash
# Test basic functionality
python -m [tool] --version     # Should show version
python -m [tool] --help        # Should show all commands

# Test core operations
python -m [tool] [main-command] # Should work without import errors

# Check code reduction
wc -l original-file.py         # Before
wc -l updated-file.py          # After
# Calculate reduction percentage

# Verify all modules can be imported
python -c "from module import function; print('OK')"
```

**NEVER proceed to next sprint without completing this stage**

### Stage 6: Sprint Closure & Documentation 📝
**REQUIRED DELIVERABLES:**
- [ ] Architecture documentation updated
- [ ] Sprint metrics documented (lines reduced, modules created, etc.)
- [ ] Lessons learned captured
- [ ] Next sprint foundation prepared

**CLOSURE VERIFICATION:**
- Document what was actually achieved vs planned
- Update project structure documentation
- Verify all sprint goals met
- Prepare foundation for next sprint

### Common MAWEP Orchestrator Mistakes 🚫

#### ❌ **Mistake #1: Trusting Agent Reports**
**Problem:** Agents report "completed" but work isn't actually integrated
**Solution:** Always verify independently with tests/commands

#### ❌ **Mistake #2: Skipping Integration Stage**
**Problem:** Assuming pod work automatically merges
**Solution:** Explicit integration protocol with verification steps

#### ❌ **Mistake #3: Rushing to Next Sprint**
**Problem:** Moving forward with incomplete foundation
**Solution:** Complete all 6 stages before proceeding

#### ❌ **Mistake #4: Poor Dependency Analysis**
**Problem:** Starting dependent work before foundation is ready
**Solution:** Map dependencies clearly and enforce execution order

#### ❌ **Mistake #5: Insufficient Verification**
**Problem:** Integration breaks but not caught until later
**Solution:** Test at each stage, not just at the end

### MAWEP Success Indicators ✅
- [ ] All 6 stages completed with documented verification
- [ ] Independent testing confirms functionality preserved
- [ ] Architecture improvements measurable (e.g., lines reduced)
- [ ] Foundation ready for next sprint
- [ ] Team understands what was accomplished

### Emergency Recovery Protocol 🚨
**If you discover a sprint is incomplete:**
1. **STOP** - Don't proceed to next sprint
2. **Assess** - Identify which stages were skipped
3. **Recovery** - Go back and complete missing stages
4. **Verify** - Test that recovery was successful
5. **Document** - Update process to prevent recurrence

### Starting MAWEP Orchestration
When ready to use MAWEP, reference the framework entry point above for complete instructions. Always get explicit user consent before starting multi-agent coordination.

**Remember: Following these stages rigorously prevents 90% of MAWEP failures.**
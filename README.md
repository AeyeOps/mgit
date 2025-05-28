# mgit - Multi-Git CLI Tool 🚀

A powerful command-line tool for managing repositories across multiple git platforms (Azure DevOps, GitHub, BitBucket Cloud). Clone entire projects, update multiple repositories, and automate your git workflows across different platforms.

**Plus**: Built-in MAWEP (Multi-Agent Workflow Execution Process) support for orchestrating parallel AI development across multiple issues!

## Overview

mgit simplifies repository management and enables advanced parallel development workflows:

**Core Git Operations:**
- Clone all repositories from a project with a single command
- Pull updates for multiple repositories simultaneously  
- Configure global settings for repeated operations
- Manage authentication credentials securely
- Automatically handle disabled repositories with clear reporting

**MAWEP Integration:**
- Orchestrate AI agents working in persistent pods (git worktrees) on GitHub issues
- Isolated development environments for conflict-free parallel work
- State management and progress tracking across development pods
- Perfect for sprint work and large refactoring efforts

Built with Python using modern package structure, leveraging asynchronous operations for speed and providing rich console output for better visibility.

## Project Structure

```
mgit/
├── mgit/                    # Main package
│   ├── __main__.py         # Entry point
│   ├── cli/                # CLI components  
│   ├── config/             # Configuration management
│   ├── git/                # Git operations
│   └── utils/              # Utility functions
├── docs/                   # Comprehensive documentation
│   ├── architecture/       # Technical design docs
│   ├── configuration/      # Config system docs
│   └── framework/          # MAWEP framework docs
├── mawep-workspace/        # MAWEP parallel development
│   ├── mawep-state.yaml   # Pod and issue tracking
│   └── worktrees/         # Development pods
│       ├── pod-1/         # Isolated workspace for issue #101
│       ├── pod-2/         # Isolated workspace for issue #102
│       └── pod-3/         # Isolated workspace for issue #103
├── memory-bank/           # Project context and progress
└── scripts/               # Automation scripts
```

## Installation

### Prerequisites

- Python 3.7 or higher
- Git

### Installation Steps

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/mgit.git
   cd mgit
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e .  # Development installation for package structure
   ```

3. Run the tool:
   ```bash
   python -m mgit
   ```

### Building a Standalone Executable

For convenience, you can build a standalone executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Create a single executable file
pyinstaller --onefile mgit/__main__.py

# Run the executable
./dist/__main__
```

## Quick Start

### Basic Git Operations

Get the current version:
```bash
python -m mgit --version
```

### Authentication

First, authenticate with Azure DevOps:

```bash
# Interactive login with prompts
python -m mgit login

# Or specify credentials directly
python -m mgit login --org https://dev.azure.com/your-org --pat your-pat
```

### Clone All Repositories

Clone all repositories from a project:

```bash
python -m mgit clone-all my-project ./repos
```

With custom options:

```bash
# Clone with 8 concurrent operations and force mode (overwrite existing repos)
python -m mgit clone-all my-project ./repos -c 8 -u force
```

### Update All Repositories

Pull the latest changes for all repositories:

```bash
python -m mgit pull-all my-project ./repos
```

### Global Configuration

View or set global configuration:

```bash
# Show current settings
python -m mgit config --show

# Set default values
python -m mgit config --org https://dev.azure.com/your-org --concurrency 16 --update-mode pull
```

### MAWEP Parallel Development

Orchestrate AI agents working in dedicated pods on GitHub issues:

```bash
# Start MAWEP orchestration for sprint work
python -m mgit mawep start --issues 101,102,103,104

# Check status of all development pods
python -m mgit mawep status

# Monitor specific pod progress
python -m mgit mawep pod-status pod-1
```

MAWEP creates isolated git worktrees (`pod-1`, `pod-2`, etc.) where AI agents work independently on different issues, preventing conflicts while enabling parallel development.

## Commands Reference

Run without arguments to see available commands:

```bash
python -m mgit
```

### Core Git Commands

#### login

Authenticate with Azure DevOps using a Personal Access Token (PAT).

```bash
python -m mgit login [--org URL] [--pat TOKEN] [--no-store]
```

#### clone-all

Clone all repositories from an Azure DevOps project.

```bash
python -m mgit clone-all PROJECT DESTINATION [--concurrency N] [--update-mode MODE]
```

Update modes:
- `skip`: Skip existing directories (default)
- `pull`: Try to git pull if it's a valid repository 
- `force`: Remove existing directories and clone fresh

#### pull-all

Pull updates for all repositories in a directory.

```bash
python -m mgit pull-all PROJECT REPOSITORY_PATH
```

#### config

View or set global configuration settings.

```bash
python -m mgit config [--show] [--org URL] [--concurrency N] [--update-mode MODE]
```

#### generate-env

Generate a sample environment file with configuration options.

```bash
python -m mgit generate-env
```

### MAWEP Commands (Parallel Development)

#### mawep start

Launch MAWEP orchestration for parallel issue development.

```bash
python -m mgit mawep start --issues ISSUE_LIST [--repository REPO] [--concurrency N]
```

#### mawep status

Show status of all development pods and assigned issues.

```bash
python -m mgit mawep status [--detailed]
```

#### mawep pod-status

Get detailed status of a specific pod.

```bash
python -m mgit mawep pod-status POD_NAME
```

#### mawep stop

Stop MAWEP orchestration and cleanup resources.

```bash
python -m mgit mawep stop [--preserve-worktrees]
```

### Global Options

#### --version

Show the application's version and exit.

```bash
python -m mgit --version
```

#### --help

Show help for any command.

```bash
python -m mgit [command] --help
```

## Configuration

The tool uses a hierarchical configuration system:

1. **Environment variables** (highest priority)
2. **Global config** in `~/.config/mgit/config` (second priority)
3. **Default values** in code (lowest priority)

Key configuration options:

- `AZURE_DEVOPS_ORG_URL`: Azure DevOps organization URL
- `AZURE_DEVOPS_EXT_PAT`: Personal Access Token
- `DEFAULT_CONCURRENCY`: Number of concurrent operations (default: 4)
- `DEFAULT_UPDATE_MODE`: Default update mode (skip, pull, force)

## Security

The tool handles sensitive information securely:
- PAT tokens are masked in logs and console output
- Configuration files have secure permissions (0600)
- Credentials can be stored securely or used only for the current session

## MAWEP: Parallel Development Made Easy

MAWEP (Multi-Agent Workflow Execution Process) transforms how you handle multi-issue development sprints. Instead of working on issues sequentially, orchestrate AI agents working in persistent pods to tackle multiple issues in parallel.

### When to Use MAWEP

✅ **Perfect for:**
- Sprint work with 3-10 independent issues
- Module extraction and refactoring
- Feature development with clear separation
- Large-scale code organization

❌ **Skip for:**
- Single issues or quick fixes
- Tightly coupled changes
- Simple sequential work

### How MAWEP Works

```
                    ┌─────────────────┐
                    │   Orchestrator  │ ← You control this
                    │ (Claude Code)   │
                    └─────────┬───────┘
                              │
                   "Invoke agent for pod-1"
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                    Agent Invocation                     │ ← Ephemeral
│  "Work on pod-1, check memory-bank, update progress"   │   (Task tool)
└──────────────────────┬──────────────────────────────────┘
                       │
            Agent works in persistent pod
                       │
                       ▼
    ┌─────────────────────────────────────────────┐
    │               Pod-1 Workspace               │ ← Persistent
    │         (Git Worktree + Memory Bank)        │   (Survives)
    │                                             │
    │  📁 mawep-workspace/worktrees/pod-1/        │
    │  ├── [complete project copy]               │
    │  ├── memory-bank/                          │
    │  │   ├── activeContext.md                  │
    │  │   ├── progress.md                       │
    │  │   └── blockers.md                       │
    │  └── .git/ (worktree branch: pod-1-issue-101) │
    └─────────────────────────────────────────────┘
```

### Key Concepts

- **🎭 Agent**: Ephemeral AI task execution (single message → response → done)
- **🏠 Pod**: Persistent git worktree where agents work over time (`pod-1`, `pod-2`, etc.)
- **📊 Orchestrator**: You, coordinating everything through Claude Code
- **💾 Memory Bank**: Persistent context in each pod so agents remember progress

### Getting Started with MAWEP

1. **Launch the Orchestrator**
   ```bash
   # In Claude Code, tell it:
   "Act as MAWEP Orchestrator for parallel development.
   Repository: my-org/awesome-project
   Issues: #101, #102, #103, #104
   Please start by analyzing dependencies and setting up pods."
   ```

2. **MAWEP Sets Up**
   - Analyzes issue dependencies
   - Creates `mawep-workspace/` with state tracking  
   - Spawns git worktrees (`pod-1`, `pod-2`, etc.)
   - Assigns issues to pods based on dependencies

3. **Monitor Progress**
   ```bash
   # Check overall status
   python -m mgit mawep status
   
   # Check specific pod
   python -m mgit mawep pod-status pod-1
   ```

### Pod Structure

Each pod is a complete, isolated workspace:

```
pod-1/
├── memory-bank/           # Persistent context
│   ├── activeContext.md  # What's being worked on
│   ├── progress.md       # What's done/next
│   ├── blockers.md       # What's stopping progress
│   └── systemPatterns.md # Codebase conventions
├── mgit/                 # Full project code
└── [all project files]   # Isolated git worktree
```

### Git Worktree Management

MAWEP automatically handles git worktree operations:

```bash
# Pod creation (MAWEP does this)
git worktree add mawep-workspace/worktrees/pod-1 -b pod-1-issue-101

# Manual pod management commands
git worktree list              # See all active pods
git worktree remove pod-1      # Clean up completed pod
git worktree repair pod-1      # Fix corrupted pod

# Pod isolation means:
# - pod-1 can modify files without affecting pod-2
# - Each pod has its own branch
# - Changes merge back to main via PRs
```

### State Management

MAWEP tracks everything in `mawep-state.yaml`:

```yaml
pods:
  pod-1:
    status: working
    current_issue: 101
    worktree_path: ./worktrees/pod-1
    last_agent_invocation: "2025-05-27T23:45:00Z"
    active_agents: 0

issues:
  101:
    title: "Extract logging module"
    status: assigned
    assigned_to: pod-1
    dependencies: []
    branch_name: pod-1-issue-101
```

### Important MAWEP Reality

⚠️ **Agents don't work in the background!** Each agent invocation is a single request-response cycle. The orchestrator (you) must continuously invoke agents to keep work progressing. Think of it like conducting an orchestra - if you stop conducting, the music stops.

## For Developers

For technical implementation details, architecture diagrams, and future improvement plans, please see [ARCHITECTURE.md](ARCHITECTURE.md).

### Development Workflow

This project uses MAWEP for its own development! The current structure shows Sprint 2 module extraction in progress with 5 active pods working on different components.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
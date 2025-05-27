# MAWEP Quick Start

Start MAWEP by telling Claude Code:

```
I want you to act as the MAWEP Orchestrator for parallel GitHub development.

Repository: [your-org/your-repo]
Issues: #101, #102, #103, #104

Follow @docs/framework/prompts/orchestrator-prompt.md

Start by:
1. Creating a mawep-workspace directory
2. Fetching issue details with gh
3. Building dependency graph
4. Spawning agents for parallel work
```

## What is MAWEP?

MAWEP (Multi-Agent Workflow Execution Process) lets you coordinate multiple AI agents working on GitHub issues in parallel, all from a single Claude Code console.

## Key Files

- **Start Here**: @docs/framework/prompts/example-usage.md
- **Orchestrator Guide**: @docs/framework/prompts/orchestrator-prompt.md
- **Agent Instructions**: @docs/framework/prompts/agent-prompt.md
- **Architecture Diagrams**: @docs/framework/mawep-diagrams.md

## Core Concepts

1. **You** start one Claude Code session as the orchestrator
2. **Orchestrator** spawns agents using the Task tool
3. **Agents** work on issues in separate git worktrees
4. **No background work** - orchestrator continuously monitors
5. **State tracking** in simple YAML file

## Example State File

The orchestrator creates `mawep-state.yaml`:

```yaml
agents:
  agent-1:
    status: working
    current_issue: 101
    worktree_path: ./worktrees/agent-1
    
issues:
  101:
    title: "Add authentication"
    status: assigned
    assigned_to: agent-1
    dependencies: []
```

## Monitoring Command

Ask the orchestrator anytime:
```
Show me the current status of all agents and issues.
```

## See Full Documentation

For complete instructions: @docs/framework/prompts/README.md
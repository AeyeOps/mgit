# MAWEP Prompt Templates

This directory contains ready-to-use instructions for implementing MAWEP (Multi-Agent Workflow Execution Process) using only Claude Code's built-in Task tool. No custom software or parameter injection needed - just copy and adapt these prompts.

## How to Use

1. Start with the **[example-usage.md](example-usage.md)** guide
2. Use the templates below as complete instructions for each role
3. The orchestrator spawns agents using the Task tool
4. All state tracking is done with simple files

## Available Templates

### Core Execution Roles

1. **[orchestrator-prompt.md](orchestrator-prompt.md)**
   - The central coordinator that drives the entire workflow
   - Manages agent assignments, worktrees, and continuous execution
   - **CRITICAL**: Contains the main execution loop - orchestrator must run continuously

2. **[agent-prompt.md](agent-prompt.md)**
   - Template for autonomous development agents
   - Includes implementation procedures, testing requirements, and communication protocols
   - Agents do NOT work in background - only when orchestrator invokes them

### Review Roles

3. **[technical-reviewer-prompt.md](technical-reviewer-prompt.md)**
   - Reviews foundation repository before work begins
   - Creates prerequisite issues for technical debt
   - Reviews individual PRs for code quality

4. **[architect-reviewer-prompt.md](architect-reviewer-prompt.md)**
   - Performs holistic review of multiple PRs developed in parallel
   - Makes individual decisions per PR (approve/approve with issue/reject)
   - Identifies integration conflicts and architectural issues

### Analysis Roles

5. **[post-mortem-analyst-prompt.md](post-mortem-analyst-prompt.md)**
   - Analyzes completed workflows for learnings
   - Extracts patterns from successes and failures
   - Creates actionable improvements for future runs

## Key Concepts

### Continuous Execution
- The orchestrator maintains a continuous loop
- Agents only work when actively invoked by the orchestrator
- No background processing happens without orchestrator driving it

### Communication Flow
- All communication goes through the orchestrator
- Agents report status updates and breaking changes
- Inter-agent queries are routed by orchestrator

### Fail Fast Philosophy
- No error recovery or fallbacks
- Immediate failure on critical issues
- Human intervention required for resolution

## Usage

These prompts should be used as complete operating manuals for each role. They contain:
- Exact procedures to follow
- Decision trees for common scenarios
- Message templates for communication
- Error handling instructions
- Specific code examples and commands

## Customization

When adapting these templates:
1. Maintain the fail-fast philosophy
2. Keep communication patterns intact
3. Preserve state tracking requirements
4. Don't add fallback mechanisms
5. Ensure orchestrator remains in control
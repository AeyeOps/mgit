# MAWEP Example Usage with Claude Code

This guide shows how to use MAWEP with Claude Code's built-in tools, without any custom software.

## Prerequisites

- A GitHub repository with issues to work on
- Git worktrees support
- GitHub CLI (`gh`) installed
- Claude Code with Task tool access

## Step 1: Start as Orchestrator

Open Claude Code and say:

```
I want you to act as the MAWEP Orchestrator. Here are the issues to work on: #101, #102, #103, #104.

The repository is at github.com/myorg/myrepo.

Follow the orchestrator instructions in orchestrator-prompt.md. 

Start by:
1. Fetching these issues with gh
2. Building a dependency graph
3. Creating a state tracking file
4. Determining if we need architectural analysis
```

## Step 2: Orchestrator Creates State File

The orchestrator will create `mawep-state.yaml`:

```yaml
agents:
  agent-1:
    status: idle
    current_issue: null
    worktree_path: ./worktrees/agent-1
  agent-2:
    status: idle
    current_issue: null
    worktree_path: ./worktrees/agent-2

issues:
  101:
    title: "Add user authentication"
    status: ready
    assigned_to: null
    dependencies: []
  102:
    title: "Add user permissions"
    status: ready
    assigned_to: null
    dependencies: [101]  # Depends on auth
  103:
    title: "Add audit logging"
    status: ready
    assigned_to: null
    dependencies: []
  104:
    title: "Add user profile page"
    status: ready
    assigned_to: null
    dependencies: [101]  # Needs auth
```

## Step 3: Architectural Analysis (if needed)

If multiple issues can run in parallel, orchestrator spawns analyst:

```
I'll analyze if issues #101 and #103 can run in parallel. Let me spawn an architectural analyst.

Task: Architectural Analysis
Description: Analyze parallel work feasibility
Prompt: You are a senior architect reviewing these issues for parallel development:

Issue #101: Add user authentication
- Implement JWT tokens
- Create auth middleware
- Add login/logout endpoints

Issue #103: Add audit logging  
- Log all API calls
- Track user actions
- Store in audit table

Check for:
1. Shared file modifications
2. Interface dependencies
3. Runtime conflicts

Report if foundation work is needed.
```

## Step 4: Orchestrator Assigns Work

Based on analysis, orchestrator creates worktrees and spawns agents:

```bash
# Orchestrator executes:
git worktree add ./worktrees/agent-1 -b agent-1-work
git worktree add ./worktrees/agent-2 -b agent-2-work
```

Then spawns first agent:

```
Task: Implement Issue #101
Description: Agent-1 working on authentication
Prompt: You are agent-1. Your assignment:

Issue: #101 - Add user authentication
Branch: feature/101-add-auth
Worktree: ./worktrees/agent-1

Instructions:
1. cd ./worktrees/agent-1
2. git checkout -b feature/101-add-auth origin/main
3. Read issue with: gh issue view 101
4. Implement the feature completely
5. Write comprehensive tests
6. Create PR when done

Report back with:
STATUS: working/complete/blocked
PROGRESS: What you've done
PR: Link when created

Follow the agent instructions in agent-prompt.md.
```

## Step 5: Orchestrator Monitors Progress

Orchestrator continuously checks on agents:

```
# Every 30 seconds, orchestrator runs:

Task: Check Agent-1 Progress
Description: Status check
Prompt: You are agent-1. Report your current status on issue #101:
- STATUS: working/complete/blocked
- PROGRESS: What you've accomplished
- BLOCKERS: Any issues
- PR: Link if created
```

## Step 6: Handling Inter-Agent Communication

If agent-1 makes a breaking change:

```
# Agent-1 reports:
BREAKING CHANGE ALERT
FILE: src/models/user.ts
CHANGE: Added required 'role' field to User interface
AFFECTS: Any code creating User objects
```

Orchestrator relays to agent-2:

```
Task: Breaking Change Notice
Description: Notify agent-2
Prompt: You are agent-2. 

BREAKING CHANGE from agent-1:
- File: src/models/user.ts  
- Change: Added required 'role' field to User interface
- Impact: Update any User object creation

Please acknowledge and update your code if needed.
```

## Step 7: Review Phase

When all agents complete:

```
Task: Holistic Architecture Review
Description: Review multiple PRs
Prompt: You are the architect reviewer. Review these PRs together:

PR #456 (Issue #101): Add user authentication
PR #457 (Issue #103): Add audit logging

Check for:
1. Integration conflicts
2. Architectural consistency
3. Shared resource conflicts

For each PR, decide:
- APPROVE
- APPROVE_WITH_ISSUE (create follow-up)
- REJECT (request changes)

Follow architect-reviewer-prompt.md for detailed procedures.
```

## Step 8: Post-Mortem

After workflow completes:

```
Task: Post-Mortem Analysis
Description: Extract learnings
Prompt: Analyze this workflow for improvements:

Metrics:
- Total time: 4 hours
- Issues completed: 4/4
- Agent utilization: 65%
- Rework required: 1 PR

Timeline:
[paste timeline events]

Extract:
1. What went well
2. What could improve
3. Actionable recommendations

Follow post-mortem-analyst-prompt.md.
```

## Key Points

1. **One orchestrator instance** manages everything
2. **Agents are spawned** using Task tool
3. **State is tracked** in a simple YAML file
4. **Communication happens** through orchestrator
5. **No background work** - orchestrator drives everything

## Tips for Success

- Keep state file updated after each action
- Check agents frequently (every 30-60 seconds)
- Use clear, specific prompts when spawning agents
- Include relevant prompt templates in agent instructions
- Let agents work autonomously but monitor progress
- Handle errors immediately (fail fast)

## Common Patterns

### Checking if Agent is Done
```
Task: Quick Status Check
Prompt: Agent-1, are you complete with issue #101? Reply with just "STATUS: complete" or "STATUS: working".
```

### Debugging Blocked Agent
```
Task: Investigate Blocker
Prompt: Agent-1, you reported being blocked. Show me:
1. The exact error message
2. What you've tried
3. What you think the issue is
```

### Coordinating Merge Order
```
After reviews, tell each agent:

Task: Merge Preparation
Prompt: Agent-1, your PR is approved. Please:
1. Rebase on latest main: git pull --rebase origin main
2. Push updates
3. Report when ready to merge
```

This approach uses only Claude Code's native capabilities - no custom software needed!
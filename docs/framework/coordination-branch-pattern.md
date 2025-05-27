# Coordination Branch Pattern for MAWEP

## Overview

A coordination branch provides a shared communication channel for agents working in parallel, reducing orchestrator overhead and enabling direct agent coordination.

## Setup

The orchestrator creates a coordination branch at startup:

```bash
git checkout -b mawep/coordination
mkdir .mawep
touch .mawep/interfaces.ts
touch .mawep/breaking-changes.md
touch .mawep/agent-status.yaml
git add .mawep
git commit -m "Initialize MAWEP coordination branch"
git push -u origin mawep/coordination
```

## Structure

```
.mawep/
├── interfaces.ts       # Shared TypeScript interfaces
├── breaking-changes.md # Log of breaking changes
├── agent-status.yaml   # Agent progress tracking
└── contracts/          # API contracts between modules
    ├── auth-api.md
    └── user-api.md
```

## Agent Workflow

### 1. Each agent's worktree tracks coordination branch

```bash
# In agent-1 worktree
git remote add coord origin
git fetch coord mawep/coordination
git checkout -b coordination --track coord/mawep/coordination
```

### 2. When creating a shared interface

```bash
# Agent-1 working on auth
cd ./worktrees/agent-1
git checkout coordination
cat >> .mawep/interfaces.ts << 'EOF'
// Added by agent-1 for issue #101
export interface User {
  id: string;
  email: string;
  role: 'admin' | 'user';  // BREAKING: Added required role field
}
EOF
git add .mawep/interfaces.ts
git commit -m "agent-1: Add User interface with role field"
git push coord coordination
git checkout feature/101-add-auth  # Back to feature branch
```

### 3. Other agents pull changes

```bash
# Agent-2 needs User interface
git checkout coordination
git pull coord coordination
# Now can import { User } from '../.mawep/interfaces'
git checkout feature/102-permissions
```

### 4. Status updates in coordination branch

```yaml
# .mawep/agent-status.yaml
agent-1:
  issue: 101
  status: working
  progress: "Implemented JWT, working on middleware"
  last_update: "2024-01-15T10:30:00Z"
  
agent-2:
  issue: 102
  status: blocked
  progress: "Waiting for User interface"
  blocker: "Need role field in User type"
  last_update: "2024-01-15T10:25:00Z"
```

## Orchestrator Adaptations

### Modified Continuous Loop

```python
# Orchestrator checks coordination branch instead of invoking each agent
while not all_work_complete():
    # Pull latest coordination branch
    git_pull("mawep/coordination")
    
    # Read agent status file
    status = read_file(".mawep/agent-status.yaml")
    
    # Only invoke agents that are blocked or idle
    for agent in status:
        if agent.status == "blocked":
            invoke_agent_to_resolve_blocker(agent)
        elif agent.status == "idle" and has_ready_issues():
            assign_next_issue(agent)
    
    # Check every 2 minutes instead of 30 seconds
    sleep(120)
```

### Conflict Resolution

The coordination branch could have conflicts when multiple agents update simultaneously:

```bash
# Agent should pull before pushing
git checkout coordination
git pull coord coordination --rebase
# Resolve any conflicts
git push coord coordination
```

## Benefits

1. **Reduced orchestrator overhead** - Less frequent agent invocation
2. **Direct agent communication** - Via shared files
3. **Real-time interface sharing** - No waiting for orchestrator relay
4. **Persistent communication log** - Git history shows all coordination
5. **Parallel status updates** - Agents update independently

## Challenges

1. **Merge conflicts** - Multiple agents updating same files
2. **Race conditions** - Agents might miss recent updates
3. **Additional complexity** - Agents must manage two branches
4. **Git expertise required** - Agents need to handle rebasing

## Implementation Decision

### Option A: Keep Current Design (Recommended)
- Simpler agent logic
- Orchestrator maintains full control
- No git conflicts to resolve
- Clear communication flow

### Option B: Add Coordination Branch
- More autonomous agents
- Reduced orchestrator load
- Better for 5+ parallel agents
- Requires more sophisticated agents

## Hybrid Approach

Use coordination branch only for:
1. Interface definitions
2. Breaking change announcements
3. Shared type definitions

Keep orchestrator for:
1. Status monitoring
2. Issue assignment
3. Blocker resolution
4. Review coordination

This provides benefits without full complexity.
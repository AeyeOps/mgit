# MAWEP Orchestration Plan for mgit Refactoring

## Initial Setup

```yaml
# mawep-state.yaml
agents:
  agent-1:
    status: idle
    current_issue: null
    worktree_path: ./worktrees/agent-1
  agent-2:
    status: idle
    current_issue: null
    worktree_path: ./worktrees/agent-2
  agent-3:
    status: idle
    current_issue: null
    worktree_path: ./worktrees/agent-3
  agent-4:
    status: idle
    current_issue: null
    worktree_path: ./worktrees/agent-4
  agent-5:
    status: idle
    current_issue: null
    worktree_path: ./worktrees/agent-5

issues:
  1:
    title: "Create package structure"
    status: ready
    assigned_to: null
    dependencies: []
    priority: P0
  2:
    title: "Extract logging module"
    status: blocked
    assigned_to: null
    dependencies: [1]
    priority: P1
  # ... (all 30 issues)
```

## Orchestration Commands

### Phase 1: Foundation (Critical)

```bash
# Create worktrees
git worktree add ./worktrees/agent-1 -b foundation-work

# Assign critical path work
# Agent 1: Issue #1 (Package Structure)
```

**Orchestrator message to Agent-1:**
```
Task: Implement Issue #1
Description: Create package structure for mgit
Prompt: You are agent-1. Your assignment:

Issue: #1 - Create package structure for mgit
Branch: feature/1-package-structure
Worktree: ./worktrees/agent-1

This is THE CRITICAL PATH - all other work depends on this.

Instructions:
1. cd ./worktrees/agent-1
2. git checkout -b feature/1-package-structure origin/main
3. Create the package structure as defined in the issue
4. Move mgit.py to mgit/__main__.py
5. Update setup.py/pyproject.toml
6. Ensure mgit command still works
7. Create comprehensive PR

Report: STATUS when complete - this unblocks 29 other issues!
```

### Phase 2: Core Module Blitz (5 Parallel Agents)

Once Issue #1 is complete:

```bash
# Create worktrees for parallel work
git worktree add ./worktrees/agent-2 -b logging-work
git worktree add ./worktrees/agent-3 -b config-work
git worktree add ./worktrees/agent-4 -b utils-work
git worktree add ./worktrees/agent-5 -b cli-work
```

**Spawn all 5 agents simultaneously:**

```
Task: Core Module Extraction Batch
Description: 5 agents working on core modules in parallel

Agent-1: Issue #2 (Logging) + Issue #6 (Constants)
Agent-2: Issue #3 (Config) [CRITICAL PATH]
Agent-3: Issue #4 (Utils)
Agent-4: Issue #5 (CLI)
Agent-5: Issue #23 (Error Handling)
```

### Phase 3: Provider & Git Systems

**Architectural Analysis First:**
```
Task: Provider Architecture Analysis
Description: Analyze provider system design
Prompt: Review these provider-related issues (#7-#12):

- Issue #7: Provider Interface (foundation)
- Issue #8: Azure DevOps Provider
- Issue #9: Provider Registry
- Issue #10: Provider Config
- Issue #11: GitHub Stub
- Issue #12: BitBucket Stub

Check for:
1. Interface design patterns
2. Shared configuration approach
3. Registry patterns
4. Authentication handling

Report if foundation patterns are needed before parallel work.
```

### Continuous Monitoring Loop

```python
# Orchestrator's main loop
while not all_issues_complete():
    # Check each agent
    for agent in agents:
        if agent.status == "working":
            check_progress(agent)
        elif agent.status == "idle":
            assign_next_available_issue(agent)
    
    # Handle completions
    for completed in get_completed_issues():
        update_dependent_issues(completed)
        reassign_agent(completed.agent)
    
    # Check for blockers
    handle_blocked_agents()
    
    sleep(60)  # Check every minute
```

## Communication Templates

### Breaking Change Alert
```
Agent-2 working on Config module reports:

BREAKING CHANGE ALERT
FILE: mgit/config/manager.py
CHANGE: ConfigManager now requires provider parameter
AFFECTS: All provider implementations
MIGRATION: Pass provider_name to ConfigManager.__init__()
```

### Progress Report
```
ORCHESTRATOR STATUS - Sprint 2
Time Elapsed: 2 hours

ACTIVE:
- Agent-1: Issue #2 (Logging) - 80% complete
- Agent-2: Issue #3 (Config) - 60% complete [CRITICAL PATH]
- Agent-3: Issue #4 (Utils) - Complete, PR #101 created
- Agent-4: Issue #5 (CLI) - 70% complete
- Agent-5: Issue #23 (Errors) - 50% complete

COMPLETED: 1/30 issues
BLOCKED: None
ESTIMATED COMPLETION: 11 hours
```

## Review Coordination

When multiple PRs are ready:

```
Task: Holistic Architecture Review
Description: Review 5 PRs from core module sprint

PRs to review:
- PR #101: Issue #2 - Logging module
- PR #102: Issue #3 - Config module [CRITICAL]
- PR #103: Issue #4 - Utils
- PR #104: Issue #5 - CLI module
- PR #105: Issue #23 - Error handling

Check for:
1. Consistent import patterns
2. Naming conventions
3. Integration conflicts
4. Shared dependencies

Priority: Config module is on critical path
```

## Success Metrics

- **Parallelization Efficiency**: 5 agents working simultaneously
- **Critical Path Management**: Config → YAML → Schema prioritized
- **Dependency Resolution**: No agent idle due to dependencies
- **Communication Events**: ~50 (status updates + breaking changes)
- **Total Duration Target**: 13-15 hours with 5 agents

## Risk Mitigation

1. **Config System Conflicts**: Agent-2 defines patterns early
2. **Import Circular Dependencies**: Review after each sprint
3. **Provider Interface Changes**: Lock interface in Issue #7
4. **Testing Infrastructure**: Set up pytest early (Issue #26)

This orchestration plan maximizes parallelization while managing dependencies and ensuring quality through structured reviews.
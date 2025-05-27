# Starting MAWEP for mgit Refactoring

## Step 1: Create Issues in Bitbucket

First, update and run the script to create issues:

```bash
# Edit the script with your credentials
nano /opt/aeo/mgit/scripts/create-bitbucket-issues.py

# Update these lines:
BITBUCKET_WORKSPACE = "pdisoftware"
BITBUCKET_REPO_SLUG = "mgit"  
BITBUCKET_TOKEN = "ATBBujULJrt3ZYfuyEkskJN5BqhY00942C30"  # Or one of your other tokens
BITBUCKET_USERNAME = "your_username"

# Run the script
python3 /opt/aeo/mgit/scripts/create-bitbucket-issues.py
```

## Step 2: Start MAWEP Orchestration

Tell Claude Code:

```
I want you to act as the MAWEP Orchestrator for the mgit refactoring project.

Repository: Bitbucket pdisoftware/mgit
Issues: 30 refactoring issues as documented in /opt/aeo/mgit/docs/refactoring-issues.md

Your job:
1. Create directory: /opt/aeo/mgit/mawep-workspace
2. Set up mawep-state.yaml tracking 5 agents and 30 issues  
3. Review the dependency analysis in /opt/aeo/mgit/mawep-simulation/dependency-analysis.md
4. Start with Issue #1 (Package Structure) - this is critical path
5. Once #1 completes, spawn 5 agents for parallel work on issues #2-6
6. Continue orchestrating according to the plan in orchestration-plan.md

Use the Task tool to spawn agents. Each agent should:
- Work in their own git worktree
- Follow the patterns in @docs/framework/prompts/agent-prompt.md
- Report progress back to you

Start by creating the workspace and assigning agent-1 to Issue #1.
```

## Step 3: Monitor Progress

Ask the orchestrator periodically:
```
Show me the current status of all agents and issues.
What's the critical path progress?
Are there any blockers?
```

## Step 4: Example Agent Spawn

The orchestrator will spawn agents like this:

```
Task: Implement Issue #1 - Package Structure
Description: Critical foundation work
Prompt: You are agent-1 working on the critical package structure issue.

Repository: /opt/aeo/mgit
Issue: #1 - Create package structure for mgit
Branch: feature/1-package-structure  
Worktree: /opt/aeo/mgit/mawep-workspace/worktrees/agent-1

Read the full issue details in /opt/aeo/mgit/docs/refactoring-issues.md

Your task:
1. cd to your worktree
2. Create feature branch
3. Implement the package structure exactly as specified
4. Move mgit.py to mgit/__main__.py
5. Update setup.py or create pyproject.toml
6. Test that 'mgit' command still works
7. Commit and push your changes
8. Create a PR

This is CRITICAL PATH - all other work depends on you. Report:
STATUS: working/complete/blocked
PROGRESS: Details of what you've done
PR: Link when created
```

## Step 5: Parallel Phase

After Issue #1 completes, orchestrator spawns 5 agents simultaneously:

```
Task: Parallel Core Module Development
Description: 5 agents working on core modules

You are agent-2. Work on Issue #3 (Config Module).
You are agent-3. Work on Issue #4 (Utils).
You are agent-4. Work on Issue #5 (CLI).
You are agent-5. Work on Issue #2 (Logging).
[Fifth agent gets Issue #6]

All agents: 
- Pull latest main (has package structure now)
- Work in your assigned worktree
- Follow the modular structure created by Issue #1
- Report progress every 30 minutes
```

## Key Points

1. **Issue #1 is critical** - Everything depends on it
2. **Maximum parallelization** happens in Sprint 2 (5 agents)
3. **Config module** (#3) is on the critical path
4. **Provider interface** (#7) blocks all provider work
5. **MAWEP components** (#19-22) can be done later

## Expected Timeline

With 5 agents working optimally:
- Sprint 1 (Issue #1): 2 hours
- Sprint 2 (Issues #2-6): 2-3 hours  
- Sprint 3 (Mixed work): 3-4 hours
- Sprint 4 (Providers): 2-3 hours
- Remaining work: 4-5 hours
- **Total: 13-17 hours**

## Success Criteria

- All 30 issues implemented
- No merge conflicts
- Tests passing
- Documentation updated
- Clean modular architecture
- Multi-provider support ready
- MAWEP integration complete

Start the orchestration and let the swarm begin!
# Sprint 2 Assignments - Parallel Core Module Extraction

## Agent Assignments

1. **Agent-1**: Issue #96 - Extract logging module
2. **Agent-2**: Issue #98 - Extract configuration module (CRITICAL PATH)
3. **Agent-3**: Issue #100 - Extract utility functions
4. **Agent-4**: Issue #101 - Extract CLI module
5. **Agent-5**: Issue #102 - Create constants module

## Common Instructions for All Agents

1. Pull the latest main (has package structure now)
2. Create your feature branch from main
3. Work in your assigned worktree
4. Extract ONLY your assigned module - don't touch other modules
5. Update imports in __main__.py to use your new module
6. Test that mgit still works after your changes
7. Create PR when complete

## Critical Notes

- Agent-2 (Config) is on critical path - other work depends on this
- Coordinate if you need to modify shared files
- Report any breaking changes immediately
- Keep __main__.py functional at all times
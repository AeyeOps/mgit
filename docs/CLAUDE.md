# CLAUDE.md - mgit Documentation Standards

This file provides guidance for maintaining and extending the specification-driven development process for mgit.

## Directory Structure

```
docs/
├── CLAUDE.md (this file)
├── ADR/                   # Architecture Decision Records
│   ├── 001-provider-abstraction.md
│   ├── 002-configuration-hierarchy.md
│   ├── 003-concurrent-operations.md
│   └── 004-pattern-matching-strategy.md
└── specs/
    ├── multi-provider-support/
    │   ├── overview.md    # Main specification
    │   ├── phases-done/   # Completed implementation phases
    │   └── phases-pending/ # Specifications awaiting implementation
    └── [feature-name]/    # Future feature specifications
        ├── overview.md
        ├── phases-done/
        └── phases-pending/
```

## Documentation Philosophy

mgit follows a **specification-first, phase-driven** approach to development:

1. **Specifications Define Intent**: Major features begin with comprehensive specs
2. **Phases Enable Incremental Progress**: Large features broken into manageable phases
3. **ADRs Document Architecture**: Key decisions preserved for future reference
4. **Provider Abstraction First**: All features must work across Azure DevOps, GitHub, and BitBucket

## Phase Specification Standards

### Required Sections
Every phase specification MUST include these sections in order:

1. **# Phase N: [Descriptive Title]**
2. **## Objective** - Single sentence stating what this phase accomplishes
3. **## Problem Summary** - Brief description of the issue being solved
4. **## Implementation Details** - Exact changes with file paths and line numbers
5. **## Agent Workflow** - Step-by-step instructions for implementation
6. **## Testing** - How to verify the implementation works
7. **## Success Criteria** - Checklist of completion requirements

### Implementation Details Format
```markdown
### File: `/opt/aeo/mgit/mgit/[module].py`

**Change N: [Description]**
**Location:** Line XXX
**Current Code:**
```python
[exact current code]
```

**New Code:**
```python
[exact new code]
```
```

### mgit-Specific Guidelines

1. **Poetry-First Development**
   - Always use `poetry run mgit` for testing
   - Include Poetry commands in testing steps
   - Reference pyproject.toml for dependencies

2. **Provider-Agnostic Design**
   - Phases must consider all three providers (Azure DevOps, GitHub, BitBucket)
   - Test against provider-specific patterns
   - Document provider differences in specifications

3. **Pattern Matching Focus**
   - Specifications should address org/project/repo patterns
   - Consider wildcard behavior across providers
   - Test multi-provider query scenarios

4. **Async Operation Handling**
   - Each phase must handle async/await properly
   - Consider event loop management
   - Document concurrency implications

## Key Principles

1. **Precision Over Ambiguity**
   - Use exact line numbers, not "around line X"
   - Show complete code snippets, not fragments
   - Specify absolute file paths starting with `/opt/aeo/mgit/`

2. **Incremental Progress**
   - Each phase should be completable in 1-2 hours
   - Phases build on each other but remain independent
   - Critical fixes before enhancements

3. **Provider Compatibility**
   - Every feature must work with all three providers
   - Document provider-specific behavior
   - Include provider-specific test cases

4. **Test-Driven Validation**
   - Every phase includes testing requirements
   - Test all three providers when applicable
   - Include manual testing checklists with actual commands

## Workflow Process

### Creating a New Phase Spec

1. **Identify the Problem**
   - Check existing ADRs for architectural guidance
   - Verify compatibility across all providers
   - Determine criticality (blocking vs enhancement)

2. **Draft the Specification**
   - Use existing phase specs as templates
   - Verify line numbers by reading actual files
   - Include before/after code snippets
   - Test commands with `poetry run mgit`

3. **Implementation**
   - Execute the agent workflow steps
   - Run specified tests using Poetry
   - Test against all three providers
   - Check all success criteria
   - Move spec to `phases-done/` when complete

### Phase Naming Convention

```
phase-[N]-[descriptive-kebab-case].md
```

Examples:
- `phase-1-gitlab-provider-support.md`
- `phase-2-collection-management.md`
- `phase-3-recursive-clone-operations.md`

## Architecture Decision Records (ADRs)

ADRs document key architectural and design decisions for mgit:

### Required ADR Structure
1. **# ADR-XXX: [Title]**
2. **## Status** - Proposed/Accepted/Deprecated
3. **## Context** - The situation requiring a decision
4. **## Decision** - What was decided
5. **## Consequences** - Results of this decision
6. **## Related** - Links to related ADRs or specs

### ADR Naming Convention
```
XXX-kebab-case-title.md
```

Examples:
- `001-provider-abstraction.md`
- `002-configuration-hierarchy.md`
- `003-concurrent-operations.md`

## Quality Standards

### DO:
- ✅ Include exact line numbers from actual code
- ✅ Show complete function signatures in changes
- ✅ Provide testable success criteria using `poetry run`
- ✅ Test against all three providers
- ✅ Reference relevant ADRs and policies
- ✅ Keep phases focused on single concerns
- ✅ Document provider-specific behavior
- ✅ Include async/concurrent scenarios

### DON'T:
- ❌ Use vague descriptions like "update the function"
- ❌ Omit testing requirements
- ❌ Combine unrelated changes in one phase
- ❌ Create phases larger than 2 hours of work
- ❌ Skip provider compatibility testing
- ❌ Ignore event loop implications
- ❌ Assume provider behavior is identical

## mgit Testing Standards

### CLI Integration Tests
```bash
# Verify basic functionality
poetry run mgit --version
poetry run mgit list "*/*/*" --limit 5

# Test with different providers
poetry run mgit list "org/*/*" --provider github_work
poetry run mgit list "org/*/*" --provider azdo_enterprise
poetry run mgit list "org/*/*" --provider bitbucket_team

# Test pattern matching
poetry run mgit list "*/project/*"
poetry run mgit list "*/*/*-api"
```

### Manual Testing Checklist Template
- [ ] Command executes without errors
- [ ] Works with Azure DevOps provider
- [ ] Works with GitHub provider
- [ ] Works with BitBucket provider
- [ ] Pattern matching behaves correctly
- [ ] Concurrent operations complete successfully
- [ ] JSON output (if applicable) is valid
- [ ] Help text is accurate: `poetry run mgit [command] --help`

## Example Phase Spec Template

```markdown
# Phase N: [Title]

## Objective
[Single sentence goal related to mgit functionality]

## Problem Summary
[2-3 sentences describing the repository management issue]

## Implementation Details

### File: `/opt/aeo/mgit/mgit/providers/[provider].py`

**Change 1: [What changes]**
**Location:** Line XXX
**Current Code:**
```python
[current code]
```

**New Code:**
```python
[new code]
```

## Agent Workflow

### Step 1: [Action]
1. [Specific instruction using poetry run]
2. [Specific instruction]
3. [Verification for each provider]

### Step 2: [Action]
1. [Specific instruction]
2. [Test with concurrent operations]

## Testing

### CLI Integration Tests
```bash
poetry run mgit list "org/*/*" --provider github
poetry run mgit sync "org/*/*" ./test --concurrency 5
```

### Manual Testing
- [ ] [Test scenario 1 with actual command]
- [ ] [Test scenario 2 with error case]
- [ ] [Verification across all providers]

## Success Criteria
- [ ] [Criterion 1 with measurable outcome]
- [ ] [Criterion 2 tested via CLI]
- [ ] All commands execute without errors
- [ ] No regressions in existing functionality
- [ ] Works with all three providers
- [ ] Handles concurrent operations correctly
```

## Maintenance Guidelines

### Weekly Review
- Move completed specs from `phases-pending/` to `phases-done/`
- Archive obsolete specs with `OBSOLETE-` prefix
- Update phase numbers if reordering needed
- Test all documented commands still work

### Documentation Updates
- Update main spec document when phases complete
- Keep running list of completed phases in overview
- Document lessons learned about provider differences

## mgit-Specific Tips

1. **Always Test with Poetry**: Use `poetry run mgit` not `python -m mgit`
2. **Test All Providers**: Each feature must work with Azure DevOps, GitHub, and BitBucket
3. **Verify Pattern Matching**: Test wildcards and specific patterns
4. **Check Concurrency**: Test with different concurrency levels
5. **Document Provider Differences**: Not all providers behave the same way
6. **Handle Async Properly**: Event loop management is critical

## Common Pitfalls to Avoid

1. **Stale Line Numbers**: Code changes, verify before implementation
2. **Missing Poetry Usage**: Always use Poetry commands in testing
3. **Single Provider Testing**: Must test all three providers
4. **Ignoring Event Loops**: Async operations need careful handling
5. **Assuming Provider Parity**: Each provider has unique behaviors
6. **Pattern Matching Edge Cases**: Test wildcards thoroughly

## Questions or Improvements?

This process is designed to evolve with mgit's needs. If you identify improvements:
1. Create an ADR proposing the change
2. Update this CLAUDE.md file
3. Apply the new process to future phases

Remember: The goal is sustainable, incremental progress with high confidence in each change while maintaining mgit's multi-provider capability and performance.

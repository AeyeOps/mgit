# Phase 1 Fix: File-Level JSONL Output

## Current State
The `mgit diff` command EXISTS but outputs wrong format:
- Currently outputs: One large JSON per repository
- Need to output: One JSON line per file change

## Required Changes

### Keep These Parts
1. Command registration in `mgit/__main__.py` - already correct
2. GitManager methods in `mgit/git/manager.py` - working fine
3. Basic structure of `mgit/commands/diff.py` - just needs output changes

### Fix Output Format in `mgit/commands/diff.py`

The `_write_changes_jsonl` function (around line 377) needs complete replacement.

**Current behavior:** Outputs entire RepositoryChange object as one JSON
**Required behavior:** Output individual file changes as separate JSON lines

## New Output Format

For each repository with changes:
1. Output one JSON line per file change
2. Include repository name in each line
3. At end of repository, output changeset record

Example output stream:
```json
{"repo": "mgit", "op": "modify", "path": ".gitignore"}
{"repo": "mgit", "op": "delete", "path": ".serena/project.yml"}
{"repo": "mgit", "op": "modify", "path": "mgit/__main__.py"}
{"repo": "mgit", "op": "add", "path": "docs/CLAUDE.md"}
{"repo": "mgit", "new_changeset": {"commit": "d59cfbf", "branch": "main"}}
```

## Implementation Focus

Replace the `_write_changes_jsonl` function to:
1. Iterate through each RepositoryChange
2. For each uncommitted_file in the change:
   - Output a file-level JSON with repo, op, path
   - Map git status codes to operations (add/modify/delete)
3. After all files, output the changeset record

## Key Mapping
Git status to operation mapping:
- 'A' or 'added' -> "add"
- 'M' or 'modified' -> "modify"  
- 'D' or 'deleted' -> "delete"
- '??' or 'untracked' -> "add"
- 'renamed' -> "modify"

## Testing
After implementation, verify:
```bash
poetry run mgit diff . | head -5
# Should show individual file changes, not repository summaries
```

## Note on Content
Phase 1 does NOT include file content - just operations and paths.
Phase 3 will add the three-tier content strategy (content/content_base64/content_ref).
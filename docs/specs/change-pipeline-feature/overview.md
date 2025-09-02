# Repository Change Detection and Streaming

## Overview
mgit extends its multi-repository orchestration capabilities with change detection and streaming. The `mgit diff` command produces standardized change streams that can be consumed by any downstream tool for synchronization, analysis, or indexing.

## Design Principles
- **Tool-agnostic output**: Standard JSONL that any consumer can parse
- **Composable**: Works with pipes, files, and other Unix tools  
- **Stateful tracking**: Maintains changesets for incremental operations
- **Provider-unified**: Same output format regardless of Git provider

## Use Cases
- Incremental synchronization to search indexes
- Change-based CI/CD triggers
- Audit trail generation
- Repository analytics
- Migration tracking
- Any tool needing repository deltas

## Output Consumers (Examples)
- elysiactl index sync - Weaviate indexing
- jq - JSON processing
- Splunk - Log aggregation
- Custom analytics pipelines
- Backup systems

## The Key Insight

mgit is building a general-purpose capability that happens to solve elysiactl's need. Tomorrow someone could use the same output for:
- Sending changes to Elasticsearch
- Feeding a metrics system
- Triggering workflows
- Generating audit reports

## What This Means

1. No mention of Weaviate, vectors, or indexing in mgit docs
2. Focus on the change detection problem mgit solves
3. Document the output contract without assuming the consumer
4. Use generic examples that show various use cases

## Example Usage Patterns

```bash
# Various ways to consume mgit diff output

# Send to a search indexer
mgit diff /repos --format=jsonl | search-indexer --update

# Generate audit report  
mgit diff /repos --since=yesterday | jq '.path' > changed-files.txt

# Trigger CI/CD for changed services
mgit diff /repos | jq -r '.repo' | sort -u | xargs -I{} trigger-build {}

# Archive changes
mgit diff /repos --include-content | zstd > changes-$(date +%Y%m%d).jsonl.zst

# Feed to analytics system
mgit diff /repos --format=jsonl | kafka-producer --topic=repo-changes

# Generate migration manifest
mgit diff /repos --from-changeset=old --to-changeset=new > migration.jsonl

# Security scanning on changed files
mgit diff /repos | jq -r 'select(.op != "delete") | .path' | xargs security-scan

# Backup only changed files
mgit diff /repos | jq -r '.path' | tar -czf changed-files.tar.gz -T -
```

## Architecture Components

### Change Detection (`mgit diff`)
Generates deltas between stored changesets and current repository state.

### Changeset Store
Tracks last synchronized state for each repository, enabling incremental operations.

### Output Format
Pure JSONL with standardized schema, making it consumable by any JSON-aware tool.

## Output Contract

Each line in the JSONL stream represents a single file change operation:

```json
{
  "repo": "ServiceA",
  "op": "modify",
  "path": "src/main.py",
  "size": 1234,
  "mime": "text/x-python",
  "content": "...",         // For small files (0-10KB)
  "content_base64": "...",  // For medium files (10-100KB)
  "content_ref": "..."      // For large files (100KB+)
}
```

Additional fields for binary/special files:
```json
{
  "repo": "ServiceA",
  "op": "add",
  "path": "logo.png",
  "size": 45678,
  "mime": "image/png",
  "skip_index": true,       // Binary files not for indexing
  "content_base64": "..."   // If under 100KB
}
```

Changeset records mark repository completion:
```json
{
  "repo": "ServiceA",
  "new_changeset": {
    "commit": "abc123",
    "parent": "def456",
    "branch": "main"
  }
}
```

**Note:** mgit does NOT include line numbers. Consumers add them if needed for their own checkpoint tracking.

## Performance Optimizations

### Smart Content Strategy
- 0-10KB: Embed as plain text
- 10-100KB: Embed as base64
- 100KB+: Provide file reference

This reduces I/O operations by 80-90% for typical source code repositories.

### Streaming Design
- Line-by-line processing capability
- No memory accumulation
- Resumable via line numbers
- Compress-friendly format

## Implementation Phases

### Phase 1: Basic Change Detection
- Simple file list output
- Add/modify/delete operations
- Repository-aware processing

### Phase 2: Changeset Management
- Persistent state tracking
- Incremental diff generation
- Multi-repository coordination

### Phase 3: Content Embedding
- Smart three-tier strategy
- MIME type detection
- Binary file handling

### Phase 4: Production Features
- Compression support
- Parallel processing
- Validation passes
- Error recovery

## Why mgit for Change Detection

mgit is uniquely positioned to provide change detection because it already:
- **Manages auth** across GitHub, Azure DevOps, BitBucket
- **Handles scale** with concurrent operations on 100+ repos
- **Unifies providers** behind consistent interface
- **Knows structure** of repository relationships

Adding change detection leverages these capabilities to answer: "What changed across my fleet?"

## Why This Matters

Traditional repository management tools focus on executing commands across repositories. mgit's change detection fills a gap by providing:

1. **Standardized change streams** - Not tied to any specific consumer
2. **Incremental processing** - Only process what changed
3. **Provider abstraction** - Same output whether from GitHub, Azure DevOps, or BitBucket
4. **Composable architecture** - Fits into any Unix pipeline

This positions mgit as the bridge between Git repositories and any system that needs to track changes, without coupling to specific downstream tools.

## Related Documentation

- [Changeset Tracking Specification](phases-pending/changeset-spec.md)
- [Diff Command Specification](phases-pending/diff-command-spec.md)
- [JSONL Format Specification](phases-pending/jsonl-format-spec.md)
# ADR-003: Concurrent Operations Strategy

## Status
Accepted

## Context

mgit performs bulk operations on potentially hundreds of repositories. Sequential processing would be prohibitively slow:
- Cloning 100 repositories sequentially could take hours
- Network latency compounds with each operation
- Users expect reasonable performance for bulk operations

Key constraints:
- Provider API rate limits (GitHub: 5000/hour, Azure DevOps: variable, BitBucket: 1000/hour)
- Memory usage with concurrent operations
- Network bandwidth limitations
- Error handling complexity with parallel operations

## Decision

Implement controlled concurrent operations with:

1. **Configurable concurrency limits**: Default 4, adjustable via `--concurrency`
2. **Provider-specific rate limiting**: 
   - GitHub: 10 concurrent
   - Azure DevOps: 4 concurrent
   - BitBucket: 5 concurrent
3. **Async/await pattern**: Using asyncio for I/O operations
4. **Semaphore-based throttling**: Prevent overwhelming providers
5. **Progress tracking**: Show real-time progress with Rich library

Implementation approach:
```python
async def bulk_operation(repos, concurrency=4):
    semaphore = asyncio.Semaphore(concurrency)
    async with semaphore:
        # Perform operation
```

## Consequences

### Positive:
- **Performance**: 5-10x faster than sequential operations
- **Scalability**: Handles hundreds of repositories efficiently
- **Resource control**: Prevents overwhelming system or APIs
- **User experience**: Progress feedback during long operations

### Negative:
- **Complexity**: Error handling in concurrent contexts
- **Debugging difficulty**: Parallel execution harder to trace
- **Resource usage**: Higher memory/CPU with concurrency
- **Event loop management**: Must handle loop lifecycle carefully

### Neutral:
- Optimal concurrency varies by network and repository size
- Some operations may still bottleneck on disk I/O
- Trade-off between speed and stability

## Related
- ADR-001: Provider abstraction (manages per-provider limits)
- Event loop management failures and solutions
- AsyncExecutor utility implementation
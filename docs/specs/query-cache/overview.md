# Query Cache Overview

## Problem Statement

The `mgit list` command currently makes live API calls to Git providers (Azure DevOps, GitHub, BitBucket) for every query. This creates several issues:

- **Slow response times** for repeated queries
- **API rate limiting** from providers
- **Network dependency** for every operation
- **Inconsistent performance** based on network conditions
- **No offline capability** when network is unavailable

## Solution Vision

Implement a configurable query caching system that:

- **Caches query results** with configurable TTL (Time To Live)
- **Invalidates intelligently** when repository changes are detected
- **Works across providers** with provider-specific cache strategies
- **Supports offline mode** when network is unavailable
- **Provides cache statistics** and management commands

## Core Requirements

### 1. Cache Storage
- **Format**: JSONL format for easy parsing and git-friendly diffs
- **Location**: `~/.cache/mgit/` directory structure
- **Encryption**: Optional encryption for sensitive repository data
- **Compression**: Optional gzip compression for large caches

### 2. Cache Keys
Cache entries identified by:
```
<provider>:<org>:<project>:<repo>:<query_pattern>:<timestamp>
```

Examples:
```
ado_pdidev:pdidev:Blue Cow:*:2024-01-01T10:00:00Z
bitbucket_pdi:cstorepro:*:*:2024-01-01T10:00:00Z
github_personal:myorg:*:*:2024-01-01T10:00:00Z
```

### 3. TTL (Time To Live) Configuration
```yaml
# ~/.config/mgit/cache.yaml
cache:
  enabled: true
  default_ttl: 3600  # 1 hour in seconds
  provider_overrides:
    ado_pdidev:
      ttl: 1800  # 30 minutes
      max_age: 86400  # Keep for 24 hours max
    bitbucket_pdi:
      ttl: 7200  # 2 hours
  offline_mode: false  # Use cache only when offline
```

### 4. Cache Invalidation Strategies

#### Time-based Invalidation
- **TTL expiration**: Automatic cleanup after TTL expires
- **Max age**: Hard limit on cache entry lifetime
- **Last modified**: Check repository last modified time

#### Content-based Invalidation
- **ETag comparison**: Compare provider ETags
- **Last commit check**: Verify latest commit hash
- **Repository count changes**: Detect additions/deletions

#### Manual Invalidation
```bash
# Clear all cache
mgit cache clear

# Clear specific provider
mgit cache clear --provider ado_pdidev

# Clear specific pattern
mgit cache clear --pattern "pdidev/*/*"

# Force refresh specific query
mgit list "pdidev/*/*" --refresh
```

### 5. Cache Performance Optimizations

#### Memory-efficient Storage
- **Pagination support**: Cache large result sets in pages
- **Lazy loading**: Load cache entries on demand
- **Index files**: Separate metadata from data for fast lookups

#### Concurrent Access
- **File locking**: Prevent corruption during concurrent operations
- **Atomic writes**: Write to temp file then rename for consistency
- **Read/write separation**: Allow multiple readers, single writer

## Implementation Phases

### Phase 1: Basic Caching (MVP)
- [ ] Basic file-based cache storage
- [ ] TTL-based expiration
- [ ] Cache hit/miss logging
- [ ] `mgit cache status` command
- [ ] `mgit cache clear` command

### Phase 2: Smart Invalidation
- [ ] ETag-based invalidation
- [ ] Repository change detection
- [ ] `--refresh` flag support
- [ ] Cache statistics tracking

### Phase 3: Advanced Features
- [ ] Offline mode support
- [ ] Compression options
- [ ] Cache size limits and cleanup
- [ ] Provider-specific strategies

### Phase 4: Performance Optimization
- [ ] Memory-efficient pagination
- [ ] Concurrent access handling
- [ ] Index optimization
- [ ] Cache preheating

## Cache Data Structure

### Cache Entry Format
```json
{
  "cache_key": "ado_pdidev:pdidev:Blue Cow:*:2024-01-01T10:00:00Z",
  "query_pattern": "pdidev/Blue Cow/*",
  "provider": "ado_pdidev",
  "created_at": "2024-01-01T10:00:00Z",
  "expires_at": "2024-01-01T11:00:00Z",
  "etag": "W/\"abc123\"",
  "result_count": 5,
  "repositories": [
    {
      "organization": "pdidev",
      "project": "Blue Cow",
      "repository": "automation_smoke_signals",
      "clone_url": "https://pdidev.visualstudio.com/DefaultCollection/Blue%20Cow/_git/automation_smoke_signals",
      "default_branch": "refs/heads/master",
      "is_private": true,
      "last_modified": "2024-01-01T09:30:00Z"
    }
  ]
}
```

### Cache Index Format
```json
{
  "version": "1.0",
  "created_at": "2024-01-01T10:00:00Z",
  "total_entries": 150,
  "total_size_mb": 25.5,
  "providers": {
    "ado_pdidev": {
      "entries": 75,
      "size_mb": 12.3,
      "oldest_entry": "2024-01-01T08:00:00Z",
      "newest_entry": "2024-01-01T10:00:00Z"
    }
  }
}
```

## CLI Integration

### New Commands
```bash
# Cache management
mgit cache status                    # Show cache statistics
mgit cache clear                     # Clear all cache
mgit cache clear --provider <name>   # Clear specific provider
mgit cache clear --pattern <pattern> # Clear pattern matches
mgit cache preload <pattern>         # Preload cache for pattern

# Cache-aware list commands
mgit list "pdidev/*/*" --cache-only  # Use cache only (offline mode)
mgit list "pdidev/*/*" --refresh     # Force cache refresh
mgit list "pdidev/*/*" --no-cache    # Skip cache, force live query
```

### Enhanced Existing Commands
```bash
# Show cache status in verbose output
mgit list "pdidev/*/*" --verbose

# Cache configuration
mgit config cache.enabled true
mgit config cache.default_ttl 3600
```

## Performance Expectations

### Expected Improvements
- **First query**: Same as current (live API call)
- **Subsequent queries**: 10-100x faster (cache hit)
- **Offline mode**: Full functionality without network
- **Rate limiting**: 90% reduction in API calls
- **Large queries**: Cached results return instantly

### Memory/Disk Usage
- **Small teams**: < 10MB cache
- **Medium teams**: 50-200MB cache
- **Large enterprises**: 500MB+ cache (with compression)
- **Retention**: Configurable cleanup policies

## Security Considerations

- **Sensitive data**: Repository URLs may contain tokens
- **Encryption**: Optional cache encryption
- **Access control**: File permissions on cache directory
- **Cleanup**: Secure deletion of expired entries

## Migration Strategy

1. **Opt-in initially**: Cache disabled by default
2. **Gradual rollout**: Enable for individual providers
3. **Backward compatibility**: No breaking changes to existing commands
4. **Migration tools**: Import existing result data if available

## Success Metrics

- **Cache hit rate**: > 80% for repeated queries
- **Query time improvement**: > 10x for cache hits
- **User satisfaction**: Reduced wait times
- **API usage reduction**: > 70% reduction in API calls
- **Offline capability**: Full functionality without network

## Future Enhancements

- **Distributed caching**: Redis/memcached support
- **Smart prefetching**: Predict and cache likely queries
- **Cache sharing**: Share cache between team members
- **Machine learning**: Learn query patterns for optimization
- **Provider webhooks**: Real-time cache invalidation
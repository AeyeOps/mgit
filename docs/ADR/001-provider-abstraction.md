# ADR-001: Provider Abstraction Strategy

## Status
Accepted

## Context

mgit needs to support multiple Git providers (Azure DevOps, GitHub, BitBucket) with a unified interface. Each provider has:
- Different API structures and authentication methods
- Unique organizational hierarchies (org/project/repo vs org/repo)
- Varying rate limits and operational constraints
- Provider-specific features and limitations

Key challenges:
- Azure DevOps uses PAT with organization URLs
- GitHub uses tokens with api.github.com
- BitBucket uses app passwords with workspace concepts
- Pattern matching must work consistently across all providers

## Decision

Implement a provider abstraction layer with:

1. **Common Interface**: All providers implement `GitProvider` base class
2. **Factory Pattern**: Provider factory creates instances based on configuration
3. **Provider Registry**: Central registry manages available providers
4. **Configuration Isolation**: Each provider has named configuration instances

Key design choices:
- Providers are stateless - new instances created per operation
- Event loop management handled per operation to avoid conflicts
- Provider-specific logic isolated in provider modules
- CLI layer remains provider-agnostic

## Implementation

### Provider Interface:
```python
class GitProvider(ABC):
    async def authenticate() -> bool
    async def list_repositories(pattern: str) -> List[Repository]
    async def clone_repository(repo: Repository, path: str) -> bool
```

### Configuration Structure:
```yaml
providers:
  github_work:
    type: github
    token: ghp_...
  azdo_enterprise:
    type: azuredevops
    pat: ...
    org_url: https://dev.azure.com/org
```

## Consequences

### Positive:
- **Extensibility**: New providers can be added without changing core logic
- **Testability**: Each provider can be tested independently
- **Flexibility**: Multiple configurations per provider type
- **Maintainability**: Provider-specific code isolated from business logic

### Negative:
- **Complexity**: Additional abstraction layer
- **Performance**: Factory instantiation overhead
- **Learning Curve**: Contributors must understand abstraction

### Neutral:
- Provider differences sometimes leak through abstraction
- Pattern matching behavior varies slightly between providers
- Some features may not be available on all providers

## Related

- Configuration hierarchy (ADR-002)
- Pattern matching strategy (ADR-004)
- Event loop management lessons from failures
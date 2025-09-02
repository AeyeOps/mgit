# ADR-002: Configuration Hierarchy

## Status
Accepted

## Context

mgit needs a flexible configuration system to manage multiple Git providers, each potentially having multiple named configurations (e.g., github_personal, github_work). The system must:
- Support multiple provider instances with different credentials
- Allow environment variable overrides for CI/CD
- Maintain secure credential storage
- Enable provider selection via CLI or defaults

## Decision

Implement a three-tier configuration hierarchy with clear precedence:

1. **Command-line arguments** (highest precedence)
   - `--provider NAME` flag for explicit provider selection
2. **Environment variables** (middle precedence)  
   - `AZURE_DEVOPS_EXT_PAT` for legacy Azure DevOps support
   - Security settings like `MGIT_SECURITY_MASK_CREDENTIALS_IN_LOGS`
3. **Configuration files** (lowest precedence)
   - YAML format at `~/.config/mgit/config.yaml`
   - Named provider configurations
   - Default provider setting

Configuration structure:
```yaml
default_provider: github_work
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
- **Multi-instance support**: Multiple configurations per provider type
- **CI/CD friendly**: Environment variables for automation
- **Secure**: Credentials in protected config files (mode 600)
- **Flexible**: Named configurations for different contexts

### Negative:
- **Migration complexity**: JSON to YAML migration required
- **Field mapping**: Provider-specific field names need mapping
- **Discovery burden**: Users must know which config to use

### Neutral:
- Configuration validation required
- Provider selection logic needed
- Backward compatibility considerations

## Related
- ADR-001: Provider abstraction strategy
- Security implementation for credential masking
- YAML migration from JSON configuration
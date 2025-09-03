# Extended Errors Overview

## Problem Statement

The `mgit` CLI currently provides minimal error information, making it difficult for users to:

- **Understand what went wrong** when commands fail
- **Debug authentication issues** across multiple providers
- **Troubleshoot network problems** or rate limiting
- **Identify pattern matching issues** with complex queries
- **Recover from recoverable errors** without trial-and-error

Current error messages are often generic: "No repositories found" or "Authentication failed" without context about which provider, what was attempted, or potential solutions.

## Solution Vision

Implement a comprehensive error reporting system that provides:

- **Contextual error messages** with specific details
- **Multi-format error output** (human-readable, JSON, structured)
- **Recovery suggestions** and actionable next steps
- **Error classification** (fatal vs recoverable, provider-specific vs general)
- **Debug information** for troubleshooting
- **Error chaining** showing the full error path

## Core Requirements

### 1. Error Classification System

#### Error Categories
```python
class ErrorCategory(Enum):
    AUTHENTICATION = "auth"           # Login/token issues
    NETWORK = "network"              # Connectivity problems
    PERMISSION = "permission"        # Access denied
    RATE_LIMIT = "rate_limit"        # API throttling
    CONFIGURATION = "config"         # Setup problems
    VALIDATION = "validation"        # Input validation errors
    PROVIDER_SPECIFIC = "provider"   # Provider API issues
    INTERNAL = "internal"            # mgit bugs
```

#### Error Severity Levels
```python
class ErrorSeverity(Enum):
    DEBUG = "debug"      # Detailed debug info
    INFO = "info"        # Informational messages
    WARNING = "warning"  # Non-fatal issues
    ERROR = "error"      # Operation failed but recoverable
    FATAL = "fatal"      # Operation cannot continue
```

### 2. Structured Error Format

#### Human-Readable Format (Default)
```
❌ Authentication failed for provider 'ado_pdidev'

🔍 Details:
   Provider: Azure DevOps
   Organization: pdidev
   Error Type: Invalid token
   Timestamp: 2024-01-01T10:30:00Z

💡 Suggestions:
   1. Check your PAT token is valid and not expired
   2. Verify token has 'Code (read)' scope
   3. Try: mgit login --provider ado_pdidev --force
   4. Visit: https://dev.azure.com/pdidev/_usersSettings/tokens

🔧 Debug Info:
   Request ID: abc123-def456
   API Endpoint: https://dev.azure.com/pdidev/_apis/projects
   HTTP Status: 401 Unauthorized
   Response Headers: {...}
```

#### JSON Format (--format json)
```json
{
  "error": {
    "category": "auth",
    "severity": "error",
    "code": "INVALID_TOKEN",
    "message": "Authentication failed for provider 'ado_pdidev'",
    "timestamp": "2024-01-01T10:30:00Z",
    "request_id": "abc123-def456"
  },
  "context": {
    "provider": "ado_pdidev",
    "provider_type": "azuredevops",
    "organization": "pdidev",
    "operation": "list_repositories"
  },
  "details": {
    "api_endpoint": "https://dev.azure.com/pdidev/_apis/projects",
    "http_status": 401,
    "response_headers": {
      "content-type": "application/json",
      "x-tfs-fedauthrealm": "https://app.vssps.visualstudio.com/",
      "x-vss-e2eid": "abc123-def456"
    },
    "error_body": {
      "$id": "1",
      "innerException": null,
      "message": "TF400813: The user is not authorized to access this resource.",
      "typeName": "Microsoft.TeamFoundation.Framework.Server.UnauthorizedRequestException"
    }
  },
  "suggestions": [
    {
      "priority": "high",
      "action": "Check your PAT token is valid and not expired",
      "command": null
    },
    {
      "priority": "high",
      "action": "Verify token has required scopes",
      "command": "mgit config --show ado_pdidev"
    },
    {
      "priority": "medium",
      "action": "Re-authenticate with provider",
      "command": "mgit login --provider ado_pdidev --force"
    },
    {
      "priority": "low",
      "action": "Check Azure DevOps status page",
      "url": "https://status.dev.azure.com/"
    }
  ],
  "debug_info": {
    "stack_trace": "...",
    "environment": {
      "mgit_version": "0.7.0",
      "python_version": "3.12.9",
      "platform": "Linux-6.6.87"
    },
    "network_info": {
      "proxy": null,
      "timeout": 30,
      "retries": 3
    }
  }
}
```

#### Machine-Readable Format (--format logfmt)
```
timestamp=2024-01-01T10:30:00Z level=error category=auth code=INVALID_TOKEN message="Authentication failed for provider 'ado_pdidev'" provider=ado_pdidev operation=list_repositories http_status=401 request_id=abc123-def456
```

### 3. Error Recovery System

#### Automatic Recovery
- **Token refresh**: Automatic retry with refreshed tokens
- **Rate limit handling**: Exponential backoff with jitter
- **Network retry**: Smart retry for transient network issues
- **Provider fallback**: Try alternative providers when primary fails

#### Interactive Recovery
```bash
# Interactive error recovery
mgit list "pdidev/*/*" --interactive

# Would show:
❌ Authentication failed for provider 'ado_pdidev'

Choose recovery option:
1. Refresh authentication token
2. Check token permissions
3. Try different provider
4. Skip this provider
5. Abort operation

Selection: 1
```

### 4. Context-Aware Error Messages

#### Provider-Specific Errors
- **Azure DevOps**: PAT scope requirements, organization access
- **GitHub**: Token permissions, repository visibility
- **BitBucket**: App password format, workspace permissions

#### Operation-Specific Errors
- **List operations**: Pattern validation, provider connectivity
- **Clone operations**: Repository access, disk space
- **Sync operations**: Merge conflicts, permission issues

### 5. Error Aggregation and Reporting

#### Batch Operation Errors
```bash
mgit list "*/*/*" --batch-report

# Shows summary + detailed breakdown
📊 Error Summary:
   Total operations: 150
   Successful: 142 (94%)
   Failed: 8 (6%)

🔍 Error Breakdown:
   Authentication (3): ado_pdidev, bitbucket_p97
   Network timeout (2): github_main
   Rate limited (3): bitbucket_pdi

📋 Detailed Report:
   See: /tmp/mgit_error_report_20240101_103000.json
```

#### Error History
```bash
# View recent errors
mgit errors --last 10

# Filter by provider
mgit errors --provider ado_pdidev --since "1 day ago"

# Export for analysis
mgit errors --export errors.json --format json
```

### 6. Configuration Options

#### Error Display Preferences
```yaml
# ~/.config/mgit/config.yaml
errors:
  format: human          # human, json, logfmt
  verbosity: normal      # quiet, normal, verbose, debug
  show_suggestions: true
  show_debug: false
  max_suggestions: 5
  interactive: true      # Enable interactive recovery
  log_errors: true       # Log errors to file
  log_path: ~/.cache/mgit/errors.log
```

#### Provider-Specific Error Handling
```yaml
providers:
  ado_pdidev:
    errors:
      retry_count: 3
      retry_delay: 5
      timeout: 60
      fallback_provider: ado_p97
```

## Implementation Strategy

### Phase 1: Core Error Infrastructure
- [ ] Create error classification system
- [ ] Implement structured error objects
- [ ] Add error logging framework
- [ ] Basic error formatting (human-readable)

### Phase 2: Enhanced Error Messages
- [ ] Provider-specific error messages
- [ ] Contextual suggestions
- [ ] Debug information inclusion
- [ ] Multiple output formats

### Phase 3: Error Recovery
- [ ] Automatic retry mechanisms
- [ ] Interactive recovery options
- [ ] Error aggregation for batch operations

### Phase 4: Advanced Features
- [ ] Error history and analytics
- [ ] Machine learning for error prediction
- [ ] Error pattern recognition

## Error Code Reference

### Authentication Errors (AUTH_*)
- `AUTH_INVALID_TOKEN`: Token is invalid or expired
- `AUTH_MISSING_SCOPES`: Token lacks required permissions
- `AUTH_ORG_ACCESS`: No access to specified organization
- `AUTH_RATE_LIMITED`: Too many authentication attempts

### Network Errors (NET_*)
- `NET_TIMEOUT`: Request timed out
- `NET_CONNECTION`: Cannot connect to provider
- `NET_DNS`: DNS resolution failed
- `NET_SSL`: SSL/TLS certificate issues

### Validation Errors (VAL_*)
- `VAL_INVALID_PATTERN`: Query pattern syntax error
- `VAL_INVALID_CHARS`: Forbidden characters in pattern
- `VAL_PATTERN_TOO_LONG`: Pattern exceeds length limits
- `VAL_UNSUPPORTED_WILDCARD`: Advanced regex not supported

### Provider-Specific Errors (PROVIDER_*)
- `PROVIDER_ADO_PAT_EXPIRED`: Azure DevOps PAT expired
- `PROVIDER_GITHUB_TOKEN_SCOPES`: GitHub token missing scopes
- `PROVIDER_BITBUCKET_APP_PASSWORD`: BitBucket app password format issue

## Success Metrics

- **User satisfaction**: Reduced time to resolve issues
- **Error resolution rate**: > 90% of errors provide actionable solutions
- **Debug efficiency**: 50% reduction in support ticket complexity
- **System reliability**: Better error handling prevents crashes

## Future Enhancements

- **AI-powered suggestions**: ML-based error resolution recommendations
- **Error prediction**: Prevent common errors before they occur
- **Collaborative debugging**: Share error context with team members
- **Integration monitoring**: Track error patterns across CI/CD pipelines
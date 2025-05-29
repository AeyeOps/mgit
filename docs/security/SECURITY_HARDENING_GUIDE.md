# mgit Security Hardening Guide

## Overview

This guide provides comprehensive security hardening instructions for mgit to ensure production-ready security controls are in place.

## Security Architecture

### Defense in Depth

mgit implements multiple layers of security:

1. **Input Validation Layer** - Validates and sanitizes all user inputs
2. **Credential Protection Layer** - Masks and protects sensitive credentials
3. **Access Control Layer** - Validates permissions and access patterns
4. **Monitoring Layer** - Tracks security events and anomalies
5. **Error Handling Layer** - Prevents information disclosure

### Security Components

- `mgit.security.credentials` - Credential masking and validation
- `mgit.security.validation` - Input validation and sanitization
- `mgit.security.logging` - Security-enhanced logging
- `mgit.security.config` - Security configuration management
- `mgit.security.monitor` - Security monitoring and event tracking

## Credential Security

### Automatic Credential Masking

All credentials are automatically masked in:
- Log messages
- Error messages
- Console output
- Configuration displays
- API responses

Example:
```python
from mgit.security import mask_sensitive_data

# Original: "https://ghp_abc123def456@github.com/user/repo.git"
# Masked: "https://***********456@github.com/user/repo.git"
safe_url = mask_sensitive_data(clone_url)
```

### Supported Credential Types

- GitHub Personal Access Tokens (PAT)
- GitHub OAuth tokens
- Azure DevOps Personal Access Tokens
- BitBucket App Passwords
- Basic authentication credentials
- Bearer tokens

### Credential Validation

```python
from mgit.security.credentials import validate_github_pat

if not validate_github_pat(token):
    raise ValueError("Invalid GitHub PAT format")
```

## Input Validation

### Path Security

All file paths are validated to prevent:
- Path traversal attacks (`../` sequences)
- Access to sensitive directories
- Malformed path inputs

```python
from mgit.security.validation import is_safe_path, sanitize_path

# Validate path safety
if not is_safe_path(user_path, base_path="/allowed/directory"):
    raise SecurityError("Path not allowed")

# Sanitize path input
safe_path = sanitize_path(user_input)
```

### URL Security

URLs are validated for:
- Allowed schemes (http, https, git, ssh)
- Hostname validation
- Credential masking
- Malicious pattern detection

```python
from mgit.security.validation import validate_git_url

if not validate_git_url(repository_url):
    raise ValueError("Invalid repository URL")
```

### Repository Name Validation

Repository and organization names are validated against:
- Character restrictions
- Length limits
- Reserved names
- Injection patterns

```python
from mgit.security.validation import validate_input

if not validate_input(repo_name, 'repo_name'):
    raise ValueError("Invalid repository name")
```

## Security Configuration

### Environment Variables

Set security configuration via environment variables:

```bash
# Enable strict validation
export MGIT_SECURITY_STRICT_PATH_VALIDATION=true
export MGIT_SECURITY_STRICT_URL_VALIDATION=true

# API security
export MGIT_SECURITY_VERIFY_SSL_CERTIFICATES=true
export MGIT_SECURITY_TIMEOUT_SECONDS=30

# Logging security
export MGIT_SECURITY_MASK_CREDENTIALS_IN_LOGS=true
export MGIT_SECURITY_LOG_SECURITY_EVENTS=true
```

### Configuration File

Create `~/.config/mgit/security.json`:

```json
{
  "mask_credentials_in_logs": true,
  "mask_credentials_in_errors": true,
  "strict_path_validation": true,
  "strict_url_validation": true,
  "verify_ssl_certificates": true,
  "timeout_seconds": 30,
  "log_security_events": true,
  "debug_mode": false,
  "allow_insecure_connections": false
}
```

### Production Security Check

```python
from mgit.security.config import is_production_secure

if not is_production_secure():
    logger.error("Configuration not suitable for production")
    sys.exit(1)
```

## Security Monitoring

### Event Tracking

All security-relevant events are automatically tracked:

```python
from mgit.security.monitor import log_security_event

log_security_event(
    event_type='suspicious_activity',
    severity='WARNING',
    source='api',
    details={'activity': 'unusual_access_pattern'}
)
```

### Security Metrics

Monitor security health:

```python
from mgit.security.monitor import get_security_monitor

monitor = get_security_monitor()
summary = monitor.get_security_summary(hours=24)

print(f"Security Score: {summary['security_score']}/100")
print(f"Failed Auth Attempts: {summary['metrics']['failed_auth_attempts']}")
```

### Rate Limiting

Automatic rate limiting prevents abuse:
- API calls: 100 per minute
- Authentication attempts: 10 per 5 minutes
- Validation failures: 20 per minute

## Secure Logging

### Enhanced Security Logger

```python
from mgit.security.logging import SecurityLogger

logger = SecurityLogger('my_component')
logger.info("User authenticated: %s", sensitive_data)  # Automatically masked
```

### API Call Logging

```python
logger.log_api_call(
    method='GET',
    url='https://api.github.com/user',  # Will be masked
    status_code=200,
    response_time=0.5
)
```

### Git Operation Logging

```python
logger.log_git_operation(
    operation='clone',
    repo_url='https://token@github.com/user/repo.git',  # Will be masked
    result='success'
)
```

## Error Handling Security

### Sanitized Error Messages

Errors are automatically sanitized to prevent information disclosure:

```python
try:
    authenticate_with_token(token)
except Exception as e:
    # Original: "Authentication failed: Invalid token ghp_abc123def456"
    # Sanitized: "Authentication failed: Invalid token ***********456"
    raise sanitized_error(e)
```

### Security-First Exception Handling

```python
from mgit.security.patches import secure_provider_method

@secure_provider_method
async def authenticate(self):
    # Automatic security controls applied
    # - Input validation
    # - Credential masking
    # - Security event logging
    # - Error sanitization
    pass
```

## Provider Security Integration

### Secure Provider Implementation

```python
from mgit.security.patches import SecureProviderMixin

class MyProvider(GitProvider, SecureProviderMixin):
    async def authenticate(self):
        # Security controls automatically applied
        result = await super().authenticate()
        return result
```

### Provider Security Patches

Apply security retroactively to existing providers:

```python
from mgit.security.patches import apply_security_patches

# Apply security to all providers
apply_security_patches()
```

## Security Best Practices

### Development

1. **Never log credentials** - Use security logger
2. **Validate all inputs** - Use validation functions
3. **Handle errors securely** - Use sanitized error handling
4. **Monitor security events** - Use security monitor

### Deployment

1. **Enable SSL verification** - Set `verify_ssl_certificates: true`
2. **Disable debug mode** - Set `debug_mode: false`
3. **Enable credential masking** - Set `mask_credentials_in_logs: true`
4. **Configure rate limiting** - Use default rate limits
5. **Monitor security metrics** - Check security score regularly

### Operations

1. **Review security logs** - Check for suspicious activities
2. **Rotate credentials** - Regular credential rotation
3. **Monitor rate limits** - Watch for abuse patterns
4. **Update security config** - Keep security settings current

## Security Checklist

### Pre-Production Checklist

- [ ] SSL certificate verification enabled
- [ ] Credential masking enabled in logs and errors
- [ ] Debug mode disabled
- [ ] Strict input validation enabled
- [ ] Security monitoring configured
- [ ] Rate limiting enabled
- [ ] Error sanitization enabled
- [ ] Security configuration review completed
- [ ] Security score > 80

### Production Monitoring

- [ ] Regular security log reviews
- [ ] Security metrics monitoring
- [ ] Failed authentication tracking
- [ ] Anomaly detection alerts
- [ ] Credential exposure monitoring

## Compliance and Auditing

### Security Audit Trail

All security events are logged with:
- Timestamp
- Event type and severity
- Source component
- Detailed context
- User information (when available)

### Export Security Events

```python
from mgit.security.monitor import get_security_monitor

monitor = get_security_monitor()
monitor.export_events(
    file_path=Path('security_audit.json'),
    hours=24
)
```

### Compliance Features

- **GDPR**: Credential masking prevents personal data exposure
- **SOX**: Audit trail for all security events
- **HIPAA**: Security monitoring and access controls
- **PCI**: Secure credential handling

## Incident Response

### Security Event Response

1. **Detection** - Security monitor alerts
2. **Assessment** - Review security events
3. **Containment** - Rate limiting and blocking
4. **Recovery** - Credential rotation and cleanup
5. **Lessons Learned** - Update security configuration

### Common Security Scenarios

#### Credential Exposure
```bash
# 1. Identify exposure
mgit security events --type credential_exposure

# 2. Rotate affected credentials
# 3. Review access logs
# 4. Update security configuration
```

#### Suspicious Authentication
```bash
# 1. Check failed authentication attempts
mgit security summary --hours 24

# 2. Review source IPs and patterns
# 3. Implement additional rate limiting
# 4. Consider credential rotation
```

## Advanced Security Features

### Custom Security Rules

```python
from mgit.security.monitor import SecurityMonitor

monitor = SecurityMonitor()
monitor.add_custom_rule(
    name='high_api_usage',
    condition=lambda events: len([e for e in events if e.event_type == 'api_call']) > 1000,
    action='alert_admin'
)
```

### Integration with External Security Tools

```python
# SIEM integration
from mgit.security.monitor import get_security_monitor

monitor = get_security_monitor()
events = monitor.get_recent_events(severity='ERROR')

for event in events:
    send_to_siem(event)
```

### Security Metrics Dashboard

```python
def security_dashboard():
    monitor = get_security_monitor()
    summary = monitor.get_security_summary()
    
    return {
        'security_score': summary['security_score'],
        'threat_level': calculate_threat_level(summary),
        'recommendations': summary['recommendations']
    }
```

## Troubleshooting

### Common Security Issues

1. **Credentials in logs** - Enable credential masking
2. **Path traversal errors** - Enable strict path validation
3. **SSL verification failures** - Check certificate configuration
4. **Rate limit exceeded** - Review usage patterns

### Debug Security Issues

```python
# Enable security debug logging
export MGIT_SECURITY_LOG_LEVEL=DEBUG

# Check security configuration
python -m mgit security config --show

# Review recent security events
python -m mgit security events --count 100
```

## Security Updates

### Keeping Security Current

1. **Regular updates** - Update mgit security modules
2. **Configuration review** - Quarterly security config review
3. **Security testing** - Regular penetration testing
4. **Threat modeling** - Annual threat model updates

### Security Release Notes

Check `SECURITY_CHANGELOG.md` for security-specific updates and patches.
# Security Policy

## Reporting Security Vulnerabilities

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**DO NOT** open a public issue for security vulnerabilities.

Instead, please email: security@aeyeops.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide updates as we investigate.

## Security Features

mgit implements several security measures:

### Credential Protection

- **Encryption**: AES-256 encryption for stored credentials
- **Secure Storage**: Platform-specific secure storage locations
- **Memory Protection**: Credentials cleared from memory after use
- **No Logging**: Tokens/passwords never appear in logs

### File Permissions

- Configuration files: `0600` (owner read/write only)
- Log files: `0640` (owner write, group read)
- Automatic permission correction on startup

### Token Handling

- Automatic masking in console output
- Secure environment variable handling
- Token validation before storage
- Automatic expiry warnings

## Best Practices

### For Users

1. **Use Personal Access Tokens**
   - Never use your main account password
   - Create tokens with minimal required permissions
   - Set expiration dates

2. **Secure Your Environment**
   ```bash
   # Check file permissions
   ls -la ~/.config/mgit/
   
   # Ensure proper permissions
   chmod 700 ~/.config/mgit
   chmod 600 ~/.config/mgit/config.yaml
   ```

3. **Rotate Credentials Regularly**
   - Update tokens before expiry
   - Remove unused provider configurations
   - Audit access logs

4. **Environment Variables**
   - Use for CI/CD environments
   - Never commit `.env` files
   - Clear after use

### For CI/CD

```yaml
# GitHub Actions example
- name: Run mgit
  env:
    GITHUB_TOKEN: ${{ secrets.MGIT_TOKEN }}
  run: |
    mgit list "myorg/*"
    unset GITHUB_TOKEN
```

## Security Checklist

### Installation
- [ ] Download from official sources only
- [ ] Verify checksums/signatures
- [ ] Check file permissions after install

### Configuration
- [ ] Use strong, unique tokens
- [ ] Set appropriate file permissions
- [ ] Enable audit logging
- [ ] Use environment variables in CI/CD

### Operation
- [ ] Regularly update mgit
- [ ] Monitor for unusual activity
- [ ] Rotate credentials periodically
- [ ] Review provider access

## Known Security Considerations

### Network Security
- All API calls use HTTPS
- Certificate validation enabled by default
- Proxy support with authentication

### Local Security
- No world-readable files created
- Secure temporary file handling
- No credential echoing to terminal

### Audit Trail
- Command logging available
- Token usage tracking
- Failed authentication alerts

## Versions

| Version | Supported | Security Updates |
|---------|-----------|------------------|
| 0.2.x   | ✓        | Active           |
| 0.1.x   | ✗        | End of Life      |

## Security Updates

Security updates are released as:
- Patch versions for fixes (0.2.x)
- Minor versions for enhancements (0.x.0)

Subscribe to security announcements:
- Watch the repository
- Join our security mailing list

## Compliance

mgit is designed with security standards in mind:
- OWASP guidelines for secure coding
- CIS benchmarks for configuration
- Industry best practices for credential management

## Contact

Security Team: security@aeyeops.com
Response Time: 48 hours
PGP Key: [Available on request]
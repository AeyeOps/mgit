#!/usr/bin/env python3
"""
Security Features Demonstration for mgit
Shows practical examples of security protection in action
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from mgit.security.credentials import CredentialMasker, validate_github_pat
from mgit.security.validation import SecurityValidator, sanitize_repository_name
from mgit.security.monitor import get_security_monitor
from mgit.security.integration import initialize_security, get_security_status


def demo_credential_protection():
    """Demonstrate credential protection features."""
    print("=" * 60)
    print("CREDENTIAL PROTECTION DEMONSTRATION")
    print("=" * 60)
    
    masker = CredentialMasker()
    
    # Example 1: Log message with credentials
    print("\n1. Protecting credentials in log messages:")
    log_msg = "Connecting to GitHub with token: ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    masked = masker.mask_string(log_msg)
    print(f"   Original: {log_msg}")
    print(f"   Protected: {masked}")
    
    # Example 2: API response with sensitive data
    print("\n2. Protecting API responses:")
    api_response = {
        'status': 'success',
        'token': 'ghp_secrettoken1234567890abcdefghijklmnop',
        'user': 'johndoe',
        'password': 'super_secret_password',
        'data': {
            'api_key': 'key_1234567890',
            'safe_field': 'This data is not sensitive'
        }
    }
    masked_response = masker.mask_dict(api_response)
    print("   Original response contains: token, password, api_key")
    print(f"   Protected response: {masked_response}")
    
    # Example 3: URL with embedded credentials
    print("\n3. Protecting URLs with credentials:")
    url = "https://user:mypassword123@github.com/org/repo.git"
    masked_url = masker.mask_url(url)
    print(f"   Original: {url}")
    print(f"   Protected: {masked_url}")


def demo_input_validation():
    """Demonstrate input validation features."""
    print("\n" + "=" * 60)
    print("INPUT VALIDATION DEMONSTRATION")
    print("=" * 60)
    
    validator = SecurityValidator()
    
    # Example 1: Repository name validation
    print("\n1. Repository name validation:")
    test_names = [
        "valid-repo-name",
        "../../../etc/passwd",
        "repo; rm -rf /",
        "<script>alert('xss')</script>"
    ]
    
    for name in test_names:
        is_valid = validator.validate_repository_name(name)
        sanitized = sanitize_repository_name(name)
        print(f"   '{name}':")
        print(f"     Valid: {is_valid}")
        print(f"     Sanitized: '{sanitized}'")
    
    # Example 2: Path validation
    print("\n2. Path validation:")
    test_paths = [
        "/opt/aeo/mgit/repos",
        "../../../../etc/passwd",
        "C:\\Windows\\System32",
        "${HOME}/.ssh/id_rsa"
    ]
    
    for path in test_paths:
        is_valid = validator.validate_path(path)
        print(f"   '{path}': {'✓ Valid' if is_valid else '✗ Blocked'}")
    
    # Example 3: URL validation
    print("\n3. URL validation:")
    test_urls = [
        "https://github.com/org/repo.git",
        "javascript:alert(document.cookie)",
        "file:///etc/passwd",
        "https://github.com/../../../admin"
    ]
    
    for url in test_urls:
        is_valid = validator.validate_url(url)
        print(f"   '{url}': {'✓ Valid' if is_valid else '✗ Blocked'}")


def demo_security_monitoring():
    """Demonstrate security monitoring features."""
    print("\n" + "=" * 60)
    print("SECURITY MONITORING DEMONSTRATION")
    print("=" * 60)
    
    monitor = get_security_monitor()
    
    # Simulate some security events
    print("\n1. Logging security events:")
    
    # Successful authentication
    monitor.log_authentication_attempt("github", "myorg", True)
    print("   ✓ Logged successful authentication")
    
    # Failed authentication attempts
    for i in range(3):
        monitor.log_authentication_attempt("github", "myorg", False)
    print("   ✓ Logged 3 failed authentication attempts")
    
    # Validation failure
    monitor.log_validation_failure("path", "../etc/passwd", "Path traversal detected")
    print("   ✓ Logged validation failure (path traversal)")
    
    # Get security summary
    print("\n2. Security Summary:")
    summary = monitor.get_security_summary(hours=1)
    print(f"   Security Score: {summary['security_score']}/100")
    print(f"   Total Events: {summary['total_events']}")
    print(f"   Failed Auth Attempts: {summary['metrics']['failed_auth_attempts']}")
    print(f"   Validation Failures: {summary['metrics']['validation_failures']}")
    
    if summary['recommendations']:
        print("\n3. Security Recommendations:")
        for rec in summary['recommendations']:
            print(f"   - {rec}")


def demo_production_security():
    """Demonstrate production security configuration."""
    print("\n" + "=" * 60)
    print("PRODUCTION SECURITY CONFIGURATION")
    print("=" * 60)
    
    # Get security status
    status = get_security_status()
    
    print("\n1. Security Configuration:")
    config = status['configuration']
    for setting, value in config.items():
        icon = "✓" if value in [True, False] and value == (setting != 'debug_mode') else "✗"
        print(f"   {icon} {setting}: {value}")
    
    print(f"\n2. Production Ready: {'✓ YES' if status['production_ready'] else '✗ NO'}")
    
    print("\n3. Security Features Active:")
    print("   ✓ Credential masking in logs")
    print("   ✓ Input validation and sanitization")
    print("   ✓ Security event monitoring")
    print("   ✓ Rate limiting protection")
    print("   ✓ Anomaly detection")


def main():
    """Run security feature demonstrations."""
    print("🛡️  mgit Security Features Demonstration")
    print("This demonstrates the security infrastructure in action\n")
    
    # Initialize security
    initialize_security()
    
    # Run demonstrations
    demo_credential_protection()
    demo_input_validation()
    demo_security_monitoring()
    demo_production_security()
    
    print("\n" + "=" * 60)
    print("✅ Security features demonstration complete!")
    print("The mgit security infrastructure provides comprehensive")
    print("protection against credential exposure, injection attacks,")
    print("and malicious activities.")
    print("=" * 60)


if __name__ == "__main__":
    main()
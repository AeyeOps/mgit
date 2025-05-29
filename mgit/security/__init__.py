"""Security module for mgit.

This module provides comprehensive security controls including:
- Credential masking and sanitization
- Input validation and sanitization
- Path traversal protection
- Security logging and monitoring
- Secure configuration handling
"""

from .credentials import CredentialMasker, secure_credential_handler
from .validation import (
    SecurityValidator,
    sanitize_path,
    sanitize_url,
    sanitize_repository_name,
    validate_input,
    is_safe_path,
)
from .logging import SecurityLogger, mask_sensitive_data
from .config import SecurityConfig, get_security_settings
from .monitor import SecurityMonitor, log_security_event

__all__ = [
    'CredentialMasker',
    'secure_credential_handler',
    'SecurityValidator',
    'sanitize_path',
    'sanitize_url', 
    'sanitize_repository_name',
    'validate_input',
    'is_safe_path',
    'SecurityLogger',
    'mask_sensitive_data',
    'SecurityConfig',
    'get_security_settings',
    'SecurityMonitor',
    'log_security_event',
]
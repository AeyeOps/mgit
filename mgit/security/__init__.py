"""Security module for mgit.

This module provides comprehensive security controls including:
- Credential masking and sanitization
- Input validation and sanitization
- Path traversal protection
- Security logging and monitoring
- Secure configuration handling
"""

from .config import SecurityConfig, get_security_settings
from .credentials import CredentialMasker, secure_credential_handler
from .logging import SecurityLogger, mask_sensitive_data
from .monitor import SecurityMonitor, log_security_event
from .validation import (
    SecurityValidator,
    is_safe_path,
    sanitize_path,
    sanitize_repository_name,
    sanitize_url,
    validate_input,
)

__all__ = [
    "CredentialMasker",
    "secure_credential_handler",
    "SecurityValidator",
    "sanitize_path",
    "sanitize_url",
    "sanitize_repository_name",
    "validate_input",
    "is_safe_path",
    "SecurityLogger",
    "mask_sensitive_data",
    "SecurityConfig",
    "get_security_settings",
    "SecurityMonitor",
    "log_security_event",
]

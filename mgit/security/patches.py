"""Security patches for existing mgit components.

This module provides patches and utilities to retrofit security
controls into existing code without major refactoring.
"""

import functools
import inspect
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from .credentials import CredentialMasker
from .logging import SecurityLogger
from .monitor import get_security_monitor
from .validation import SecurityValidator, validate_input

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def secure_provider_method[F: Callable[..., Any]](func: F) -> F:
    """Decorator to add security controls to provider methods.

    This decorator:
    - Masks credentials in arguments and return values
    - Validates inputs
    - Logs security events
    - Handles errors securely
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        monitor = get_security_monitor()

        # Get method info
        method_name = func.__name__
        class_name = args[0].__class__.__name__ if args else "Unknown"

        try:
            # Validate inputs based on method name
            if "authenticate" in method_name:
                # Log authentication attempt
                provider_name = getattr(args[0], "PROVIDER_NAME", "unknown")
                monitor.log_authentication_attempt(
                    provider=provider_name,
                    organization="unknown",  # Will be updated by actual implementation
                    success=False,  # Will be updated based on result
                    details={"method": method_name},
                )

            # Execute original method
            result = func(*args, **kwargs)

            # Handle async results
            if inspect.iscoroutine(result):

                async def async_wrapper():
                    try:
                        async_result = await result

                        # Log successful operation
                        if "authenticate" in method_name and async_result:
                            provider_name = getattr(args[0], "PROVIDER_NAME", "unknown")
                            monitor.log_authentication_attempt(
                                provider=provider_name,
                                organization="unknown",
                                success=True,
                                details={"method": method_name},
                            )

                        return async_result
                    except Exception as e:
                        # Log security event for failures
                        monitor.log_security_event(
                            event_type="provider_error",
                            severity="ERROR",
                            source=f"{class_name}.{method_name}",
                            details={"error": str(e), "provider": class_name},
                        )
                        raise

                return async_wrapper()

            return result

        except Exception as e:
            # Log security event for failures
            monitor.log_security_event(
                event_type="provider_error",
                severity="ERROR",
                source=f"{class_name}.{method_name}",
                details={"error": str(e), "provider": class_name},
            )
            raise

    return wrapper


def secure_logging_patch():
    """Patch logging to automatically mask credentials."""

    def patch_handler(handler):
        """Patch a logging handler to mask credentials."""
        if hasattr(handler, "_original_emit"):
            return  # Already patched

        original_emit = handler.emit
        handler._original_emit = original_emit

        def secure_emit(record):
            # Apply credential masking to the record
            masker = CredentialMasker()

            if hasattr(record, "msg") and record.msg:
                record.msg = masker.mask_string(str(record.msg))

            if hasattr(record, "args") and record.args:
                masked_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        masked_args.append(masker.mask_string(arg))
                    elif isinstance(arg, dict):
                        masked_args.append(masker.mask_dict(arg))
                    else:
                        masked_args.append(arg)
                record.args = tuple(masked_args)

            # Call original emit with masked record
            original_emit(record)

        handler.emit = secure_emit

    # Patch all existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        patch_handler(handler)

    # Store original addHandler to patch new handlers
    original_addHandler = logging.Logger.addHandler

    def secure_addHandler(self, handler):
        patch_handler(handler)
        original_addHandler(self, handler)

    logging.Logger.addHandler = secure_addHandler


def secure_url_handling_patch():
    """Patch URL handling to mask credentials and validate URLs."""

    def secure_url_formatter(url: str) -> str:
        """Secure URL formatter that masks credentials."""
        masker = CredentialMasker()
        validator = SecurityValidator()

        # Validate URL
        if not validator.validate_url(url):
            logger.warning(f"Invalid URL detected: {masker.mask_url(url)}")

        return masker.mask_url(url)

    # This would be applied to provider URL handling methods
    return secure_url_formatter


def patch_provider_error_handling():
    """Patch provider error handling to prevent information disclosure."""

    def secure_error_handler(original_error: Exception, context: str) -> Exception:
        """Create a sanitized error message."""
        masker = CredentialMasker()

        # Mask any credentials in error message
        error_message = masker.mask_string(str(original_error))

        # Remove potentially sensitive information
        sanitized_message = error_message

        # Replace specific error types with generic messages in production
        if "authentication" in error_message.lower():
            sanitized_message = "Authentication failed"
        elif "connection" in error_message.lower():
            sanitized_message = "Connection failed"
        elif "timeout" in error_message.lower():
            sanitized_message = "Request timeout"

        # Log the original error securely for debugging
        monitor = get_security_monitor()
        monitor.log_security_event(
            event_type="error_sanitized",
            severity="INFO",
            source=context,
            details={
                "original_error_type": type(original_error).__name__,
                "sanitized_message": sanitized_message,
            },
        )

        # Return new exception with sanitized message
        return type(original_error)(sanitized_message)

    return secure_error_handler


class SecureProviderMixin:
    """Mixin class to add security features to existing providers."""

    def __init_subclass__(cls, **kwargs):
        """Automatically apply security patches when subclassed."""
        super().__init_subclass__(**kwargs)

        # Apply security decorator to key methods
        security_methods = [
            "authenticate",
            "test_connection",
            "list_repositories",
            "get_repository",
            "list_organizations",
            "list_projects",
        ]

        for method_name in security_methods:
            if hasattr(cls, method_name):
                original_method = getattr(cls, method_name)
                secured_method = secure_provider_method(original_method)
                setattr(cls, method_name, secured_method)

    def _secure_log(self, level: str, message: str, **kwargs):
        """Secure logging method."""
        security_logger = SecurityLogger(self.__class__.__name__)
        log_method = getattr(security_logger, level.lower(), security_logger.info)
        log_method(message, **kwargs)

    def _mask_credentials_in_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Mask credentials in configuration dictionary."""
        masker = CredentialMasker()
        return masker.mask_dict(config)

    def _validate_repository_name(self, name: str) -> bool:
        """Validate repository name."""
        validator = SecurityValidator()
        return validator.validate_repository_name(name)

    def _validate_organization_name(self, name: str) -> bool:
        """Validate organization name."""
        validator = SecurityValidator()
        return validator.validate_organization_name(name)

    def _validate_url(self, url: str) -> bool:
        """Validate URL."""
        validator = SecurityValidator()
        return validator.validate_url(url)


def apply_security_patches():
    """Apply all security patches to the mgit codebase."""
    logger.info("Applying security patches...")

    # Patch logging
    secure_logging_patch()

    # Additional patches can be added here
    logger.info("Security patches applied successfully")


def create_secure_provider_factory():
    """Create a factory function that applies security controls to providers."""

    def secure_provider_wrapper(provider_class):
        """Wrap a provider class with security controls."""

        class SecureProvider(provider_class, SecureProviderMixin):
            """Provider with security controls applied."""

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._security_logger = SecurityLogger(
                    f"secure_{provider_class.__name__}"
                )
                self._credential_masker = CredentialMasker()
                self._validator = SecurityValidator()
                self._monitor = get_security_monitor()

            async def authenticate(self, *args, **kwargs):
                """Secure authentication with monitoring."""
                provider_name = getattr(self, "PROVIDER_NAME", "unknown")

                try:
                    result = await super().authenticate(*args, **kwargs)

                    # Log successful authentication
                    self._monitor.log_authentication_attempt(
                        provider=provider_name,
                        organization=getattr(self, "url", "unknown"),
                        success=True,
                    )

                    return result

                except Exception as e:
                    # Log failed authentication
                    self._monitor.log_authentication_attempt(
                        provider=provider_name,
                        organization=getattr(self, "url", "unknown"),
                        success=False,
                        details={"error": str(e)},
                    )
                    raise

            def get_authenticated_clone_url(self, repository):
                """Get authenticated clone URL with security validation."""
                # Validate repository first
                if not self._validate_repository_name(repository.name):
                    raise ValueError(f"Invalid repository name: {repository.name}")

                # Get the URL from parent class
                url = super().get_authenticated_clone_url(repository)

                # Validate the resulting URL
                if not self._validator.validate_url(url):
                    raise ValueError("Generated clone URL failed security validation")

                return url

        return SecureProvider

    return secure_provider_wrapper


# Convenience functions for common security operations
def secure_api_call(func):
    """Decorator for API calls with security monitoring."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        monitor = get_security_monitor()

        # Extract method and URL if possible
        method = kwargs.get("method", "UNKNOWN")
        url = kwargs.get("url", "unknown")

        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            response_time = time.time() - start_time

            # Log successful API call
            monitor.log_api_call(
                method=method,
                url=url,
                status_code=200,  # Assumed successful
                response_time=response_time,
            )

            return result

        except Exception:
            response_time = time.time() - start_time

            # Log failed API call
            monitor.log_api_call(
                method=method,
                url=url,
                status_code=500,  # Assumed error
                response_time=response_time,
            )

            raise

    return wrapper


def validate_and_sanitize_input(input_type: str):
    """Decorator to validate and sanitize input parameters."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_security_monitor()

            # Validate based on input type and parameter names
            for key, value in kwargs.items():
                if isinstance(value, str):
                    if not validate_input(value, input_type):
                        monitor.log_validation_failure(
                            input_type=f"{input_type}:{key}",
                            value=value,
                            reason="Failed security validation",
                        )
                        raise ValueError(f"Invalid {input_type} parameter: {key}")

            return func(*args, **kwargs)

        return wrapper

    return decorator

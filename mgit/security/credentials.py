"""Credential security handling for mgit.

This module provides secure credential management, masking, and validation
to prevent credential exposure in logs, error messages, and API responses.
"""

import logging
import re
from functools import wraps
from typing import Any, Dict
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)


class CredentialMasker:
    """Handles masking of sensitive credentials in various contexts."""

    # Common credential patterns
    CREDENTIAL_PATTERNS = {
        "github_pat": re.compile(r"\bghp_[a-zA-Z0-9]{36}\b"),
        "github_oauth": re.compile(r"\bgho_[a-zA-Z0-9]{36}\b"),
        "azure_pat": re.compile(r"\b[a-zA-Z0-9]{52}\b"),  # Azure DevOps PAT format
        "bitbucket_app_password": re.compile(r"\bATBB[a-zA-Z0-9]{28}\b"),
        "basic_auth_url": re.compile(r"://[^:]+:[^@]+@"),
        "bearer_token": re.compile(r"\bBearer\s+[a-zA-Z0-9._-]+", re.IGNORECASE),
        "authorization_header": re.compile(r"\bAuthorization:\s*[^\s]+", re.IGNORECASE),
        "token_header": re.compile(r"\btoken\s+[a-zA-Z0-9._-]+", re.IGNORECASE),
        "generic_token": re.compile(r"\b[a-fA-F0-9]{40,}\b"),  # 40+ char hex strings
        "base64_credentials": re.compile(r"\bBasic\s+[A-Za-z0-9+/]+=*", re.IGNORECASE),
    }

    # Sensitive field names that should be masked
    SENSITIVE_FIELDS = {
        "pat",
        "token",
        "password",
        "secret",
        "key",
        "auth",
        "credential",
        "app_password",
        "oauth_token",
        "access_token",
        "refresh_token",
        "authorization",
        "x-api-key",
        "x-auth-token",
    }

    # URL parameters that should be masked
    SENSITIVE_URL_PARAMS = {"token", "access_token", "auth", "key", "secret", "pat"}

    def __init__(self, mask_char: str = "*", show_length: int = 4):
        """Initialize credential masker.

        Args:
            mask_char: Character to use for masking
            show_length: Number of characters to show at the end
        """
        self.mask_char = mask_char
        self.show_length = show_length

    def mask_string(self, text: str) -> str:
        """Mask credentials in a string.

        Args:
            text: String that may contain credentials

        Returns:
            String with credentials masked
        """
        if not text or not isinstance(text, str):
            return text

        masked_text = text

        # Apply each credential pattern
        for pattern_name, pattern in self.CREDENTIAL_PATTERNS.items():
            masked_text = pattern.sub(self._mask_match, masked_text)

        return masked_text

    def mask_url(self, url: str) -> str:
        """Mask credentials in URLs.

        Args:
            url: URL that may contain credentials

        Returns:
            URL with credentials masked
        """
        if not url or not isinstance(url, str):
            return url

        try:
            parsed = urlparse(url)

            # Mask credentials in userinfo (username:password@)
            if parsed.username or parsed.password:
                masked_username = (
                    self._mask_credential(parsed.username) if parsed.username else ""
                )
                masked_password = (
                    self._mask_credential(parsed.password) if parsed.password else ""
                )

                # Reconstruct netloc without credentials if both are masked
                if masked_username and masked_password:
                    netloc = f"{masked_username}:{masked_password}@{parsed.hostname}"
                    if parsed.port:
                        netloc += f":{parsed.port}"
                else:
                    netloc = parsed.hostname
                    if parsed.port:
                        netloc += f":{parsed.port}"

                # Reconstruct URL
                parsed = parsed._replace(netloc=netloc)

            # Mask sensitive query parameters
            if parsed.query:
                query_params = parse_qs(parsed.query, keep_blank_values=True)
                masked_params = {}

                for key, values in query_params.items():
                    if key.lower() in self.SENSITIVE_URL_PARAMS:
                        masked_params[key] = [self._mask_credential(v) for v in values]
                    else:
                        masked_params[key] = values

                # Reconstruct query string
                new_query = urlencode(masked_params, doseq=True)
                parsed = parsed._replace(query=new_query)

            return urlunparse(parsed)

        except Exception as e:
            logger.debug(f"Error masking URL: {e}")
            # Fallback to string masking
            return self.mask_string(url)

    def mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask credentials in dictionary values.

        Args:
            data: Dictionary that may contain credentials

        Returns:
            Dictionary with credentials masked
        """
        if not isinstance(data, dict):
            return data

        masked_data = {}

        for key, value in data.items():
            # Check if the key indicates sensitive data
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                masked_data[key] = self._mask_credential(value)
            elif isinstance(value, str):
                masked_data[key] = self.mask_string(value)
            elif isinstance(value, dict):
                masked_data[key] = self.mask_dict(value)
            elif isinstance(value, list):
                masked_data[key] = [
                    (
                        self.mask_dict(item)
                        if isinstance(item, dict)
                        else self.mask_string(item)
                        if isinstance(item, str)
                        else item
                    )
                    for item in value
                ]
            else:
                masked_data[key] = value

        return masked_data

    def mask_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Mask credentials in HTTP headers.

        Args:
            headers: HTTP headers dictionary

        Returns:
            Headers with credentials masked
        """
        if not isinstance(headers, dict):
            return headers

        masked_headers = {}

        for key, value in headers.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                masked_headers[key] = self._mask_credential(value)
            else:
                masked_headers[key] = (
                    self.mask_string(value) if isinstance(value, str) else value
                )

        return masked_headers

    def _mask_match(self, match: re.Match) -> str:
        """Mask a regex match."""
        return self._mask_credential(match.group(0))

    def _mask_credential(self, credential: Any) -> str:
        """Mask a single credential value.

        Args:
            credential: Credential value to mask

        Returns:
            Masked credential string
        """
        if not credential or not isinstance(credential, str):
            return str(credential) if credential is not None else ""

        # For very short strings, mask completely
        if len(credential) <= self.show_length:
            return self.mask_char * len(credential)

        # Show last few characters
        visible_part = credential[-self.show_length :]
        masked_part = self.mask_char * (len(credential) - self.show_length)

        return f"{masked_part}{visible_part}"


def secure_credential_handler(func):
    """Decorator to automatically mask credentials in function arguments and return values.

    Usage:
        @secure_credential_handler
        def api_call(url: str, token: str) -> dict:
            # Function implementation
            pass
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        masker = CredentialMasker()

        try:
            # Execute function
            result = func(*args, **kwargs)

            # Mask credentials in return value if it's a dict or string
            if isinstance(result, dict):
                return masker.mask_dict(result)
            elif isinstance(result, str):
                return masker.mask_string(result)
            else:
                return result

        except Exception as e:
            # Mask credentials in exception message
            error_message = str(e)
            masked_message = masker.mask_string(error_message)

            # Re-raise with masked message if it changed
            if masked_message != error_message:
                raise type(e)(masked_message) from e
            else:
                raise

    return wrapper


def mask_sensitive_data(data: Any) -> Any:
    """Convenience function to mask sensitive data.

    Args:
        data: Data that may contain credentials

    Returns:
        Data with credentials masked
    """
    masker = CredentialMasker()

    if isinstance(data, str):
        return masker.mask_string(data)
    elif isinstance(data, dict):
        return masker.mask_dict(data)
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    else:
        return data


# Validation functions for credentials
def validate_github_pat(token: str) -> bool:
    """Validate GitHub Personal Access Token format.

    Args:
        token: Token to validate

    Returns:
        True if token format is valid
    """
    if not token or not isinstance(token, str):
        return False

    # GitHub PAT formats: ghp_, gho_, ghu_, ghs_, ghr_
    github_patterns = [
        r"^ghp_[a-zA-Z0-9]{36}$",  # Personal access token
        r"^gho_[a-zA-Z0-9]{36}$",  # OAuth token
        r"^ghu_[a-zA-Z0-9]{36}$",  # User-to-server token
        r"^ghs_[a-zA-Z0-9]{36}$",  # Server-to-server token
        r"^ghr_[a-zA-Z0-9]{76}$",  # Refresh token
    ]

    return any(re.match(pattern, token) for pattern in github_patterns)


def validate_azure_pat(token: str) -> bool:
    """Validate Azure DevOps Personal Access Token format.

    Args:
        token: Token to validate

    Returns:
        True if token format is valid
    """
    if not token or not isinstance(token, str):
        return False

    # Azure DevOps PAT is typically 52 characters, base64-like
    return bool(re.match(r"^[a-zA-Z0-9]{52}$", token))


def validate_bitbucket_app_password(password: str) -> bool:
    """Validate BitBucket App Password format.

    Args:
        password: App password to validate

    Returns:
        True if password format is valid
    """
    if not password or not isinstance(password, str):
        return False

    # BitBucket App Password formats:
    # - New format: ATBB + alphanumeric characters (variable length)
    # - Legacy format: Long alphanumeric strings
    # We'll be lenient and accept any reasonable app password
    if password.startswith("ATBB"):
        return bool(re.match(r"^ATBB[a-zA-Z0-9]+$", password))
    else:
        # Accept any string that looks like a token (alphanumeric, min 20 chars)
        return bool(re.match(r"^[a-zA-Z0-9]{20,}$", password))


def is_credential_exposed(text: str) -> bool:
    """Check if text contains exposed credentials.

    Args:
        text: Text to check

    Returns:
        True if credentials are detected
    """
    if not text or not isinstance(text, str):
        return False

    masker = CredentialMasker()

    # Check against all credential patterns
    for pattern in masker.CREDENTIAL_PATTERNS.values():
        if pattern.search(text):
            return True

    return False


def sanitize_for_logging(data: Any) -> Any:
    """Sanitize data for safe logging.

    Args:
        data: Data to sanitize

    Returns:
        Sanitized data safe for logging
    """
    return mask_sensitive_data(data)

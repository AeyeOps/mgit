"""mgit exception hierarchy and error handling utilities.

This module provides a standardized exception hierarchy for mgit and error
handling decorators for CLI commands to ensure consistent error handling
and user-friendly error messages.
"""

import asyncio
import functools
import logging
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar

import typer
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

T = TypeVar("T", bound=Callable[..., Any])


class MgitError(Exception):
    """Base exception for all mgit errors.

    All mgit-specific exceptions should inherit from this class.
    This allows for easy catching of all mgit errors while still
    being able to handle specific error types.
    """

    def __init__(self, message: str, exit_code: int = 1, details: str | None = None):
        """Initialize MgitError.

        Args:
            message: The error message to display
            exit_code: Exit code for CLI (default: 1)
            details: Additional details about the error (optional)
        """
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.details = details

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class ConfigurationError(MgitError):
    """Configuration-related errors.

    Raised when there are issues with mgit configuration, such as:
    - Missing required configuration values
    - Invalid configuration format
    - Unable to load/save configuration files
    """

    pass


class AuthenticationError(MgitError):
    """Authentication-related errors.

    Raised when authentication fails, such as:
    - Invalid PAT token
    - Expired credentials
    - Missing authentication information
    """

    def __init__(self, message: str, provider: str | None = None):
        """Initialize AuthenticationError.

        Args:
            message: The error message
            provider: The provider that failed authentication (optional)
        """
        details = f"Provider: {provider}" if provider else None
        super().__init__(message, exit_code=2, details=details)


class ConnectionError(MgitError):
    """Connection-related errors.

    Raised when connection to a service fails, such as:
    - Network timeout
    - Service unavailable
    - DNS resolution failures
    """

    def __init__(self, message: str, url: str | None = None):
        """Initialize ConnectionError.

        Args:
            message: The error message
            url: The URL that failed to connect (optional)
        """
        details = f"URL: {url}" if url else None
        super().__init__(message, exit_code=3, details=details)


class RepositoryOperationError(MgitError):
    """Repository operation errors.

    Raised when Git operations fail, such as:
    - Clone failures
    - Pull failures
    - Invalid repository state
    """

    def __init__(self, message: str, operation: str, repository: str | None = None):
        """Initialize RepositoryOperationError.

        Args:
            message: The error message
            operation: The operation that failed (clone, pull, etc.)
            repository: The repository name/URL (optional)
        """
        details = f"Operation: {operation}"
        if repository:
            details += f", Repository: {repository}"
        super().__init__(message, exit_code=4, details=details)


class ProjectNotFoundError(MgitError):
    """Project not found error.

    Raised when a specified project cannot be found in the provider.
    """

    def __init__(self, project_name: str, provider: str | None = None):
        """Initialize ProjectNotFoundError.

        Args:
            project_name: The name of the project that wasn't found
            provider: The provider being searched (optional)
        """
        message = f"Project '{project_name}' not found"
        if provider:
            message += f" in {provider}"
        super().__init__(message, exit_code=5)


class OrganizationNotFoundError(MgitError):
    """Organization not found error.

    Raised when a specified organization cannot be found or accessed.
    """

    def __init__(self, org_name: str, provider: str | None = None):
        """Initialize OrganizationNotFoundError.

        Args:
            org_name: The name/URL of the organization that wasn't found
            provider: The provider being used (optional)
        """
        message = f"Organization '{org_name}' not found or inaccessible"
        if provider:
            message += f" in {provider}"
        super().__init__(message, exit_code=6)


class ValidationError(MgitError):
    """Input validation error.

    Raised when user input fails validation, such as:
    - Invalid URLs
    - Invalid file paths
    - Invalid command arguments
    """

    def __init__(self, message: str, field: str | None = None):
        """Initialize ValidationError.

        Args:
            message: The error message
            field: The field that failed validation (optional)
        """
        if field:
            message = f"Validation error for '{field}': {message}"
        super().__init__(message, exit_code=7)


class FileSystemError(MgitError):
    """File system operation error.

    Raised when file system operations fail, such as:
    - Permission denied
    - Directory not found
    - Disk full
    """

    def __init__(self, message: str, path: str | None = None):
        """Initialize FileSystemError.

        Args:
            message: The error message
            path: The path that caused the error (optional)
        """
        details = f"Path: {path}" if path else None
        super().__init__(message, exit_code=8, details=details)


class ProviderError(MgitError):
    """Base exception for provider-specific errors.

    This is the base class for all provider-related errors that might
    occur when interacting with different Git providers (Azure DevOps,
    GitHub, GitLab, Bitbucket, etc.).
    """

    def __init__(self, message: str, provider: str, exit_code: int = 9):
        """Initialize ProviderError.

        Args:
            message: The error message
            provider: The name of the provider
            exit_code: Exit code for CLI (default: 9)
        """
        super().__init__(message, exit_code=exit_code, details=f"Provider: {provider}")
        self.provider = provider


class CLIError(MgitError):
    """CLI-specific errors.

    Raised when there are issues with CLI command execution, such as:
    - Invalid command syntax
    - Missing required arguments
    - Command execution failures
    """

    def __init__(self, message: str, command: str | None = None):
        """Initialize CLIError.

        Args:
            message: The error message
            command: The command that failed (optional)
        """
        details = f"Command: {command}" if command else None
        super().__init__(message, exit_code=10, details=details)


# Retry configuration
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
DEFAULT_RETRY_BACKOFF = 2.0  # exponential backoff multiplier


class RetryExhausted(MgitError):
    """Raised when all retry attempts have been exhausted."""

    def __init__(
        self, message: str, attempts: int, last_error: Exception | None = None
    ):
        """Initialize RetryExhausted.

        Args:
            message: The error message
            attempts: Number of attempts made
            last_error: The last error that occurred
        """
        details = f"Attempts: {attempts}"
        if last_error:
            details += f", Last error: {str(last_error)}"
        super().__init__(message, exit_code=11, details=details)
        self.attempts = attempts
        self.last_error = last_error


def retry_with_backoff(
    retries: int = DEFAULT_RETRY_ATTEMPTS,
    delay: float = DEFAULT_RETRY_DELAY,
    backoff: float = DEFAULT_RETRY_BACKOFF,
    exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        RepositoryOperationError,
    ),
    on_retry: Callable[[Exception, int], None] | None = None,
) -> Callable[[T], T]:
    """Decorator to retry operations with exponential backoff.

    Args:
        retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for exponential backoff
        exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called on each retry with (exception, attempt_number)

    Returns:
        Decorated function

    Example:
        @retry_with_backoff(retries=5, delay=2.0)
        def fetch_repository():
            # Operation that might fail
            pass
    """

    def decorator(func: T) -> T:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            current_delay = delay

            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == retries:
                        raise RetryExhausted(
                            f"Operation failed after {retries + 1} attempts",
                            attempts=retries + 1,
                            last_error=e,
                        )

                    if on_retry:
                        on_retry(e, attempt + 1)
                    else:
                        logger.warning(
                            "Attempt %d/%d failed: %s. Retrying in %.1fs...",
                            attempt + 1,
                            retries + 1,
                            str(e),
                            current_delay,
                        )

                    time.sleep(current_delay)
                    current_delay *= backoff

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry logic error")

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            current_delay = delay

            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == retries:
                        raise RetryExhausted(
                            f"Operation failed after {retries + 1} attempts",
                            attempts=retries + 1,
                            last_error=e,
                        )

                    if on_retry:
                        on_retry(e, attempt + 1)
                    else:
                        logger.warning(
                            "Attempt %d/%d failed: %s. Retrying in %.1fs...",
                            attempt + 1,
                            retries + 1,
                            str(e),
                            current_delay,
                        )

                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry logic error")

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


@contextmanager
def error_context(
    operation: str,
    *,
    suppress: tuple[type[Exception], ...] | None = None,
    transform: dict[type[Exception], type[MgitError]] | None = None,
    details: dict[str, Any] | None = None,
) -> Generator[None]:
    """Context manager for consistent error handling and transformation.

    Args:
        operation: Description of the operation being performed
        suppress: Tuple of exception types to suppress (log but don't raise)
        transform: Dict mapping exception types to MgitError types
        details: Additional context details to include in errors

    Example:
        with error_context("cloning repository",
                         transform={GitCommandError: RepositoryOperationError},
                         details={"repo": "myrepo"}):
            # Perform git clone operation
            pass
    """
    try:
        yield
    except Exception as e:
        # Check if we should suppress this exception
        if suppress and isinstance(e, suppress):
            logger.warning("Suppressed error during %s: %s", operation, str(e))
            return

        # Check if we should transform this exception
        if transform:
            for exc_type, mgit_error_type in transform.items():
                if isinstance(e, exc_type):
                    error_msg = f"Failed to {operation}: {str(e)}"

                    # Build kwargs for the MgitError constructor
                    kwargs: dict[str, Any] = {"message": error_msg}

                    # Add operation-specific details
                    if details:
                        if mgit_error_type == RepositoryOperationError:
                            kwargs["operation"] = operation
                            kwargs["repository"] = details.get("repo")
                        elif mgit_error_type == FileSystemError:
                            kwargs["path"] = details.get("path")
                        elif mgit_error_type == ConnectionError:
                            kwargs["url"] = details.get("url")
                        elif mgit_error_type == AuthenticationError:
                            kwargs["provider"] = details.get("provider")
                        elif mgit_error_type == ValidationError:
                            kwargs["field"] = details.get("field")

                    raise mgit_error_type(**kwargs) from e

        # Re-raise MgitErrors as-is
        if isinstance(e, MgitError):
            raise

        # Convert unknown errors to generic MgitError
        raise MgitError(
            f"Unexpected error during {operation}: {str(e)}",
            details=str(details) if details else None,
        ) from e


@contextmanager
def temporary_error_handler(
    *,
    show_traceback: bool = False,
    exit_on_error: bool = True,
) -> Generator[None]:
    """Temporary error handler for specific code blocks.

    Args:
        show_traceback: Whether to show full traceback
        exit_on_error: Whether to exit on error

    Example:
        with temporary_error_handler(show_traceback=True):
            # Code that might fail
            pass
    """
    try:
        yield
    except MgitError as e:
        if show_traceback:
            console.print_exception()
        else:
            console.print(f"[red]Error:[/red] {e.message}")
            if e.details:
                console.print(f"[dim]{e.details}[/dim]")

        if exit_on_error:
            raise typer.Exit(code=e.exit_code)
        raise
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        if exit_on_error:
            raise typer.Exit(code=130)
        raise
    except Exception as e:
        if show_traceback:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error:[/red] {str(e)}")

        if exit_on_error:
            raise typer.Exit(code=1)
        raise


def error_handler(
    *,
    exceptions: type[Exception] | tuple[type[Exception], ...] | None = None,
    exit_on_error: bool = True,
    log_traceback: bool = True,
) -> Callable[[T], T]:
    """Decorator for consistent error handling in CLI commands.

    This decorator catches specified exceptions and handles them consistently:
    - Logs the error with appropriate level
    - Shows user-friendly error messages
    - Exits with appropriate exit code

    Args:
        exceptions: Exception types to catch (default: catch all MgitError)
        exit_on_error: Whether to exit the program on error (default: True)
        log_traceback: Whether to log the full traceback (default: True)

    Returns:
        Decorated function

    Example:
        @error_handler()
        def clone_command():
            # Command implementation
            pass

        @error_handler(exceptions=(ConnectionError, AuthenticationError))
        def login_command():
            # Command implementation
            pass
    """
    if exceptions is None:
        exceptions = MgitError

    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                # Handle MgitError and its subclasses
                if isinstance(e, MgitError):
                    console.print(f"[red]Error:[/red] {e.message}")
                    if e.details:
                        console.print(f"[dim]{e.details}[/dim]")

                    if log_traceback:
                        logger.exception("Command failed with error: %s", e)
                    else:
                        logger.error("Command failed: %s", e)

                    if exit_on_error:
                        raise typer.Exit(code=e.exit_code)
                    raise

                # Handle provider errors
                elif isinstance(e, ProviderError):
                    console.print(f"[red]Error:[/red] {e.message}")
                    if e.details:
                        console.print(f"[dim]{e.details}[/dim]")

                    if log_traceback:
                        logger.exception("Provider error: %s", e)
                    else:
                        logger.error("Provider error: %s", e)

                    if exit_on_error:
                        raise typer.Exit(code=e.exit_code)
                    raise

                # Handle other exceptions
                else:
                    console.print(f"[red]Error:[/red] {str(e)}")

                    if log_traceback:
                        logger.exception("Unexpected error: %s", e)
                    else:
                        logger.error("Unexpected error: %s", e)

                    if exit_on_error:
                        raise typer.Exit(code=1)
                    raise

            except KeyboardInterrupt:
                console.print("\n[yellow]Operation cancelled by user[/yellow]")
                if exit_on_error:
                    raise typer.Exit(code=130)  # Standard SIGINT exit code
                raise
            except Exception as e:
                # Catch-all for any unexpected errors
                console.print(f"[red]Unexpected error:[/red] {str(e)}")
                logger.exception("Unexpected error in command: %s", e)

                if exit_on_error:
                    raise typer.Exit(code=1)
                raise

        return wrapper  # type: ignore

    return decorator


def async_error_handler(
    *,
    exceptions: type[Exception] | tuple[type[Exception], ...] | None = None,
    exit_on_error: bool = True,
    log_traceback: bool = True,
) -> Callable[[T], T]:
    """Decorator for consistent error handling in async CLI commands.

    Similar to error_handler but for async functions.

    Args:
        exceptions: Exception types to catch (default: catch all MgitError)
        exit_on_error: Whether to exit the program on error (default: True)
        log_traceback: Whether to log the full traceback (default: True)

    Returns:
        Decorated function
    """
    if exceptions is None:
        exceptions = MgitError

    def decorator(func: T) -> T:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                # Same error handling logic as sync version
                if isinstance(e, MgitError):
                    console.print(f"[red]Error:[/red] {e.message}")
                    if e.details:
                        console.print(f"[dim]{e.details}[/dim]")

                    if log_traceback:
                        logger.exception("Async command failed with error: %s", e)
                    else:
                        logger.error("Async command failed: %s", e)

                    if exit_on_error:
                        raise typer.Exit(code=e.exit_code)
                    raise

                elif isinstance(e, ProviderError):
                    console.print(f"[red]Error:[/red] {e.message}")
                    if e.details:
                        console.print(f"[dim]{e.details}[/dim]")

                    if log_traceback:
                        logger.exception("Async provider error: %s", e)
                    else:
                        logger.error("Async provider error: %s", e)

                    if exit_on_error:
                        raise typer.Exit(code=e.exit_code)
                    raise

                else:
                    console.print(f"[red]Error:[/red] {str(e)}")

                    if log_traceback:
                        logger.exception("Unexpected async error: %s", e)
                    else:
                        logger.error("Unexpected async error: %s", e)

                    if exit_on_error:
                        raise typer.Exit(code=1)
                    raise

            except KeyboardInterrupt:
                console.print("\n[yellow]Operation cancelled by user[/yellow]")
                if exit_on_error:
                    raise typer.Exit(code=130)
                raise
            except Exception as e:
                console.print(f"[red]Unexpected error:[/red] {str(e)}")
                logger.exception("Unexpected error in async command: %s", e)

                if exit_on_error:
                    raise typer.Exit(code=1)
                raise

        return wrapper  # type: ignore

    return decorator


# Convenience function for validating inputs
def validate_url(url: str, provider: str | None = None) -> None:
    """Validate that a URL is properly formatted.

    Args:
        url: The URL to validate
        provider: The provider type (optional, for better error messages)

    Raises:
        ValidationError: If the URL is invalid
    """
    if not url:
        raise ValidationError("URL cannot be empty", field="url")

    if not url.startswith(("http://", "https://")):
        raise ValidationError(
            f"URL must start with http:// or https://, got: {url}", field="url"
        )

    # Additional provider-specific validation could go here
    if (
        provider == "azuredevops"
        and "dev.azure.com" not in url
        and "visualstudio.com" not in url
    ):
        raise ValidationError(
            "Azure DevOps URL must contain 'dev.azure.com' or 'visualstudio.com'",
            field="url",
        )


def validate_path(path: str | Path, must_exist: bool = False) -> Path:
    """Validate a file system path.

    Args:
        path: The path to validate
        must_exist: Whether the path must already exist

    Returns:
        The validated Path object

    Raises:
        ValidationError: If the path is invalid
        FileSystemError: If the path doesn't exist (when must_exist=True)
    """
    try:
        path_obj = Path(path)
    except Exception as e:
        raise ValidationError(f"Invalid path: {e}", field="path")

    if must_exist and not path_obj.exists():
        raise FileSystemError("Path does not exist", path=str(path_obj))

    return path_obj


# Error reporting utilities
class ErrorReport:
    """Utility class for generating detailed error reports."""

    def __init__(self, error: Exception, context: dict[str, Any] | None = None):
        """Initialize ErrorReport.

        Args:
            error: The exception to report on
            context: Additional context information
        """
        self.error = error
        self.context = context or {}
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Convert error report to dictionary format.

        Returns:
            Dictionary containing error details
        """
        report = {
            "error_type": type(self.error).__name__,
            "error_message": str(self.error),
            "timestamp": self.timestamp,
            "context": self.context,
        }

        if isinstance(self.error, MgitError):
            report["exit_code"] = self.error.exit_code
            if self.error.details:
                report["details"] = self.error.details

        return report

    def format_for_display(self) -> str:
        """Format error report for console display.

        Returns:
            Formatted error report string
        """
        lines = [
            f"Error Type: {type(self.error).__name__}",
            f"Message: {str(self.error)}",
        ]

        if isinstance(self.error, MgitError) and self.error.details:
            lines.append(f"Details: {self.error.details}")

        if self.context:
            lines.append("Context:")
            for key, value in self.context.items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)

    def format_for_log(self) -> str:
        """Format error report for logging.

        Returns:
            Formatted error report string for logs
        """
        import json

        return json.dumps(self.to_dict(), indent=2)


def create_error_report(
    error: Exception, operation: str | None = None, **context: Any
) -> ErrorReport:
    """Create an error report with context.

    Args:
        error: The exception to report
        operation: The operation that was being performed
        **context: Additional context as keyword arguments

    Returns:
        ErrorReport instance

    Example:
        report = create_error_report(
            error,
            operation="clone repository",
            repository="myrepo",
            url="https://github.com/user/repo"
        )
    """
    if operation:
        context["operation"] = operation

    return ErrorReport(error, context)


# Export all exceptions and utilities
__all__ = [
    # Base exception
    "MgitError",
    # Specific exceptions
    "ConfigurationError",
    "AuthenticationError",
    "ConnectionError",
    "RepositoryOperationError",
    "ProjectNotFoundError",
    "OrganizationNotFoundError",
    "ValidationError",
    "FileSystemError",
    "ProviderError",
    "CLIError",
    "RetryExhausted",
    # Decorators
    "error_handler",
    "async_error_handler",
    "retry_with_backoff",
    # Context managers
    "error_context",
    "temporary_error_handler",
    # Validation utilities
    "validate_url",
    "validate_path",
    # Error reporting
    "ErrorReport",
    "create_error_report",
    # Constants
    "DEFAULT_RETRY_ATTEMPTS",
    "DEFAULT_RETRY_DELAY",
    "DEFAULT_RETRY_BACKOFF",
]

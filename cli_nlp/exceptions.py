"""Custom exceptions for CLI-NLP."""


class QTCError(Exception):
    """Base exception for all QTC errors."""

    def __init__(self, message: str, details: str | None = None):
        """
        Initialize QTC error.

        Args:
            message: User-friendly error message
            details: Optional detailed error information
        """
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class ConfigurationError(QTCError):
    """Configuration-related errors."""

    def __init__(self, message: str, config_path: str | None = None):
        """
        Initialize configuration error.

        Args:
            message: Error message
            config_path: Path to config file if relevant
        """
        details = f"Config file: {config_path}" if config_path else None
        super().__init__(message, details)
        self.config_path = config_path


class APIError(QTCError):
    """API-related errors."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        status_code: int | None = None,
        details: str | None = None,
    ):
        """
        Initialize API error.

        Args:
            message: Error message
            provider: Provider name if relevant
            status_code: HTTP status code if relevant
            details: Additional error details
        """
        error_details = []
        if provider:
            error_details.append(f"Provider: {provider}")
        if status_code:
            error_details.append(f"Status: {status_code}")
        if details:
            error_details.append(f"Details: {details}")

        combined_details = "\n".join(error_details) if error_details else None
        super().__init__(message, combined_details)
        self.provider = provider
        self.status_code = status_code


class CacheError(QTCError):
    """Cache-related errors."""

    def __init__(self, message: str, cache_path: str | None = None):
        """
        Initialize cache error.

        Args:
            message: Error message
            cache_path: Path to cache file if relevant
        """
        details = f"Cache file: {cache_path}" if cache_path else None
        super().__init__(message, details)
        self.cache_path = cache_path


class CommandExecutionError(QTCError):
    """Command execution errors."""

    def __init__(
        self,
        message: str,
        command: str | None = None,
        exit_code: int | None = None,
        stderr: str | None = None,
    ):
        """
        Initialize command execution error.

        Args:
            message: Error message
            command: Command that failed
            exit_code: Exit code if available
            stderr: Error output if available
        """
        error_details = []
        if command:
            error_details.append(f"Command: {command}")
        if exit_code is not None:
            error_details.append(f"Exit code: {exit_code}")
        if stderr:
            error_details.append(f"Error output: {stderr}")

        combined_details = "\n".join(error_details) if error_details else None
        super().__init__(message, combined_details)
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr


class ValidationError(QTCError):
    """Input validation errors."""

    def __init__(self, message: str, field: str | None = None, value: str | None = None):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Field name that failed validation
            value: Invalid value if relevant
        """
        error_details = []
        if field:
            error_details.append(f"Field: {field}")
        if value:
            error_details.append(f"Value: {value[:100]}")  # Truncate long values

        combined_details = "\n".join(error_details) if error_details else None
        super().__init__(message, combined_details)
        self.field = field
        self.value = value

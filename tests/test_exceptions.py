"""Tests for custom exceptions."""

import pytest

from cli_nlp.exceptions import (
    APIError,
    CacheError,
    CommandExecutionError,
    ConfigurationError,
    QTCError,
    ValidationError,
)


class TestQTCError:
    """Test QTCError base exception."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = QTCError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details is None

    def test_error_with_details(self):
        """Test error with details."""
        error = QTCError("Test error", details="Additional info")
        assert "Test error" in str(error)
        assert "Additional info" in str(error)
        assert error.details == "Additional info"


class TestConfigurationError:
    """Test ConfigurationError."""

    def test_basic_config_error(self):
        """Test basic configuration error."""
        error = ConfigurationError("Invalid config")
        assert "Invalid config" in str(error)
        assert error.config_path is None

    def test_config_error_with_path(self):
        """Test configuration error with path."""
        error = ConfigurationError("Invalid config", config_path="/path/to/config.json")
        assert "Invalid config" in str(error)
        assert error.config_path == "/path/to/config.json"
        assert "config.json" in str(error)


class TestAPIError:
    """Test APIError."""

    def test_basic_api_error(self):
        """Test basic API error."""
        error = APIError("API call failed")
        assert "API call failed" in str(error)
        assert error.provider is None
        assert error.status_code is None

    def test_api_error_with_provider(self):
        """Test API error with provider."""
        error = APIError("API call failed", provider="openai")
        assert "API call failed" in str(error)
        assert error.provider == "openai"
        assert "openai" in str(error)

    def test_api_error_with_status_code(self):
        """Test API error with status code."""
        error = APIError("API call failed", status_code=500)
        assert "API call failed" in str(error)
        assert error.status_code == 500
        assert "500" in str(error)

    def test_api_error_full(self):
        """Test API error with all fields."""
        error = APIError(
            "API call failed",
            provider="openai",
            status_code=429,
            details="Rate limit exceeded",
        )
        assert "API call failed" in str(error)
        assert error.provider == "openai"
        assert error.status_code == 429
        assert "429" in str(error)
        assert "Rate limit exceeded" in str(error)


class TestCacheError:
    """Test CacheError."""

    def test_basic_cache_error(self):
        """Test basic cache error."""
        error = CacheError("Cache operation failed")
        assert "Cache operation failed" in str(error)
        assert error.cache_path is None

    def test_cache_error_with_path(self):
        """Test cache error with path."""
        error = CacheError("Cache operation failed", cache_path="/path/to/cache.json")
        assert "Cache operation failed" in str(error)
        assert error.cache_path == "/path/to/cache.json"
        assert "cache.json" in str(error)


class TestCommandExecutionError:
    """Test CommandExecutionError."""

    def test_basic_execution_error(self):
        """Test basic command execution error."""
        error = CommandExecutionError("Command failed")
        assert "Command failed" in str(error)
        assert error.command is None
        assert error.exit_code is None
        assert error.stderr is None

    def test_execution_error_with_command(self):
        """Test execution error with command."""
        error = CommandExecutionError("Command failed", command="rm -rf /")
        assert "Command failed" in str(error)
        assert error.command == "rm -rf /"
        assert "rm -rf /" in str(error)

    def test_execution_error_with_exit_code(self):
        """Test execution error with exit code."""
        error = CommandExecutionError("Command failed", exit_code=1)
        assert "Command failed" in str(error)
        assert error.exit_code == 1
        assert "1" in str(error)

    def test_execution_error_full(self):
        """Test execution error with all fields."""
        error = CommandExecutionError(
            "Command failed",
            command="test-command",
            exit_code=127,
            stderr="command not found",
        )
        assert "Command failed" in str(error)
        assert error.command == "test-command"
        assert error.exit_code == 127
        assert error.stderr == "command not found"
        assert "test-command" in str(error)
        assert "127" in str(error)
        assert "command not found" in str(error)


class TestValidationError:
    """Test ValidationError."""

    def test_basic_validation_error(self):
        """Test basic validation error."""
        error = ValidationError("Invalid input")
        assert "Invalid input" in str(error)
        assert error.field is None
        assert error.value is None

    def test_validation_error_with_field(self):
        """Test validation error with field."""
        error = ValidationError("Invalid input", field="query")
        assert "Invalid input" in str(error)
        assert error.field == "query"
        assert "query" in str(error)

    def test_validation_error_with_value(self):
        """Test validation error with value."""
        error = ValidationError("Invalid input", value="test-value")
        assert "Invalid input" in str(error)
        assert error.value == "test-value"
        assert "test-value" in str(error)

    def test_validation_error_truncates_long_values(self):
        """Test that long values are truncated in details."""
        long_value = "x" * 200
        error = ValidationError("Invalid input", value=long_value)
        # Value itself is not truncated, but details are
        assert error.value == long_value  # Original value preserved
        assert "x" * 100 in error.details  # Truncated in details

    def test_validation_error_full(self):
        """Test validation error with all fields."""
        error = ValidationError("Invalid input", field="query", value="empty-string")
        assert "Invalid input" in str(error)
        assert error.field == "query"
        assert error.value == "empty-string"
        assert "query" in str(error)
        assert "empty-string" in str(error)

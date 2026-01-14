"""Tests for retry logic edge cases."""

import time
from unittest.mock import patch

import pytest

from cli_nlp.exceptions import APIError
from cli_nlp.retry import RetryConfig, retry_with_backoff


class TestRetryEdgeCases:
    """Test edge cases in retry logic."""

    def test_retry_config_custom_exceptions(self):
        """Test retry config with custom exceptions."""
        config = RetryConfig(
            max_attempts=2,
            initial_delay=0.01,
            retryable_exceptions=(ValueError, TypeError),
        )
        assert ValueError in config.retryable_exceptions
        assert TypeError in config.retryable_exceptions
        assert Exception not in config.retryable_exceptions

    def test_retry_non_retryable_exception(self):
        """Test that non-retryable exceptions don't retry."""
        call_count = 0

        @retry_with_backoff(
            RetryConfig(
                max_attempts=3,
                initial_delay=0.01,
                retryable_exceptions=(ValueError,),
            )
        )
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retryable")

        with pytest.raises(TypeError):
            failing_function()

        assert call_count == 1  # Should not retry

    def test_retry_max_delay_respected(self):
        """Test that max delay is respected."""
        delays = []

        def mock_sleep(delay):
            delays.append(delay)

        call_count = 0

        @retry_with_backoff(
            RetryConfig(
                max_attempts=5,
                initial_delay=10.0,  # Start below max_delay
                max_delay=60.0,
                exponential_base=2.0,
            )
        )
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise ValueError("Retryable")
            return "success"

        with patch("time.sleep", side_effect=mock_sleep):
            result = failing_function()
            assert result == "success"

        # All delays should be capped at max_delay
        assert all(delay <= 60.0 for delay in delays)
        assert len(delays) == 4  # 4 retries

    def test_retry_no_config(self):
        """Test retry decorator without config (uses defaults)."""
        call_count = 0

        @retry_with_backoff()  # No config provided
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()
        assert result == "success"
        assert call_count == 1

    def test_retry_4xx_error_no_retry(self):
        """Test that 4xx errors don't retry."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.01))
        def client_error_function():
            nonlocal call_count
            call_count += 1
            raise APIError("Client error", status_code=400)

        with pytest.raises(APIError):
            client_error_function()

        assert call_count == 1  # Should not retry on 4xx

    def test_retry_5xx_error_retries(self):
        """Test that 5xx errors do retry."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.01))
        def server_error_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APIError("Server error", status_code=500)
            return "success"

        result = server_error_function()
        assert result == "success"
        assert call_count == 3  # Should retry on 5xx

    def test_retry_api_error_no_status_code(self):
        """Test retry with APIError but no status_code."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.01))
        def api_error_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APIError("API error")  # No status_code
            return "success"

        result = api_error_function()
        assert result == "success"
        assert call_count == 3  # Should retry when no status_code

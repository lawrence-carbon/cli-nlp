"""Tests for retry logic."""

import time
from unittest.mock import MagicMock, patch

import pytest

from cli_nlp.exceptions import APIError
from cli_nlp.retry import RetryConfig, retry_with_backoff


class TestRetryConfig:
    """Test RetryConfig."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert Exception in config.retryable_exceptions

    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
        )
        assert config.max_attempts == 5
        assert config.initial_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0


class TestRetryWithBackoff:
    """Test retry_with_backoff decorator."""

    def test_successful_call_no_retry(self):
        """Test that successful calls don't retry."""
        call_count = 0

        @retry_with_backoff()
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_exception(self):
        """Test that function retries on exception."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.01))
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            return "success"

        result = failing_function()
        assert result == "success"
        assert call_count == 3

    def test_max_attempts_exceeded(self):
        """Test that exception is raised after max attempts."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.01))
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_failing_function()

        assert call_count == 3

    def test_exponential_backoff(self):
        """Test that delays increase exponentially."""
        delays = []

        original_sleep = time.sleep

        def mock_sleep(delay):
            delays.append(delay)
            original_sleep(0)  # Don't actually wait

        call_count = 0

        @retry_with_backoff(RetryConfig(max_attempts=4, initial_delay=0.1, exponential_base=2.0))
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Test error")
            return "success"

        with patch("time.sleep", side_effect=mock_sleep):
            failing_function()

        # Should have delays: 0.1, 0.2, 0.4 (exponential backoff)
        assert len(delays) == 3
        assert delays[0] == pytest.approx(0.1, rel=0.1)
        assert delays[1] == pytest.approx(0.2, rel=0.1)
        assert delays[2] == pytest.approx(0.4, rel=0.1)

    def test_max_delay_cap(self):
        """Test that delays don't exceed max_delay."""
        delays = []

        original_sleep = time.sleep

        def mock_sleep(delay):
            delays.append(delay)
            original_sleep(0)  # Don't actually wait

        call_count = 0

        @retry_with_backoff(
            RetryConfig(max_attempts=5, initial_delay=50.0, max_delay=60.0, exponential_base=2.0)
        )
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise ValueError("Test error")
            return "success"

        with patch("time.sleep", side_effect=mock_sleep):
            failing_function()

        # All delays should be capped at max_delay
        assert all(delay <= 60.0 for delay in delays)

    def test_no_retry_on_4xx_errors(self):
        """Test that 4xx errors don't retry."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.01))
        def client_error_function():
            nonlocal call_count
            call_count += 1
            raise APIError("Client error", status_code=400)

        with pytest.raises(APIError):
            client_error_function()

        # Should not retry on 4xx errors
        assert call_count == 1

    def test_retry_on_5xx_errors(self):
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
        assert call_count == 3

    def test_custom_retryable_exceptions(self):
        """Test custom retryable exceptions."""
        call_count = 0

        @retry_with_backoff(
            RetryConfig(
                max_attempts=3,
                initial_delay=0.01,
                retryable_exceptions=(ValueError,),
            )
        )
        def custom_exception_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retryable")
            return "success"

        result = custom_exception_function()
        assert result == "success"
        assert call_count == 3

    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions don't retry."""
        call_count = 0

        @retry_with_backoff(
            RetryConfig(
                max_attempts=3,
                initial_delay=0.01,
                retryable_exceptions=(ValueError,),
            )
        )
        def non_retryable_function():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retryable")

        with pytest.raises(TypeError):
            non_retryable_function()

        # Should not retry on non-retryable exception
        assert call_count == 1

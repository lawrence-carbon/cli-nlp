"""Retry logic with exponential backoff for API calls."""

import time
from functools import wraps
from typing import Any, Callable, TypeVar

from cli_nlp.exceptions import APIError
from cli_nlp.logger import get_logger

logger = get_logger(__name__)
T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff calculation
            retryable_exceptions: Tuple of exception types that should trigger retry
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions


def retry_with_backoff(config: RetryConfig | None = None):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        config: Retry configuration (uses defaults if None)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(RetryConfig(max_attempts=3))
        def api_call():
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            delay = config.initial_delay

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    # Don't retry on certain errors
                    if isinstance(e, APIError) and e.status_code:
                        # Don't retry on 4xx errors (client errors)
                        if 400 <= e.status_code < 500:
                            logger.error(
                                f"Client error ({e.status_code}), not retrying: {e}"
                            )
                            raise

                    if attempt == config.max_attempts:
                        logger.error(
                            f"Failed after {config.max_attempts} attempts: {e}",
                            exc_info=True,
                        )
                        raise

                    logger.warning(
                        f"Attempt {attempt}/{config.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * config.exponential_base, config.max_delay)

            # Should never reach here, but type checker needs it
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry logic failed unexpectedly")

        return wrapper

    return decorator

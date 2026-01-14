"""Structured logging configuration for CLI-NLP."""

import logging
import sys
from pathlib import Path
from typing import Any

from rich.logging import RichHandler


class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive data from logs."""

    SENSITIVE_PATTERNS = [
        "api_key",
        "api-key",
        "apikey",
        "password",
        "secret",
        "token",
        "sk-",
        "sk_",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records and redact sensitive data."""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            msg = record.msg
            for pattern in self.SENSITIVE_PATTERNS:
                # Simple redaction - replace sensitive patterns
                if pattern.lower() in msg.lower():
                    # Redact the value after the pattern
                    parts = msg.split(pattern)
                    if len(parts) > 1:
                        # Redact the part after the pattern
                        redacted = f"{parts[0]}{pattern}=***REDACTED***"
                        record.msg = redacted
        return True


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    verbose: bool = False,
) -> logging.Logger:
    """
    Set up structured logging with Rich console handler and optional file handler.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        verbose: Enable DEBUG level logging

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("cli_nlp")
    logger.setLevel(logging.DEBUG if verbose else getattr(logging, level.upper()))

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Rich console handler for beautiful output
    console_handler = RichHandler(
        rich_tracebacks=True,
        show_time=True,
        show_path=False,  # Don't show full paths in console
        markup=True,
        console=None,  # Use default console
    )
    console_handler.setLevel(logging.INFO if not verbose else logging.DEBUG)

    # Add sensitive data filter
    console_handler.addFilter(SensitiveDataFilter())
    logger.addHandler(console_handler)

    # File handler for persistent logs
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(formatter)
        # Add filter to file handler too
        file_handler.addFilter(SensitiveDataFilter())
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Optional logger name (defaults to 'cli_nlp')

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"cli_nlp.{name}")
    return logging.getLogger("cli_nlp")

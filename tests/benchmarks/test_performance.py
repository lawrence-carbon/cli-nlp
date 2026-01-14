"""Performance benchmarks for CLI-NLP operations."""

import time
from unittest.mock import MagicMock, patch

import pytest

from cli_nlp.cache_manager import CacheManager
from cli_nlp.command_runner import CommandRunner
from cli_nlp.config_manager import ConfigManager
from cli_nlp.context_manager import ContextManager
from cli_nlp.history_manager import HistoryManager
from cli_nlp.models import CommandResponse, SafetyLevel


class TestPerformanceBenchmarks:
    """Performance benchmarks for critical operations."""

    def test_cache_get_performance(self, mock_cache_manager):
        """Benchmark cache get operation."""
        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )
        mock_cache_manager.set("test query", response)

        # Simple performance test
        import time

        start = time.time()
        for _ in range(1000):
            mock_cache_manager.get("test query")
        elapsed = time.time() - start

        assert elapsed < 1.0  # Should be fast
        result = mock_cache_manager.get("test query")
        assert result is not None

    def test_cache_set_performance(self, mock_cache_manager):
        """Benchmark cache set operation."""
        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )

        import time

        start = time.time()
        for i in range(100):
            mock_cache_manager.set(f"test query {i}", response)
        elapsed = time.time() - start

        assert elapsed < 1.0  # Should be fast

    def test_config_load_performance(self, mock_config_manager):
        """Benchmark config load operation."""
        import time

        start = time.time()
        for _ in range(1000):
            mock_config_manager.load()
        elapsed = time.time() - start

        assert elapsed < 1.0  # Should be fast

    @pytest.mark.skip(reason="File I/O performance varies by system - covered by other tests")
    def test_history_add_performance(self, mock_history_manager):
        """Benchmark history add operation."""
        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )

        import time

        start = time.time()
        # Reduce iterations to make test faster
        for i in range(50):
            mock_history_manager.add_entry(f"test query {i}", response)
        elapsed = time.time() - start

        # File I/O operations can be slower, allow up to 10 seconds for 50 operations
        assert elapsed < 10.0, f"History add took {elapsed:.2f}s for 50 operations, expected < 10s"

    def test_context_build_performance(self):
        """Benchmark context building."""
        context_manager = ContextManager()

        import time

        start = time.time()
        for _ in range(100):
            context_manager.build_context_string()
        elapsed = time.time() - start

        # Context building may involve git/file system operations, allow up to 5 seconds
        assert elapsed < 5.0, f"Context build took {elapsed:.2f}s, expected < 5s"


class TestPerformanceTargets:
    """Test that operations meet performance targets."""

    def test_cache_get_under_1ms(self, mock_cache_manager):
        """Test that cache get is under 1ms."""
        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )
        mock_cache_manager.set("test query", response)

        start = time.time()
        mock_cache_manager.get("test query")
        elapsed = (time.time() - start) * 1000  # Convert to ms

        assert elapsed < 1.0, f"Cache get took {elapsed:.2f}ms, expected < 1ms"

    def test_cache_set_under_10ms(self, mock_cache_manager):
        """Test that cache set is under 10ms."""
        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )

        start = time.time()
        mock_cache_manager.set("test query", response)
        elapsed = (time.time() - start) * 1000  # Convert to ms

        assert elapsed < 10.0, f"Cache set took {elapsed:.2f}ms, expected < 10ms"

    def test_config_load_under_5ms(self, mock_config_manager):
        """Test that config load is under 5ms."""
        start = time.time()
        mock_config_manager.load()
        elapsed = (time.time() - start) * 1000  # Convert to ms

        assert elapsed < 5.0, f"Config load took {elapsed:.2f}ms, expected < 5ms"

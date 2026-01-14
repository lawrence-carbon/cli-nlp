"""Integration tests for cache functionality."""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cli_nlp.cache_manager import CacheEntry, CacheManager
from cli_nlp.command_runner import CommandRunner
from cli_nlp.config_manager import ConfigManager
from cli_nlp.context_manager import ContextManager
from cli_nlp.history_manager import HistoryManager
from cli_nlp.models import CommandResponse, SafetyLevel


class TestCacheIntegration:
    """Test cache integration with command generation."""

    def test_cache_persistence(self, temp_dir, mock_config_manager):
        """Test that cache persists across instances."""
        cache_file = temp_dir / "cache.json"
        cache_manager1 = CacheManager(ttl_seconds=86400)
        cache_manager1.cache_path = cache_file

        # Add entry
        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )
        cache_manager1.set("list files", response)

        # Create new instance with same cache file
        cache_manager2 = CacheManager(ttl_seconds=86400)
        cache_manager2.cache_path = cache_file
        cache_manager2._load_cache()

        # Should retrieve cached entry
        cached = cache_manager2.get("list files")
        assert cached is not None
        assert cached.command == "ls -la"

    def test_cache_expiration(self, temp_dir):
        """Test that expired cache entries are not returned."""
        cache_file = temp_dir / "cache.json"
        cache_manager = CacheManager(ttl_seconds=1)  # 1 second TTL
        cache_manager.cache_path = cache_file

        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )

        # Add entry with short TTL
        cache_manager.set("list files", response, ttl_seconds=1)

        # Should be available immediately
        cached = cache_manager.get("list files")
        assert cached is not None

        # Wait for expiration
        import time

        time.sleep(1.1)

        # Should not be available after expiration
        cached = cache_manager.get("list files")
        assert cached is None

    def test_cache_stats(self, mock_cache_manager):
        """Test cache statistics."""
        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )

        # Add entry
        mock_cache_manager.set("list files", response)

        # Miss (different query)
        mock_cache_manager.get("different query")

        # Hit
        mock_cache_manager.get("list files")

        stats = mock_cache_manager.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total"] == 2
        assert stats["hit_rate"] == 50.0

    def test_cache_corruption_recovery(self, temp_dir):
        """Test that corrupted cache file is handled gracefully."""
        cache_file = temp_dir / "cache.json"
        cache_file.write_text("invalid json{")

        cache_manager = CacheManager(ttl_seconds=86400)
        cache_manager.cache_path = cache_file

        # Should not raise exception, should start with empty cache
        cached = cache_manager.get("any query")
        assert cached is None

        # Should be able to add new entries
        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )
        cache_manager.set("list files", response)

        # Should work normally after recovery
        cached = cache_manager.get("list files")
        assert cached is not None

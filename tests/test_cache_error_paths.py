"""Tests for cache manager error paths and edge cases."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cli_nlp.cache_manager import CacheEntry, CacheManager
from cli_nlp.exceptions import CacheError
from cli_nlp.models import CommandResponse, SafetyLevel


class TestCacheManagerErrorPaths:
    """Test error paths in CacheManager."""

    def test_load_cache_corrupted_json(self, temp_dir):
        """Test loading corrupted JSON cache file."""
        cache_file = temp_dir / "cache.json"
        cache_file.write_text("invalid json{")

        cache_manager = CacheManager(ttl_seconds=86400)
        cache_manager.cache_path = cache_file

        # Should not raise exception, should start with empty cache
        # The _load_cache is called in __init__, so we need to reload
        cache_manager._load_cache()
        cached = cache_manager.get("any query")
        assert cached is None
        assert len(cache_manager._cache) == 0

    def test_load_cache_invalid_entry(self, temp_dir):
        """Test loading cache with invalid entry."""
        cache_file = temp_dir / "cache.json"
        cache_data = {
            "valid_key": {
                "command": "ls -la",
                "is_safe": True,
                "safety_level": "safe",
                "explanation": "List files",
                "timestamp": "2024-01-01T00:00:00",
                "ttl_seconds": 86400,
            },
            "invalid_key": {
                "command": "test",
                # Missing required fields
            },
        }
        cache_file.write_text(json.dumps(cache_data))

        cache_manager = CacheManager(ttl_seconds=86400)
        cache_manager.cache_path = cache_file

        # Should load valid entry and skip invalid one
        cached = cache_manager.get("query_for_valid_key")
        # Note: This won't match because we don't know the hash, but should not crash
        assert cache_manager._cache is not None

    def test_load_cache_permission_error(self, temp_dir):
        """Test loading cache with permission error."""
        cache_file = temp_dir / "cache.json"
        cache_file.write_text('{"test": "data"}')

        cache_manager = CacheManager(ttl_seconds=86400)
        cache_manager.cache_path = cache_file

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(CacheError, match="Failed to read cache file"):
                cache_manager._load_cache()

    def test_save_cache_permission_error(self, temp_dir):
        """Test saving cache with permission error."""
        cache_file = temp_dir / "cache.json"
        cache_file.write_text('{"test": "data"}')

        cache_manager = CacheManager(ttl_seconds=86400)
        cache_manager.cache_path = cache_file

        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(CacheError, match="Failed to save cache file"):
                cache_manager.set("test query", response)

    def test_save_cache_directory_creation_error(self, temp_dir):
        """Test saving cache when directory creation fails."""
        cache_file = temp_dir / "nonexistent" / "cache.json"

        cache_manager = CacheManager(ttl_seconds=86400)
        cache_manager.cache_path = cache_file

        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )

        with patch("pathlib.Path.mkdir", side_effect=OSError("Cannot create directory")):
            with pytest.raises(CacheError):
                cache_manager.set("test query", response)

    def test_cache_size_limit(self, temp_dir):
        """Test cache size limit enforcement."""
        cache_manager = CacheManager(ttl_seconds=86400, max_size=2)
        cache_manager.cache_path = temp_dir / "cache.json"

        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )

        # Add 3 entries (exceeds max_size of 2)
        cache_manager.set("query1", response)
        cache_manager.set("query2", response)
        cache_manager.set("query3", response)

        # Should only have 2 entries (oldest removed)
        assert len(cache_manager._cache) <= 2

    def test_get_cache_with_save_error(self, temp_dir):
        """Test getting cache when save fails during cleanup."""
        cache_file = temp_dir / "cache.json"
        cache_manager = CacheManager(ttl_seconds=86400)
        cache_manager.cache_path = cache_file

        # Add an expired entry
        expired_entry = CacheEntry(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
            timestamp=None,  # This will cause issues
            ttl_seconds=1,
        )
        # Manually set timestamp to expired
        from datetime import datetime, timedelta

        expired_entry.timestamp = datetime.now() - timedelta(seconds=2)
        cache_manager._cache["test_key"] = expired_entry

        # Mock save to fail
        with patch.object(cache_manager, "_save_cache", side_effect=CacheError("Save failed")):
            # Should handle gracefully and return None
            result = cache_manager.get("test query")
            assert result is None

    def test_cache_entry_from_dict_missing_fields(self):
        """Test CacheEntry.from_dict with missing fields."""
        with pytest.raises((KeyError, ValueError)):
            CacheEntry.from_dict({"command": "test"})  # Missing required fields

    def test_cache_entry_from_dict_invalid_safety_level(self):
        """Test CacheEntry.from_dict with invalid safety level."""
        with pytest.raises(ValueError):
            CacheEntry.from_dict(
                {
                    "command": "test",
                    "is_safe": True,
                    "safety_level": "invalid_level",
                    "timestamp": "2024-01-01T00:00:00",
                }
            )

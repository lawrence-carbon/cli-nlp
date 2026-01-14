"""Tests for cache manager edge cases."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cli_nlp.cache_manager import CacheEntry, CacheManager
from cli_nlp.models import CommandResponse, SafetyLevel


class TestCacheEdgeCases:
    """Test edge cases in CacheManager."""

    def test_cache_entry_expired(self):
        """Test cache entry expiration."""
        entry = CacheEntry(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
            timestamp=datetime.now() - timedelta(seconds=86401),  # Expired
            ttl_seconds=86400,
        )
        assert entry.is_expired() is True

    def test_cache_entry_not_expired(self):
        """Test cache entry not expired."""
        entry = CacheEntry(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
            timestamp=datetime.now() - timedelta(seconds=100),  # Not expired
            ttl_seconds=86400,
        )
        assert entry.is_expired() is False

    def test_cache_entry_to_dict(self):
        """Test cache entry to_dict conversion."""
        entry = CacheEntry(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
            timestamp=datetime.now(),
            ttl_seconds=86400,
        )
        data = entry.to_dict()
        assert data["command"] == "ls -la"
        assert data["is_safe"] is True
        assert data["safety_level"] == "safe"
        assert "timestamp" in data

    def test_cache_entry_from_dict(self):
        """Test cache entry from_dict conversion."""
        data = {
            "command": "ls -la",
            "is_safe": True,
            "safety_level": "safe",
            "explanation": "List files",
            "timestamp": datetime.now().isoformat(),
            "ttl_seconds": 86400,
        }
        entry = CacheEntry.from_dict(data)
        assert entry.command == "ls -la"
        assert entry.is_safe is True
        assert entry.safety_level == SafetyLevel.SAFE

    def test_cache_entry_to_command_response(self):
        """Test cache entry to CommandResponse conversion."""
        entry = CacheEntry(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
            timestamp=datetime.now(),
        )
        response = entry.to_command_response()
        assert isinstance(response, CommandResponse)
        assert response.command == "ls -la"
        assert response.is_safe is True

    def test_cache_get_with_different_model(self, mock_cache_manager):
        """Test cache get with different model."""
        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )

        # Cache with one model
        mock_cache_manager.set("list files", response, model="gpt-4o-mini")

        # Get with different model should miss
        cached = mock_cache_manager.get("list files", model="gpt-4o")
        assert cached is None

        # Get with same model should hit
        cached = mock_cache_manager.get("list files", model="gpt-4o-mini")
        assert cached is not None

    def test_cache_set_with_custom_ttl(self, mock_cache_manager):
        """Test cache set with custom TTL."""
        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )

        # Set with custom TTL
        mock_cache_manager.set("list files", response, ttl_seconds=3600)

        # Should be available
        cached = mock_cache_manager.get("list files")
        assert cached is not None

    def test_cache_stats_empty(self, mock_cache_manager):
        """Test cache stats when empty."""
        stats = mock_cache_manager.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total"] == 0
        assert stats["hit_rate"] == 0.0

    def test_cache_clear(self, mock_cache_manager):
        """Test clearing cache."""
        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )

        mock_cache_manager.set("list files", response)
        assert len(mock_cache_manager._cache) > 0

        mock_cache_manager.clear()
        assert len(mock_cache_manager._cache) == 0

        stats = mock_cache_manager.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

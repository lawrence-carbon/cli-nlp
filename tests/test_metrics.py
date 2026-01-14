"""Tests for metrics collection."""

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cli_nlp.metrics import Metrics, MetricsCollector


class TestMetrics:
    """Test Metrics data structure."""

    def test_metrics_defaults(self):
        """Test metrics default values."""
        metrics = Metrics()
        assert metrics.total_queries == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert metrics.api_calls == 0
        assert metrics.execution_time_avg == 0.0
        assert metrics.cache_hit_rate == 0.0

    def test_metrics_execution_time_avg(self):
        """Test execution time average calculation."""
        metrics = Metrics()
        metrics.execution_time_sum = 10.0
        metrics.execution_time_count = 5
        assert metrics.execution_time_avg == 2.0

    def test_metrics_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        metrics = Metrics()
        metrics.cache_hits = 8
        metrics.cache_misses = 2
        assert metrics.cache_hit_rate == 0.8

    def test_metrics_to_dict(self):
        """Test metrics to_dict conversion."""
        metrics = Metrics(
            total_queries=10,
            cache_hits=8,
            cache_misses=2,
            api_calls=2,
            execution_time_sum=5.0,
            execution_time_count=10,
        )
        data = metrics.to_dict()
        assert data["total_queries"] == 10
        assert data["cache_hits"] == 8
        assert data["cache_hit_rate"] == 0.8
        assert data["execution_time_avg"] == 0.5


class TestMetricsCollector:
    """Test MetricsCollector."""

    def test_init(self, temp_dir, monkeypatch):
        """Test MetricsCollector initialization."""
        metrics_file = temp_dir / "metrics.json"
        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        collector = MetricsCollector()
        assert collector._metrics.total_queries == 0

    def test_record_query_cached(self, temp_dir, monkeypatch):
        """Test recording a cached query."""
        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        collector = MetricsCollector()
        collector.record_query(cached=True, execution_time=0.1, provider="openai", model="gpt-4o-mini")
        assert collector._metrics.total_queries == 1
        assert collector._metrics.cache_hits == 1
        assert collector._metrics.cache_misses == 0
        assert collector._metrics.api_calls == 0

    def test_record_query_not_cached(self, temp_dir, monkeypatch):
        """Test recording a non-cached query."""
        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        collector = MetricsCollector()
        collector.record_query(cached=False, execution_time=0.5, provider="openai", model="gpt-4o-mini")
        assert collector._metrics.total_queries == 1
        assert collector._metrics.cache_hits == 0
        assert collector._metrics.cache_misses == 1
        assert collector._metrics.api_calls == 1

    def test_record_error(self, temp_dir, monkeypatch):
        """Test recording an error."""
        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        collector = MetricsCollector()
        collector.record_error(provider="openai")
        assert collector._metrics.errors == 1

    def test_record_command_execution(self, temp_dir, monkeypatch):
        """Test recording command execution."""
        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        collector = MetricsCollector()
        collector.record_command_execution(executed=True)
        assert collector._metrics.commands_executed == 1
        assert collector._metrics.commands_skipped == 0

        collector.record_command_execution(executed=False)
        assert collector._metrics.commands_executed == 1
        assert collector._metrics.commands_skipped == 1

    def test_get_stats(self, temp_dir, monkeypatch):
        """Test getting statistics."""
        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        collector = MetricsCollector()
        collector.record_query(cached=True, execution_time=0.1, provider="openai")
        collector.record_query(cached=False, execution_time=0.5, provider="openai")

        stats = collector.get_stats()
        assert stats["total_queries"] == 2
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["cache_hit_rate"] == 0.5

    def test_get_provider_comparison(self, temp_dir, monkeypatch):
        """Test getting provider comparison."""
        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        collector = MetricsCollector()
        collector.record_query(cached=False, execution_time=0.5, provider="openai", model="gpt-4o-mini")
        collector.record_query(cached=False, execution_time=0.3, provider="anthropic", model="claude-3-opus")

        comparison = collector.get_provider_comparison()
        assert len(comparison) == 2
        assert comparison[0]["provider"] in ["openai", "anthropic"]
        assert comparison[1]["provider"] in ["openai", "anthropic"]

    def test_reset(self, temp_dir, monkeypatch):
        """Test resetting metrics."""
        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        collector = MetricsCollector()
        collector.record_query(cached=True, execution_time=0.1, provider="openai")
        assert collector._metrics.total_queries == 1

        collector.reset()
        assert collector._metrics.total_queries == 0

    def test_load_metrics_from_file(self, temp_dir, monkeypatch):
        """Test loading metrics from file."""
        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        metrics_file = temp_dir / "cli-nlp" / "metrics.json"
        metrics_file.parent.mkdir(parents=True, exist_ok=True)
        metrics_data = {
            "total_queries": 10,
            "cache_hits": 8,
            "cache_misses": 2,
            "api_calls": 2,
            "execution_time_sum": 5.0,
            "execution_time_count": 10,
            "errors": 1,
            "commands_executed": 5,
            "commands_skipped": 5,
            "last_updated": "2024-01-01T00:00:00",
            "provider_stats": {},
        }
        metrics_file.write_text(json.dumps(metrics_data))

        collector = MetricsCollector()
        assert collector._metrics.total_queries == 10
        assert collector._metrics.cache_hits == 8

    def test_load_metrics_corrupted_file(self, temp_dir, monkeypatch):
        """Test loading metrics from corrupted file."""
        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        metrics_file = temp_dir / "cli-nlp" / "metrics.json"
        metrics_file.parent.mkdir(parents=True, exist_ok=True)
        metrics_file.write_text("invalid json{")

        collector = MetricsCollector()
        # Should start with empty metrics
        assert collector._metrics.total_queries == 0

    def test_provider_stats_tracking(self, temp_dir, monkeypatch):
        """Test provider statistics tracking."""
        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        collector = MetricsCollector()
        collector.record_query(cached=False, execution_time=0.5, provider="openai", model="gpt-4o-mini")
        collector.record_query(cached=False, execution_time=0.3, provider="openai", model="gpt-4o")

        assert "openai" in collector._metrics.provider_stats
        assert collector._metrics.provider_stats["openai"]["queries"] == 2
        assert collector._metrics.provider_stats["openai"]["api_calls"] == 2
        assert "gpt-4o-mini" in collector._metrics.provider_stats["openai"]["models"]
        assert "gpt-4o" in collector._metrics.provider_stats["openai"]["models"]

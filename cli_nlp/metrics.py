"""Metrics collection and reporting for QTC."""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cli_nlp.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Metrics:
    """Metrics data structure."""

    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0
    execution_time_sum: float = 0.0
    execution_time_count: int = 0
    errors: int = 0
    commands_executed: int = 0
    commands_skipped: int = 0
    last_updated: str | None = None
    provider_stats: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def execution_time_avg(self) -> float:
        """Calculate average execution time."""
        if self.execution_time_count == 0:
            return 0.0
        return self.execution_time_sum / self.execution_time_count

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_cache_operations = self.cache_hits + self.cache_misses
        if total_cache_operations == 0:
            return 0.0
        return self.cache_hits / total_cache_operations

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_queries": self.total_queries,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "api_calls": self.api_calls,
            "execution_time_avg": self.execution_time_avg,
            "execution_time_sum": self.execution_time_sum,
            "execution_time_count": self.execution_time_count,
            "errors": self.errors,
            "commands_executed": self.commands_executed,
            "commands_skipped": self.commands_skipped,
            "last_updated": self.last_updated,
            "provider_stats": self.provider_stats,
        }


class MetricsCollector:
    """Collect and report metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics_path = self._get_metrics_path()
        self._metrics = self._load_metrics()

    def _get_metrics_path(self) -> Path:
        """Get path to metrics file."""
        xdg_data = os.getenv("XDG_DATA_HOME")
        if xdg_data:
            data_dir = Path(xdg_data) / "cli-nlp"
        else:
            data_dir = Path.home() / ".local" / "share" / "cli-nlp"

        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "metrics.json"

    def _load_metrics(self) -> Metrics:
        """Load metrics from file."""
        if not self.metrics_path.exists():
            return Metrics()

        try:
            with open(self.metrics_path, encoding="utf-8") as f:
                data = json.load(f)
                metrics = Metrics(
                    total_queries=data.get("total_queries", 0),
                    cache_hits=data.get("cache_hits", 0),
                    cache_misses=data.get("cache_misses", 0),
                    api_calls=data.get("api_calls", 0),
                    execution_time_sum=data.get("execution_time_sum", 0.0),
                    execution_time_count=data.get("execution_time_count", 0),
                    errors=data.get("errors", 0),
                    commands_executed=data.get("commands_executed", 0),
                    commands_skipped=data.get("commands_skipped", 0),
                    last_updated=data.get("last_updated"),
                    provider_stats=data.get("provider_stats", {}),
                )
                return metrics
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to load metrics, starting fresh: {e}")
            return Metrics()

    def _save_metrics(self):
        """Save metrics to file."""
        try:
            self._metrics.last_updated = datetime.now().isoformat()
            temp_path = self.metrics_path.with_suffix(".json.tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._metrics.to_dict(), f, indent=2)
            temp_path.replace(self.metrics_path)
        except Exception as e:
            logger.warning(f"Failed to save metrics: {e}")

    def record_query(
        self,
        cached: bool,
        execution_time: float,
        provider: str | None = None,
        model: str | None = None,
    ):
        """Record a query execution."""
        self._metrics.total_queries += 1
        if cached:
            self._metrics.cache_hits += 1
        else:
            self._metrics.cache_misses += 1
            self._metrics.api_calls += 1

        # Track execution time
        self._metrics.execution_time_sum += execution_time
        self._metrics.execution_time_count += 1

        # Track provider stats
        if provider:
            if provider not in self._metrics.provider_stats:
                self._metrics.provider_stats[provider] = {
                    "queries": 0,
                    "api_calls": 0,
                    "total_time": 0.0,
                    "models": {},
                }
            self._metrics.provider_stats[provider]["queries"] += 1
            if not cached:
                self._metrics.provider_stats[provider]["api_calls"] += 1
            self._metrics.provider_stats[provider]["total_time"] += execution_time

            if model:
                if model not in self._metrics.provider_stats[provider]["models"]:
                    self._metrics.provider_stats[provider]["models"][model] = {
                        "queries": 0,
                        "api_calls": 0,
                    }
                self._metrics.provider_stats[provider]["models"][model]["queries"] += 1
                if not cached:
                    self._metrics.provider_stats[provider]["models"][model][
                        "api_calls"
                    ] += 1

        self._save_metrics()

    def record_error(self, provider: str | None = None):
        """Record an error."""
        self._metrics.errors += 1
        if provider and provider in self._metrics.provider_stats:
            if "errors" not in self._metrics.provider_stats[provider]:
                self._metrics.provider_stats[provider]["errors"] = 0
            self._metrics.provider_stats[provider]["errors"] += 1
        self._save_metrics()

    def record_command_execution(self, executed: bool):
        """Record command execution."""
        if executed:
            self._metrics.commands_executed += 1
        else:
            self._metrics.commands_skipped += 1
        self._save_metrics()

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        return self._metrics.to_dict()

    def reset(self):
        """Reset all metrics."""
        self._metrics = Metrics()
        self._save_metrics()
        logger.info("Metrics reset")

    def get_provider_comparison(self) -> list[dict[str, Any]]:
        """Get provider performance comparison."""
        comparison = []
        for provider, stats in self._metrics.provider_stats.items():
            query_count = stats.get("queries", 0)
            if query_count == 0:
                continue

            avg_time = (
                stats.get("total_time", 0.0) / query_count if query_count > 0 else 0.0
            )
            comparison.append(
                {
                    "provider": provider,
                    "queries": query_count,
                    "api_calls": stats.get("api_calls", 0),
                    "avg_time": avg_time,
                    "errors": stats.get("errors", 0),
                    "models": stats.get("models", {}),
                }
            )

        # Sort by query count (descending)
        comparison.sort(key=lambda x: x["queries"], reverse=True)
        return comparison

"""Command caching for CLI-NLP to reduce API calls."""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

from cli_nlp.exceptions import CacheError
from cli_nlp.logger import get_logger
from cli_nlp.models import CommandResponse, SafetyLevel

logger = get_logger(__name__)


class CacheEntry:
    """Represents a cached command response."""

    def __init__(
        self,
        command: str,
        is_safe: bool,
        safety_level: SafetyLevel,
        explanation: str | None,
        timestamp: datetime,
        ttl_seconds: int = 86400,  # Default 24 hours
    ):
        self.command = command
        self.is_safe = is_safe
        self.safety_level = safety_level
        self.explanation = explanation
        self.timestamp = timestamp
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        age = datetime.now() - self.timestamp
        return age.total_seconds() > self.ttl_seconds

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "command": self.command,
            "is_safe": self.is_safe,
            "safety_level": self.safety_level.value,
            "explanation": self.explanation,
            "timestamp": self.timestamp.isoformat(),
            "ttl_seconds": self.ttl_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        """Create from dictionary."""
        return cls(
            command=data["command"],
            is_safe=data["is_safe"],
            safety_level=SafetyLevel(data["safety_level"]),
            explanation=data.get("explanation"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            ttl_seconds=data.get("ttl_seconds", 86400),
        )

    def to_command_response(self) -> CommandResponse:
        """Convert to CommandResponse."""
        return CommandResponse(
            command=self.command,
            is_safe=self.is_safe,
            safety_level=self.safety_level,
            explanation=self.explanation,
        )


class CacheManager:
    """Manages command caching to reduce API calls."""

    def __init__(self, ttl_seconds: int = 86400, max_size: int = 1000):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.cache_path = self._get_cache_path()
        self._cache: dict[str, CacheEntry] = {}
        self._stats = {"hits": 0, "misses": 0}
        self._load_cache()

    @staticmethod
    def _get_cache_path() -> Path:
        """Get the path to the cache file."""
        # Use XDG cache directory if available
        xdg_cache = os.getenv("XDG_CACHE_HOME")
        if xdg_cache:
            cache_dir = Path(xdg_cache) / "cli-nlp"
        else:
            cache_dir = Path.home() / ".cache" / "cli-nlp"

        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "command_cache.json"

    def _query_hash(self, query: str, model: str | None = None) -> str:
        """Generate hash for query (and optionally model)."""
        key = f"{query}:{model or 'default'}"
        return hashlib.sha256(key.encode()).hexdigest()

    def _load_cache(self):
        """Load cache from file."""
        if not self.cache_path.exists():
            logger.debug(f"Cache file does not exist: {self.cache_path}")
            self._cache = {}
            return

        try:
            with open(self.cache_path, encoding="utf-8") as f:
                data = json.load(f)
                # Load entries and filter expired ones
                loaded_count = 0
                for key, entry_data in data.items():
                    try:
                        entry = CacheEntry.from_dict(entry_data)
                        if not entry.is_expired():
                            self._cache[key] = entry
                            loaded_count += 1
                    except (KeyError, ValueError) as e:
                        logger.warning(
                            f"Skipping invalid cache entry '{key}': {e}",
                            exc_info=True,
                        )
                        continue

                logger.debug(
                    f"Loaded {loaded_count} cache entries from {self.cache_path}"
                )
        except json.JSONDecodeError as e:
            logger.warning(
                f"Cache file corrupted, starting fresh: {e}",
                exc_info=True,
            )
            # Backup corrupted cache file
            backup_path = self.cache_path.with_suffix(".json.bak")
            try:
                self.cache_path.rename(backup_path)
                logger.debug(f"Backed up corrupted cache to {backup_path}")
            except Exception as backup_error:
                logger.warning(f"Could not backup corrupted cache: {backup_error}")
            self._cache = {}
        except (OSError, PermissionError) as e:
            raise CacheError(
                f"Failed to read cache file: {e}",
                cache_path=str(self.cache_path),
            ) from e

    def _save_cache(self):
        """Save cache to file."""
        try:
            # Only save non-expired entries
            valid_cache = {
                key: entry.to_dict()
                for key, entry in self._cache.items()
                if not entry.is_expired()
            }

            # Limit cache size
            if len(valid_cache) > self.max_size:
                # Remove oldest entries
                sorted_entries = sorted(
                    valid_cache.items(),
                    key=lambda x: x[1]["timestamp"],
                )
                removed_count = len(valid_cache) - self.max_size
                valid_cache = dict(sorted_entries[-self.max_size :])
                logger.debug(f"Cache size limit reached, removed {removed_count} oldest entries")

            # Ensure cache directory exists
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Write cache file atomically using a temporary file
            temp_path = self.cache_path.with_suffix(".json.tmp")
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(valid_cache, f, indent=2)
                temp_path.replace(self.cache_path)
                logger.debug(f"Saved {len(valid_cache)} cache entries to {self.cache_path}")
            except Exception as write_error:
                # Clean up temp file on error
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
                raise

        except (OSError, PermissionError) as e:
            logger.error(
                f"Failed to save cache file: {e}",
                exc_info=True,
            )
            raise CacheError(
                f"Failed to save cache file: {e}",
                cache_path=str(self.cache_path),
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected error saving cache: {e}",
                exc_info=True,
            )
            raise CacheError(
                f"Unexpected error saving cache: {e}",
                cache_path=str(self.cache_path),
            ) from e

    def get(
        self,
        query: str,
        model: str | None = None,
    ) -> CommandResponse | None:
        """Get cached command response if available and not expired."""
        cache_key = self._query_hash(query, model)
        entry = self._cache.get(cache_key)

        if entry is None:
            self._stats["misses"] += 1
            logger.debug(f"Cache miss for query: {query[:50]}...")
            return None

        if entry.is_expired():
            # Remove expired entry
            logger.debug(f"Cache entry expired for query: {query[:50]}...")
            del self._cache[cache_key]
            try:
                self._save_cache()
            except CacheError:
                # Log but don't fail on cache save errors during get
                logger.warning("Failed to save cache after removing expired entry")
            self._stats["misses"] += 1
            return None

        self._stats["hits"] += 1
        logger.debug(f"Cache hit for query: {query[:50]}...")
        return entry.to_command_response()

    def set(
        self,
        query: str,
        command_response: CommandResponse,
        model: str | None = None,
        ttl_seconds: int | None = None,
    ):
        """Cache a command response."""
        cache_key = self._query_hash(query, model)
        ttl = ttl_seconds or self.ttl_seconds

        entry = CacheEntry(
            command=command_response.command,
            is_safe=command_response.is_safe,
            safety_level=command_response.safety_level,
            explanation=command_response.explanation,
            timestamp=datetime.now(),
            ttl_seconds=ttl,
        )

        self._cache[cache_key] = entry
        logger.debug(f"Caching command for query: {query[:50]}...")

        # Limit cache size
        if len(self._cache) > self.max_size:
            # Remove oldest entries
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].timestamp,
            )
            removed_count = len(self._cache) - self.max_size
            self._cache = dict(sorted_entries[-self.max_size :])
            logger.debug(f"Cache size limit reached, removed {removed_count} oldest entries")

        self._save_cache()

    def clear(self):
        """Clear all cache entries."""
        logger.info("Clearing cache")
        self._cache = {}
        self._stats = {"hits": 0, "misses": 0}
        self._save_cache()

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total * 100 if total > 0 else 0.0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "total": total,
            "hit_rate": round(hit_rate, 2),
            "entries": len(self._cache),
        }

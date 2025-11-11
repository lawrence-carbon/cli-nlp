"""Command caching for CLI-NLP to reduce API calls."""

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from cli_nlp.models import CommandResponse, SafetyLevel


class CacheEntry:
    """Represents a cached command response."""
    
    def __init__(
        self,
        command: str,
        is_safe: bool,
        safety_level: SafetyLevel,
        explanation: Optional[str],
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
    
    def to_dict(self) -> Dict:
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
    def from_dict(cls, data: Dict) -> "CacheEntry":
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
        self._cache: Dict[str, CacheEntry] = {}
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
    
    def _query_hash(self, query: str, model: Optional[str] = None) -> str:
        """Generate hash for query (and optionally model)."""
        key = f"{query}:{model or 'default'}"
        return hashlib.sha256(key.encode()).hexdigest()
    
    def _load_cache(self):
        """Load cache from file."""
        if not self.cache_path.exists():
            self._cache = {}
            return
        
        try:
            with open(self.cache_path, 'r') as f:
                data = json.load(f)
                # Load entries and filter expired ones
                for key, entry_data in data.items():
                    entry = CacheEntry.from_dict(entry_data)
                    if not entry.is_expired():
                        self._cache[key] = entry
        except (json.JSONDecodeError, KeyError, ValueError):
            # If cache file is corrupted, start fresh
            self._cache = {}
    
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
                valid_cache = dict(sorted_entries[-self.max_size:])
            
            with open(self.cache_path, 'w') as f:
                json.dump(valid_cache, f, indent=2)
        except Exception:
            # Silently fail if we can't save cache
            pass
    
    def get(
        self,
        query: str,
        model: Optional[str] = None,
    ) -> Optional[CommandResponse]:
        """Get cached command response if available and not expired."""
        cache_key = self._query_hash(query, model)
        entry = self._cache.get(cache_key)
        
        if entry is None:
            self._stats["misses"] += 1
            return None
        
        if entry.is_expired():
            # Remove expired entry
            del self._cache[cache_key]
            self._save_cache()
            self._stats["misses"] += 1
            return None
        
        self._stats["hits"] += 1
        return entry.to_command_response()
    
    def set(
        self,
        query: str,
        command_response: CommandResponse,
        model: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
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
        
        # Limit cache size
        if len(self._cache) > self.max_size:
            # Remove oldest entries
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].timestamp,
            )
            self._cache = dict(sorted_entries[-self.max_size:])
        
        self._save_cache()
    
    def clear(self):
        """Clear all cache entries."""
        self._cache = {}
        self._save_cache()
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (
            self._stats["hits"] / total * 100
            if total > 0
            else 0.0
        )
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "total": total,
            "hit_rate": round(hit_rate, 2),
            "entries": len(self._cache),
        }


"""History management for CLI-NLP commands and queries."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from cli_nlp.models import SafetyLevel


class HistoryEntry:
    """Represents a single history entry."""
    
    def __init__(
        self,
        query: str,
        command: str,
        is_safe: bool,
        safety_level: SafetyLevel,
        timestamp: Optional[datetime] = None,
        explanation: Optional[str] = None,
        executed: bool = False,
        return_code: Optional[int] = None,
    ):
        self.query = query
        self.command = command
        self.is_safe = is_safe
        self.safety_level = safety_level
        self.timestamp = timestamp or datetime.now()
        self.explanation = explanation
        self.executed = executed
        self.return_code = return_code
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "query": self.query,
            "command": self.command,
            "is_safe": self.is_safe,
            "safety_level": self.safety_level.value,
            "timestamp": self.timestamp.isoformat(),
            "explanation": self.explanation,
            "executed": self.executed,
            "return_code": self.return_code,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "HistoryEntry":
        """Create from dictionary."""
        return cls(
            query=data["query"],
            command=data["command"],
            is_safe=data["is_safe"],
            safety_level=SafetyLevel(data["safety_level"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            explanation=data.get("explanation"),
            executed=data.get("executed", False),
            return_code=data.get("return_code"),
        )


class HistoryManager:
    """Manages command history storage and retrieval."""
    
    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self.history_path = self._get_history_path()
        self._history: List[HistoryEntry] = []
        self._load_history()
    
    @staticmethod
    def _get_history_path() -> Path:
        """Get the path to the history file."""
        # Use XDG data directory if available
        xdg_data = os.getenv("XDG_DATA_HOME")
        if xdg_data:
            data_dir = Path(xdg_data) / "cli-nlp"
        else:
            data_dir = Path.home() / ".local" / "share" / "cli-nlp"
        
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "history.json"
    
    def _load_history(self):
        """Load history from file."""
        if not self.history_path.exists():
            self._history = []
            return
        
        try:
            with open(self.history_path, 'r') as f:
                data = json.load(f)
                self._history = [
                    HistoryEntry.from_dict(entry) for entry in data
                ]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If history file is corrupted, start fresh
            self._history = []
    
    def _save_history(self):
        """Save history to file."""
        try:
            with open(self.history_path, 'w') as f:
                json.dump(
                    [entry.to_dict() for entry in self._history],
                    f,
                    indent=2
                )
        except Exception:
            # Silently fail if we can't save history
            pass
    
    def add_entry(
        self,
        query: str,
        command: str,
        is_safe: bool,
        safety_level: SafetyLevel,
        explanation: Optional[str] = None,
        executed: bool = False,
        return_code: Optional[int] = None,
    ) -> HistoryEntry:
        """Add a new entry to history."""
        entry = HistoryEntry(
            query=query,
            command=command,
            is_safe=is_safe,
            safety_level=safety_level,
            explanation=explanation,
            executed=executed,
            return_code=return_code,
        )
        
        self._history.append(entry)
        
        # Keep only the most recent entries
        if len(self._history) > self.max_entries:
            self._history = self._history[-self.max_entries:]
        
        self._save_history()
        return entry
    
    def get_all(self, limit: Optional[int] = None) -> List[HistoryEntry]:
        """Get all history entries, optionally limited."""
        entries = self._history
        if limit:
            entries = entries[-limit:]
        return list(reversed(entries))  # Most recent first
    
    def search(self, query: str) -> List[HistoryEntry]:
        """Search history by query or command."""
        query_lower = query.lower()
        results = []
        for entry in self._history:
            if (
                query_lower in entry.query.lower() or
                query_lower in entry.command.lower()
            ):
                results.append(entry)
        return list(reversed(results))  # Most recent first
    
    def get_by_id(self, entry_id: int) -> Optional[HistoryEntry]:
        """Get entry by index (0-based, most recent first)."""
        if entry_id < 0 or entry_id >= len(self._history):
            return None
        # Convert to reverse index
        reverse_index = len(self._history) - 1 - entry_id
        return self._history[reverse_index]
    
    def clear(self):
        """Clear all history."""
        self._history = []
        self._save_history()
    
    def export(self, format: str = "json") -> str:
        """Export history in specified format."""
        if format == "json":
            return json.dumps(
                [entry.to_dict() for entry in self._history],
                indent=2
            )
        elif format == "csv":
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "timestamp", "query", "command", "is_safe", "safety_level",
                "executed", "return_code", "explanation"
            ])
            for entry in self._history:
                writer.writerow([
                    entry.timestamp.isoformat(),
                    entry.query,
                    entry.command,
                    entry.is_safe,
                    entry.safety_level.value,
                    entry.executed,
                    entry.return_code or "",
                    entry.explanation or "",
                ])
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")


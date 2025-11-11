"""Configuration management for CLI-NLP."""

import json
import os
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console

from cli_nlp.utils import console


class ConfigManager:
    """Manages configuration file operations."""
    
    DEFAULT_CONFIG = {
        "openai_api_key": "",
        "default_model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 200
    }
    
    def __init__(self):
        self.config_path = self._get_config_path()
    
    @staticmethod
    def _get_config_path() -> Path:
        """Get the path to the config file."""
        # Try XDG config directory first, then fallback to ~/.config
        xdg_config = os.getenv("XDG_CONFIG_HOME")
        if xdg_config:
            config_dir = Path(xdg_config) / "cli-nlp"
        else:
            config_dir = Path.home() / ".config" / "cli-nlp"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.json"
    
    def load(self) -> Dict:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            return {}
        
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            console.print(f"[red]Error: Invalid JSON in config file: {e}[/red]")
            console.print(f"Config file location: {self.config_path}")
            raise
        except Exception as e:
            console.print(f"[red]Error reading config file: {e}[/red]")
            raise
    
    def create_default(self) -> bool:
        """Create a default config file with template."""
        if self.config_path.exists():
            console.print(f"[yellow]Config file already exists at: {self.config_path}[/yellow]")
            return False
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.DEFAULT_CONFIG, f, indent=2)
            
            # Set restrictive permissions (read/write for user only)
            os.chmod(self.config_path, 0o600)
            
            console.print(f"[green]Created config file at: {self.config_path}[/green]")
            console.print("[yellow]Please edit it and add your OpenAI API key.[/yellow]")
            return True
        except Exception as e:
            console.print(f"[red]Error creating config file: {e}[/red]")
            return False
    
    def get_api_key(self) -> Optional[str]:
        """Get OpenAI API key from config or environment."""
        config = self.load()
        return config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    
    def get(self, key: str, default=None):
        """Get a config value."""
        config = self.load()
        return config.get(key, default)


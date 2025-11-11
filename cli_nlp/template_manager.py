"""Template/alias management for CLI-NLP."""

import json
import os
from pathlib import Path
from typing import Dict, Optional


class TemplateManager:
    """Manages command templates/aliases."""
    
    def __init__(self):
        self.templates_path = self._get_templates_path()
        self._templates: Dict[str, Dict] = {}
        self._load_templates()
    
    @staticmethod
    def _get_templates_path() -> Path:
        """Get the path to the templates file."""
        # Use XDG config directory if available
        xdg_config = os.getenv("XDG_CONFIG_HOME")
        if xdg_config:
            config_dir = Path(xdg_config) / "cli-nlp"
        else:
            config_dir = Path.home() / ".config" / "cli-nlp"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "templates.json"
    
    def _load_templates(self):
        """Load templates from file."""
        if not self.templates_path.exists():
            self._templates = {}
            return
        
        try:
            with open(self.templates_path, 'r') as f:
                self._templates = json.load(f)
        except (json.JSONDecodeError, Exception):
            # If templates file is corrupted, start fresh
            self._templates = {}
    
    def _save_templates(self):
        """Save templates to file."""
        try:
            with open(self.templates_path, 'w') as f:
                json.dump(self._templates, f, indent=2)
        except Exception:
            # Silently fail if we can't save templates
            pass
    
    def save_template(self, name: str, command: str, description: Optional[str] = None) -> bool:
        """
        Save a command template.
        
        Args:
            name: Template name/alias
            command: The command to save
            description: Optional description
        
        Returns:
            True if saved successfully
        """
        if not name or not command:
            return False
        
        self._templates[name] = {
            "command": command,
            "description": description or "",
        }
        self._save_templates()
        return True
    
    def get_template(self, name: str) -> Optional[str]:
        """Get a template command by name."""
        template = self._templates.get(name)
        if template:
            return template.get("command")
        return None
    
    def list_templates(self) -> Dict[str, Dict]:
        """List all templates."""
        return self._templates.copy()
    
    def delete_template(self, name: str) -> bool:
        """Delete a template."""
        if name in self._templates:
            del self._templates[name]
            self._save_templates()
            return True
        return False
    
    def template_exists(self, name: str) -> bool:
        """Check if a template exists."""
        return name in self._templates


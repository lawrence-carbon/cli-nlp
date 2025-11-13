"""Configuration management for CLI-NLP."""

import json
import os
from pathlib import Path

from cli_nlp.utils import console


class ConfigManager:
    """Manages configuration file operations."""

    DEFAULT_CONFIG = {
        "providers": {},
        "active_provider": None,
        "active_model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 200,
    }

    def __init__(self):
        self.config_path = self._get_config_path()
        self._migrated = False

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

    def _migrate_old_config(self, config: dict) -> dict:
        """Migrate old config format to new multi-provider format."""
        if self._migrated:
            return config

        # Check if this is an old config format
        if "openai_api_key" in config and "providers" not in config:
            console.print(
                "[yellow]Migrating config to new multi-provider format...[/yellow]"
            )

            # Create new structure
            new_config = {
                "providers": {},
                "active_provider": None,
                "active_model": config.get("default_model", "gpt-4o-mini"),
                "temperature": config.get("temperature", 0.3),
                "max_tokens": config.get("max_tokens", 200),
            }

            # Migrate OpenAI config if present
            openai_key = config.get("openai_api_key")
            if openai_key:
                new_config["providers"]["openai"] = {
                    "api_key": openai_key,
                    "models": [config.get("default_model", "gpt-4o-mini")],
                }
                new_config["active_provider"] = "openai"

            # Save migrated config
            try:
                self.save(new_config)
                console.print("[green]Config migration completed.[/green]")
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not save migrated config: {e}[/yellow]"
                )

            self._migrated = True
            return new_config

        self._migrated = True
        return config

    def load(self) -> dict:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path) as f:
                config = json.load(f)

            # Migrate old config format if needed
            config = self._migrate_old_config(config)

            # Ensure new structure has required fields
            if "providers" not in config:
                config["providers"] = {}
            if "active_provider" not in config:
                config["active_provider"] = None
            if "active_model" not in config:
                config["active_model"] = config.get("default_model", "gpt-4o-mini")

            return config
        except json.JSONDecodeError as e:
            console.print(f"[red]Error: Invalid JSON in config file: {e}[/red]")
            console.print(f"Config file location: {self.config_path}")
            raise
        except Exception as e:
            console.print(f"[red]Error reading config file: {e}[/red]")
            raise

    def save(self, config: dict | None = None) -> bool:
        """Save configuration to JSON file."""
        if config is None:
            config = self.load()

        try:
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)

            # Set restrictive permissions (read/write for user only)
            os.chmod(self.config_path, 0o600)
            return True
        except Exception as e:
            console.print(f"[red]Error saving config file: {e}[/red]")
            return False

    def create_default(self) -> bool:
        """Create a default config file with template."""
        if self.config_path.exists():
            console.print(
                f"[yellow]Config file already exists at: {self.config_path}[/yellow]"
            )
            return False

        try:
            with open(self.config_path, "w") as f:
                json.dump(self.DEFAULT_CONFIG, f, indent=2)

            # Set restrictive permissions (read/write for user only)
            os.chmod(self.config_path, 0o600)

            console.print(f"[green]Created config file at: {self.config_path}[/green]")
            console.print(
                "[yellow]Run 'qtc config providers set' to configure a provider.[/yellow]"
            )
            return True
        except Exception as e:
            console.print(f"[red]Error creating config file: {e}[/red]")
            return False

    def get_api_key(self) -> str | None:
        """Get API key for active provider from config or environment."""
        config = self.load()
        active_provider = config.get("active_provider")

        if active_provider:
            provider_config = config.get("providers", {}).get(active_provider, {})
            api_key = provider_config.get("api_key")
            if api_key:
                return api_key

        # Fallback to environment variables
        # Check provider-specific env vars
        if active_provider:
            env_var_map = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "cohere": "COHERE_API_KEY",
                "google": "GOOGLE_API_KEY",
                "mistral": "MISTRAL_API_KEY",
                "azure": "AZURE_API_KEY",
            }
            env_var = env_var_map.get(active_provider.lower())
            if env_var:
                return os.getenv(env_var)

        # Legacy fallback for OpenAI
        return os.getenv("OPENAI_API_KEY")

    def get_active_provider(self) -> str | None:
        """Get the active provider name."""
        config = self.load()
        return config.get("active_provider")

    def get_active_model(self) -> str:
        """Get the active model string."""
        config = self.load()
        return config.get("active_model", "gpt-4o-mini")

    def get_provider_config(self, provider_name: str) -> dict | None:
        """Get configuration for a specific provider."""
        config = self.load()
        return config.get("providers", {}).get(provider_name)

    def set_active_provider(self, provider_name: str) -> bool:
        """Set the active provider."""
        config = self.load()

        if provider_name not in config.get("providers", {}):
            console.print(
                f"[red]Error: Provider '{provider_name}' is not configured.[/red]"
            )
            return False

        config["active_provider"] = provider_name
        return self.save(config)

    def add_provider(
        self, provider_name: str, api_key: str, models: list | None = None
    ) -> bool:
        """Add or update a provider configuration."""
        config = self.load()

        if "providers" not in config:
            config["providers"] = {}

        config["providers"][provider_name] = {
            "api_key": api_key,
            "models": models or [],
        }

        return self.save(config)

    def remove_provider(self, provider_name: str) -> bool:
        """Remove a provider configuration."""
        config = self.load()

        if provider_name not in config.get("providers", {}):
            console.print(
                f"[red]Error: Provider '{provider_name}' is not configured.[/red]"
            )
            return False

        # If removing active provider, clear active_provider
        if config.get("active_provider") == provider_name:
            config["active_provider"] = None

        del config["providers"][provider_name]
        return self.save(config)

    def get(self, key: str, default=None):
        """Get a config value."""
        config = self.load()
        return config.get(key, default)

"""Tests for config manager error paths and edge cases."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cli_nlp.config_manager import ConfigManager
from cli_nlp.exceptions import ConfigurationError


class TestConfigManagerErrorPaths:
    """Test error paths in ConfigManager."""

    def test_load_config_permission_error(self, temp_dir):
        """Test loading config with permission error."""
        config_file = temp_dir / "config.json"
        config_file.write_text('{"providers": {}}')

        manager = ConfigManager()
        manager.config_path = config_file

        # Make file unreadable
        config_file.chmod(0o000)
        try:
            with pytest.raises(ConfigurationError, match="Failed to read config file|Error reading config file"):
                manager.load()
        finally:
            # Restore permissions for cleanup
            config_file.chmod(0o644)

    def test_load_config_invalid_json(self, temp_dir):
        """Test loading config with invalid JSON."""
        config_file = temp_dir / "config.json"
        config_file.write_text("invalid json{")

        manager = ConfigManager()
        manager.config_path = config_file

        with pytest.raises(ConfigurationError, match="Invalid JSON"):
            manager.load()

    def test_save_config_validation_error(self, mock_config_manager):
        """Test saving config with validation error."""
        invalid_config = {
            "providers": "not-a-dict",  # Invalid structure
        }

        with pytest.raises(ConfigurationError, match="Invalid configuration"):
            mock_config_manager.save(invalid_config)

    def test_save_config_permission_error(self, temp_dir):
        """Test saving config with permission error."""
        config_file = temp_dir / "config.json"
        config_file.write_text('{"providers": {}}')

        manager = ConfigManager()
        manager.config_path = config_file

        config = {
            "providers": {
                "openai": {
                    "api_key": "sk-test",
                    "models": ["gpt-4o-mini"],
                }
            },
            "active_provider": "openai",
        }

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(ConfigurationError, match="Failed to save config file"):
                manager.save(config)

    def test_save_config_directory_creation_error(self, temp_dir):
        """Test saving config when directory creation fails."""
        config_file = temp_dir / "nonexistent" / "config.json"

        manager = ConfigManager()
        manager.config_path = config_file

        config = {
            "providers": {
                "openai": {
                    "api_key": "sk-test",
                    "models": ["gpt-4o-mini"],
                }
            },
            "active_provider": "openai",
        }

        with patch("pathlib.Path.mkdir", side_effect=OSError("Cannot create directory")):
            with pytest.raises(ConfigurationError):
                manager.save(config)

    def test_migrate_old_config_save_failure(self, temp_dir):
        """Test migration when save fails."""
        config_file = temp_dir / "config.json"
        old_config = {
            "openai_api_key": "sk-old-key",
            "default_model": "gpt-4o-mini",
        }
        config_file.write_text(json.dumps(old_config))

        manager = ConfigManager()
        manager.config_path = config_file

        with patch.object(manager, "save", return_value=False):
            # Should still return migrated config even if save fails
            config = manager.load()
            assert "providers" in config
            assert "openai" in config["providers"]

    def test_get_active_provider_none(self, temp_dir):
        """Test getting active provider when none is set."""
        config_file = temp_dir / "config.json"
        config_file.write_text('{"providers": {}, "active_provider": null}')

        manager = ConfigManager()
        manager.config_path = config_file

        assert manager.get_active_provider() is None

    def test_get_active_model_default(self, temp_dir):
        """Test getting active model with default."""
        config_file = temp_dir / "config.json"
        config_file.write_text('{"providers": {}}')

        manager = ConfigManager()
        manager.config_path = config_file

        assert manager.get_active_model() == "gpt-4o-mini"

    def test_set_active_provider_nonexistent(self, mock_config_manager):
        """Test setting active provider that doesn't exist."""
        assert mock_config_manager.set_active_provider("nonexistent") is False

    def test_remove_provider_nonexistent(self, mock_config_manager):
        """Test removing provider that doesn't exist."""
        assert mock_config_manager.remove_provider("nonexistent") is False

    def test_add_provider_updates_existing(self, mock_config_manager):
        """Test adding provider updates existing."""
        mock_config_manager.add_provider("openai", "sk-key1", ["model1"])
        mock_config_manager.add_provider("openai", "sk-key2", ["model2"])

        config = mock_config_manager.load()
        assert config["providers"]["openai"]["api_key"] == "sk-key2"
        assert config["providers"]["openai"]["models"] == ["model2"]

    def test_get_config_value_with_default(self, mock_config_manager):
        """Test getting config value with default."""
        value = mock_config_manager.get("nonexistent_key", "default_value")
        assert value == "default_value"

    def test_get_config_value_none(self, mock_config_manager):
        """Test getting config value that doesn't exist."""
        value = mock_config_manager.get("nonexistent_key")
        assert value is None

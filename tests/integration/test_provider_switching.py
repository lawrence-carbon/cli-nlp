"""Integration tests for provider switching."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cli_nlp.config_manager import ConfigManager
from cli_nlp.exceptions import ConfigurationError


class TestProviderSwitching:
    """Test provider switching functionality."""

    def test_switch_active_provider(self, mock_config_manager):
        """Test switching active provider."""
        # Add multiple providers
        mock_config_manager.add_provider("openai", "sk-openai-key", ["gpt-4o-mini"])
        mock_config_manager.add_provider("anthropic", "sk-anthropic-key", ["claude-3-opus"])

        # Set active provider
        assert mock_config_manager.set_active_provider("openai") is True
        assert mock_config_manager.get_active_provider() == "openai"

        # Switch to another provider
        assert mock_config_manager.set_active_provider("anthropic") is True
        assert mock_config_manager.get_active_provider() == "anthropic"

    def test_switch_to_nonexistent_provider(self, mock_config_manager):
        """Test switching to nonexistent provider."""
        assert mock_config_manager.set_active_provider("nonexistent") is False

    def test_get_api_key_for_active_provider(self, mock_config_manager):
        """Test getting API key for active provider."""
        mock_config_manager.add_provider("openai", "sk-test-key", ["gpt-4o-mini"])
        mock_config_manager.set_active_provider("openai")

        api_key = mock_config_manager.get_api_key()
        assert api_key == "sk-test-key"

    def test_remove_active_provider(self, mock_config_manager):
        """Test removing active provider clears active_provider."""
        mock_config_manager.add_provider("openai", "sk-test-key", ["gpt-4o-mini"])
        mock_config_manager.set_active_provider("openai")

        assert mock_config_manager.get_active_provider() == "openai"

        # Remove provider
        assert mock_config_manager.remove_provider("openai") is True
        assert mock_config_manager.get_active_provider() is None

"""Unit tests for ProviderManager."""

import json
from unittest.mock import patch

import pytest

from cli_nlp.provider_manager import (
    ProviderDiscoveryError,
    format_model_name,
    get_available_providers,
    get_model_provider,
    get_provider_models,
    refresh_provider_cache,
    search_models,
    search_providers,
)


class TestProviderManager:
    """Test suite for ProviderManager."""

    def test_get_available_providers(self, monkeypatch):
        """Test getting available providers."""
        mock_providers = {
            "openai": ["gpt-4o-mini", "gpt-4o"],
            "anthropic": ["claude-3-opus", "claude-3-sonnet"],
        }

        with patch(
            "cli_nlp.provider_manager._get_provider_models_dict",
            return_value=mock_providers,
        ):
            providers = get_available_providers()
            assert "openai" in providers
            assert "anthropic" in providers
            assert len(providers) == 2

    def test_get_available_providers_error(self, monkeypatch):
        """Test getting available providers when discovery fails."""
        with patch(
            "cli_nlp.provider_manager._get_provider_models_dict",
            side_effect=ProviderDiscoveryError("Test error"),
        ):
            with pytest.raises(ProviderDiscoveryError):
                get_available_providers()

    def test_get_provider_models(self, monkeypatch):
        """Test getting models for a provider."""
        mock_providers = {
            "openai": ["gpt-4o-mini", "gpt-4o"],
            "anthropic": ["claude-3-opus"],
        }

        with patch(
            "cli_nlp.provider_manager._get_provider_models_dict",
            return_value=mock_providers,
        ):
            models = get_provider_models("openai")
            assert "gpt-4o-mini" in models
            assert "gpt-4o" in models
            assert len(models) == 2

    def test_get_provider_models_error(self, monkeypatch):
        """Test getting provider models when discovery fails."""
        with patch(
            "cli_nlp.provider_manager._get_provider_models_dict",
            side_effect=ProviderDiscoveryError("Test error"),
        ):
            with pytest.raises(ProviderDiscoveryError):
                get_provider_models("openai")

    def test_get_provider_models_nonexistent(self, monkeypatch):
        """Test getting models for non-existent provider."""
        mock_providers = {
            "openai": ["gpt-4o-mini"],
        }

        with patch(
            "cli_nlp.provider_manager._get_provider_models_dict",
            return_value=mock_providers,
        ):
            models = get_provider_models("nonexistent")
            assert models == []

    def test_format_model_name(self):
        """Test formatting model name."""
        # OpenAI, Anthropic, Google, Cohere don't need prefix
        assert format_model_name("openai", "gpt-4o-mini") == "gpt-4o-mini"
        assert format_model_name("anthropic", "claude-3-opus") == "claude-3-opus"
        # Azure, Bedrock, Ollama need prefix
        assert format_model_name("azure", "gpt-4o-mini") == "azure/gpt-4o-mini"
        assert (
            format_model_name("bedrock", "claude-3-opus") == "bedrock/claude-3-opus"
        )
        assert format_model_name("ollama", "llama2") == "ollama/llama2"
        # Already formatted
        assert (
            format_model_name("azure", "azure/gpt-4o-mini") == "azure/gpt-4o-mini"
        )

    def test_get_model_provider(self, monkeypatch):
        """Test getting provider from model name."""
        mock_providers = {
            "openai": ["gpt-4o-mini", "gpt-4o"],
            "anthropic": ["claude-3-opus"],
        }

        with patch(
            "cli_nlp.provider_manager._get_provider_models_dict",
            return_value=mock_providers,
        ):
            # Formatted model name
            provider = get_model_provider("openai/gpt-4o-mini")
            assert provider == "openai"

            # Unformatted model name
            provider = get_model_provider("gpt-4o-mini")
            assert provider == "openai"

    def test_get_model_provider_default_openai(self):
        """Test getting provider defaults to OpenAI for GPT models."""
        with patch(
            "cli_nlp.provider_manager._get_provider_models_dict", return_value={}
        ):
            provider = get_model_provider("gpt-4")
            assert provider == "openai"

    def test_search_providers(self, monkeypatch):
        """Test searching providers."""
        # Mock _get_provider_models_dict to avoid calling LiteLLM
        mock_providers_dict = {
            "openai": ["gpt-4o-mini"],
            "anthropic": ["claude-3-opus"],
            "cohere": ["command"],
        }
        with patch(
            "cli_nlp.provider_manager._get_provider_models_dict",
            return_value=mock_providers_dict,
        ):
            # Exact match
            matches = search_providers("openai")
            assert "openai" in matches

            # Partial match
            matches = search_providers("anth")
            assert "anthropic" in matches

            # Case insensitive
            matches = search_providers("OPENAI")
            assert "openai" in matches

            # No match - use a query that won't fuzzy match
            # Note: fuzzy matching matches first char, so "nonexistent" might match providers containing 'n'
            matches = search_providers("zzzzzzz")
            assert matches == []

    def test_search_models(self, monkeypatch):
        """Test searching models."""
        # Mock _get_provider_models_dict to avoid calling LiteLLM
        mock_providers_dict = {
            "openai": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        }
        with patch(
            "cli_nlp.provider_manager._get_provider_models_dict",
            return_value=mock_providers_dict,
        ):
            # Exact match
            matches = search_models("openai", "gpt-4o-mini")
            assert "gpt-4o-mini" in matches

            # Partial match
            matches = search_models("openai", "gpt-4")
            assert "gpt-4o-mini" in matches
            assert "gpt-4o" in matches

            # Case insensitive
            matches = search_models("openai", "GPT-4O")
            assert "gpt-4o" in matches

            # No match - use a query that won't fuzzy match
            # Note: fuzzy matching matches first char, so "nonexistent" might match "gpt-4o-mini" (contains 'n')
            matches = search_models("openai", "zzzzzzz")
            assert matches == []

    def test_refresh_provider_cache(self, temp_dir, monkeypatch):
        """Test refreshing provider cache."""
        cache_file = temp_dir / "provider_cache.json"

        # Create initial cache
        initial_cache = {
            "openai": ["gpt-4o-mini"],
        }
        cache_file.write_text(json.dumps(initial_cache))

        with (
            patch("cli_nlp.provider_manager._get_cache_path", return_value=cache_file),
            patch(
                "cli_nlp.provider_manager._fetch_from_litellm",
                return_value={"openai": ["gpt-4o", "gpt-4o-mini"]},
            ),
        ):

            refresh_provider_cache()

            # Cache should be updated
            updated_cache = json.loads(cache_file.read_text())
            assert "gpt-4o" in updated_cache["openai"]

    def test_provider_discovery_error(self):
        """Test ProviderDiscoveryError exception."""
        error = ProviderDiscoveryError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

"""Tests for command runner error paths and edge cases."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cli_nlp.command_runner import CommandRunner
from cli_nlp.exceptions import APIError, ValidationError
from cli_nlp.models import CommandResponse, SafetyLevel


class TestCommandRunnerErrorPaths:
    """Test error paths in CommandRunner."""

    def test_generate_command_empty_response(self, mock_config_manager, mock_cache_manager):
        """Test command generation with empty API response."""
        from cli_nlp.context_manager import ContextManager
        from cli_nlp.history_manager import HistoryManager

        runner = CommandRunner(
            mock_config_manager,
            HistoryManager(),
            mock_cache_manager,
            ContextManager(),
        )

        with patch("litellm.completion") as mock_completion:
            mock_response = MagicMock()
            mock_response.choices = []  # Empty choices

            mock_completion.return_value = mock_response

            with pytest.raises(APIError, match="Empty response from API"):
                runner.generate_command("list files")

    def test_generate_command_no_content(self, mock_config_manager, mock_cache_manager):
        """Test command generation with response but no content."""
        from cli_nlp.context_manager import ContextManager
        from cli_nlp.history_manager import HistoryManager

        runner = CommandRunner(
            mock_config_manager,
            HistoryManager(),
            mock_cache_manager,
            ContextManager(),
        )

        with patch("litellm.completion") as mock_completion:
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_message = MagicMock()
            mock_message.content = None  # No content
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]

            mock_completion.return_value = mock_response

            with pytest.raises(APIError, match="Empty response from API"):
                runner.generate_command("list files")

    def test_generate_command_invalid_json(self, mock_config_manager, mock_cache_manager):
        """Test command generation with invalid JSON response."""
        from cli_nlp.context_manager import ContextManager
        from cli_nlp.history_manager import HistoryManager

        runner = CommandRunner(
            mock_config_manager,
            HistoryManager(),
            mock_cache_manager,
            ContextManager(),
        )

        with patch("litellm.completion") as mock_completion:
            mock_response = MagicMock()
            mock_message = MagicMock()
            mock_message.content = "not valid json"
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]

            mock_completion.return_value = mock_response

            with pytest.raises(APIError, match="Invalid JSON response"):
                runner.generate_command("list files")

    def test_generate_command_cache_error_handled(self, mock_config_manager, temp_dir):
        """Test that cache errors are handled gracefully."""
        from cli_nlp.cache_manager import CacheManager
        from cli_nlp.context_manager import ContextManager
        from cli_nlp.history_manager import HistoryManager

        cache_manager = CacheManager(ttl_seconds=86400)
        cache_manager.cache_path = temp_dir / "cache.json"

        runner = CommandRunner(
            mock_config_manager,
            HistoryManager(),
            cache_manager,
            ContextManager(),
        )

        with patch("litellm.completion") as mock_completion:
            mock_response = MagicMock()
            mock_message = MagicMock()
            mock_message.content = json.dumps({
                "command": "ls -la",
                "is_safe": True,
                "safety_level": "safe",
                "explanation": "List files",
            })
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]

            mock_completion.return_value = mock_response

            # Mock cache.get to raise error
            with patch.object(cache_manager, "get", side_effect=Exception("Cache error")):
                # Should continue without cache
                response = runner.generate_command("list files")
                assert response.command == "ls -la"

    def test_generate_command_context_error_handled(self, mock_config_manager, mock_cache_manager):
        """Test that context building errors are handled gracefully."""
        from cli_nlp.context_manager import ContextManager
        from cli_nlp.history_manager import HistoryManager

        context_manager = ContextManager()

        runner = CommandRunner(
            mock_config_manager,
            HistoryManager(),
            mock_cache_manager,
            context_manager,
        )

        with patch("litellm.completion") as mock_completion:
            mock_response = MagicMock()
            mock_message = MagicMock()
            mock_message.content = json.dumps({
                "command": "ls -la",
                "is_safe": True,
                "safety_level": "safe",
                "explanation": "List files",
            })
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]

            mock_completion.return_value = mock_response

            # Mock context building to raise error
            with patch.object(
                context_manager, "build_context_string", side_effect=Exception("Context error")
            ):
                # Should continue with query only
                response = runner.generate_command("list files")
                assert response.command == "ls -la"

    def test_generate_command_cache_save_error_handled(self, mock_config_manager, mock_cache_manager):
        """Test that cache save errors are handled gracefully."""
        from cli_nlp.context_manager import ContextManager
        from cli_nlp.history_manager import HistoryManager

        runner = CommandRunner(
            mock_config_manager,
            HistoryManager(),
            mock_cache_manager,
            ContextManager(),
        )

        with patch("litellm.completion") as mock_completion:
            mock_response = MagicMock()
            mock_message = MagicMock()
            mock_message.content = json.dumps({
                "command": "ls -la",
                "is_safe": True,
                "safety_level": "safe",
                "explanation": "List files",
            })
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]

            mock_completion.return_value = mock_response

            # Mock cache.set to raise error
            with patch.object(mock_cache_manager, "set", side_effect=Exception("Cache save error")):
                # Should still return response
                response = runner.generate_command("list files")
                assert response.command == "ls -la"

    def test_generate_command_validation_error(self, mock_config_manager, mock_cache_manager):
        """Test command generation with validation error."""
        from cli_nlp.context_manager import ContextManager
        from cli_nlp.history_manager import HistoryManager

        runner = CommandRunner(
            mock_config_manager,
            HistoryManager(),
            mock_cache_manager,
            ContextManager(),
        )

        # Empty query should raise ValidationError
        with pytest.raises(ValidationError):
            runner.generate_command("")

        # Query too long should raise ValidationError
        long_query = "x" * 10001
        with pytest.raises(ValidationError):
            runner.generate_command(long_query)

    def test_generate_command_api_key_setup_error(self, temp_dir, monkeypatch):
        """Test command generation when API key setup fails."""
        from cli_nlp.cache_manager import CacheManager
        from cli_nlp.config_manager import ConfigManager
        from cli_nlp.context_manager import ContextManager
        from cli_nlp.history_manager import HistoryManager

        config_file = temp_dir / "config.json"
        config_file.write_text('{"providers": {}, "active_provider": null}')

        config_manager = ConfigManager()
        config_manager.config_path = config_file

        # Remove any environment API keys
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        runner = CommandRunner(
            config_manager,
            HistoryManager(),
            CacheManager(),
            ContextManager(),
        )

        # Should raise APIError or SystemExit depending on implementation
        with pytest.raises((APIError, SystemExit)):
            runner.generate_command("list files")

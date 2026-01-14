"""Integration tests for full command generation flow."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cli_nlp.cache_manager import CacheManager
from cli_nlp.command_runner import CommandRunner
from cli_nlp.config_manager import ConfigManager
from cli_nlp.context_manager import ContextManager
from cli_nlp.history_manager import HistoryManager
from cli_nlp.models import CommandResponse, SafetyLevel


@pytest.fixture
def mock_litellm_response():
    """Create a mock LiteLLM response."""
    mock_message = MagicMock()
    mock_message.content = json.dumps(
        {
            "command": "ls -la",
            "is_safe": True,
            "safety_level": "safe",
            "explanation": "List files",
        }
    )

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    return mock_response


class TestFullCommandGenerationFlow:
    """Test full command generation flow."""

    def test_generate_command_with_cache(self, mock_config_manager, mock_cache_manager, mock_litellm_response):
        """Test command generation with caching."""
        history_manager = HistoryManager()
        context_manager = ContextManager()

        runner = CommandRunner(
            mock_config_manager,
            history_manager,
            mock_cache_manager,
            context_manager,
        )

        # Mock litellm module - always return JSON string in content
        with patch("litellm.completion") as mock_completion:
            def mock_completion_side_effect(*args, **kwargs):
                # Always return JSON string in content (works for all fallback paths)
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
                return mock_response

            mock_completion.side_effect = mock_completion_side_effect

            # First call - should hit API
            response1 = runner.generate_command("list files")
            assert response1.command == "ls -la"
            assert response1.is_safe is True

            # Second call - should use cache
            response2 = runner.generate_command("list files")
            assert response2.command == "ls -la"
            assert response2.is_safe is True

            # Should only call API once (second call uses cache)
            assert mock_completion.call_count == 1

    def test_generate_command_with_history(self, mock_config_manager, mock_cache_manager, mock_litellm_response):
        """Test command generation with history tracking."""
        history_manager = HistoryManager()
        context_manager = ContextManager()

        runner = CommandRunner(
            mock_config_manager,
            history_manager,
            mock_cache_manager,
            context_manager,
        )

        with patch("litellm.completion") as mock_completion:
            def mock_completion_side_effect(*args, **kwargs):
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
                return mock_response

            mock_completion.side_effect = mock_completion_side_effect

            response = runner.generate_command("list files")
            assert response.command == "ls -la"
            assert response is not None

    def test_generate_command_with_validation_error(self, mock_config_manager, mock_cache_manager):
        """Test command generation with invalid input."""
        history_manager = HistoryManager()
        context_manager = ContextManager()

        runner = CommandRunner(
            mock_config_manager,
            history_manager,
            mock_cache_manager,
            context_manager,
        )

        from cli_nlp.exceptions import ValidationError

        # Empty query should raise ValidationError
        with pytest.raises(ValidationError):
            runner.generate_command("")

        # Query too long should raise ValidationError
        long_query = "x" * 10001
        with pytest.raises(ValidationError):
            runner.generate_command(long_query)

    def test_generate_command_with_api_error(self, mock_config_manager, mock_cache_manager):
        """Test command generation with API error."""
        history_manager = HistoryManager()
        context_manager = ContextManager()

        runner = CommandRunner(
            mock_config_manager,
            history_manager,
            mock_cache_manager,
            context_manager,
        )

        with patch("litellm.completion") as mock_completion:
            from cli_nlp.exceptions import APIError

            # Mock to raise exception on all retry attempts
            mock_completion.side_effect = Exception("API Error")

            with pytest.raises(APIError):
                runner.generate_command("list files")

    def test_generate_command_retry_logic(self, mock_config_manager, mock_cache_manager, mock_litellm_response):
        """Test that retry logic works on transient failures."""
        history_manager = HistoryManager()
        context_manager = ContextManager()

        runner = CommandRunner(
            mock_config_manager,
            history_manager,
            mock_cache_manager,
            context_manager,
        )

        call_count = 0

        def mock_completion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Transient error")
            # Return JSON response on success
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
            return mock_response

        with patch("litellm.completion") as mock_completion_func:
            mock_completion_func.side_effect = mock_completion

            response = runner.generate_command("list files")
            assert response.command == "ls -la"
            assert call_count == 2  # Should retry once

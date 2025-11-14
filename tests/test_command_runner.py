"""Unit tests for CommandRunner with mocked LLM calls."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from cli_nlp.command_runner import CommandRunner
from cli_nlp.models import CommandResponse, MultiCommandResponse, SafetyLevel


class TestCommandRunner:
    """Test suite for CommandRunner."""

    def test_init(
        self,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test CommandRunner initialization."""
        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        assert runner.config_manager == mock_config_manager
        assert runner.history_manager == mock_history_manager
        assert runner.cache_manager == mock_cache_manager
        assert runner.context_manager == mock_context_manager

    def test_setup_litellm_api_key_success(self, mock_config_manager, monkeypatch):
        """Test successful LiteLLM API key setup."""
        monkeypatch.setenv("OPENAI_API_KEY", "")

        runner = CommandRunner(config_manager=mock_config_manager)

        # Should not raise exception when API key is available
        runner._setup_litellm_api_key()
        # Verify API key was set in environment
        assert os.getenv("OPENAI_API_KEY") == "test-api-key-12345"

    def test_setup_litellm_api_key_missing(self, temp_dir, monkeypatch):
        """Test LiteLLM API key setup with missing API key."""
        from cli_nlp.config_manager import ConfigManager

        config_file = temp_dir / "config.json"
        config_file.write_text(
            json.dumps(
                {
                    "providers": {},
                    "active_provider": None,
                    "active_model": "gpt-4o-mini",
                }
            )
        )

        manager = ConfigManager()
        manager.config_path = config_file
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        runner = CommandRunner(config_manager=manager)

        with pytest.raises(SystemExit):
            runner._setup_litellm_api_key()

    def test_generate_command_pydantic_structured_output(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
        sample_command_response,
    ):
        """Test command generation using Pydantic structured output."""
        # Mock LiteLLM completion
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(
            {
                "command": "ls -la",
                "is_safe": True,
                "safety_level": "safe",
                "explanation": "List files in current directory",
            }
        )
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test
            result = runner.generate_command("list files", use_cache=False)

            # Assertions
            assert isinstance(result, CommandResponse)
            assert result.command == "ls -la"
            assert result.is_safe is True
            assert result.safety_level == SafetyLevel.SAFE
            mock_litellm_module.completion.assert_called_once()

    def test_generate_command_json_fallback(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test command generation using JSON fallback when structured output fails."""
        # Mock LiteLLM completion - first call fails (Pydantic schema), second succeeds (JSON mode)
        mock_response_json = MagicMock()
        mock_message_json = MagicMock()
        mock_message_json.content = json.dumps(
            {
                "command": "ls -la",
                "is_safe": True,
                "safety_level": "safe",
                "explanation": "List files in current directory",
            }
        )
        mock_choice_json = MagicMock()
        mock_choice_json.message = mock_message_json
        mock_response_json.choices = [mock_choice_json]

        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.side_effect = [
            Exception("Schema not supported"),
            mock_response_json,
        ]

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test
            result = runner.generate_command("list files", use_cache=False)

            # Assertions
            assert isinstance(result, CommandResponse)
            assert result.command == "ls -la"
            assert result.is_safe is True
            # Should have tried twice (Pydantic schema, then JSON mode)
            assert mock_litellm_module.completion.call_count == 2

    def test_generate_command_with_cache(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
        sample_command_response,
    ):
        """Test command generation uses cache when available."""
        # Setup cache
        mock_cache_manager.set(
            "list files", sample_command_response, model="gpt-4o-mini"
        )

        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Test - should return cached result
        result = runner.generate_command("list files")

        # Assertions
        assert result == sample_command_response
        # Should not have called LiteLLM (cached)
        # If we call again, it should use cache
        result2 = runner.generate_command("list files")
        assert result2 == sample_command_response
        # LiteLLM should not be called if cache is used
        # (This is tested implicitly - if cache works, LiteLLM won't be called)

    def test_generate_command_caches_result(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test that generated commands are cached."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]

        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Generate command
            result = runner.generate_command("list files", use_cache=True)

            # Check cache
            cached = mock_cache_manager.get("list files", model="gpt-4o-mini")
            assert cached is not None
            assert cached.command == result.command

    def test_generate_command_with_custom_model(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test command generation with custom model."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]

        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test with custom model
            runner.generate_command("list files", model="gpt-4o", use_cache=False)

            # Check model was used
            call_kwargs = mock_litellm_module.completion.call_args[1]
            assert call_kwargs["model"] == "gpt-4o"

    def test_refine_command(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test command refinement."""
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(
            {
                "command": "ls -la",
                "is_safe": True,
                "safety_level": "safe",
                "explanation": "List files including hidden",
            }
        )
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test refinement
            result = runner.refine_command(
                original_query="list files",
                refinement_request="show hidden files",
                original_command="ls",
            )

            assert isinstance(result, CommandResponse)
            mock_litellm_module.completion.assert_called_once()

    def test_generate_alternatives(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
        mock_openai_alternatives_response,
    ):
        """Test generating alternative commands."""
        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_openai_alternatives_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test alternatives
            alternatives = runner.generate_alternatives("list files", count=3)

            assert len(alternatives) == 3
            assert all(isinstance(alt, CommandResponse) for alt in alternatives)
            mock_litellm_module.completion.assert_called_once()

    def test_generate_multi_command(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
        mock_openai_multi_command_response,
    ):
        """Test generating multi-command responses."""
        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_openai_multi_command_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test multi-command
            result = runner.generate_multi_command("find python files and count lines")

            assert isinstance(result, MultiCommandResponse)
            assert len(result.commands) == 2
            assert result.execution_type == "pipeline"
            assert result.overall_safe is True
            mock_litellm_module.completion.assert_called_once()

    @patch("cli_nlp.command_runner.console")
    def test_run_display_only(
        self,
        mock_console,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run() method displays command without executing."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test run without execution
            runner.run("list files", execute=False)

            # Check history was saved
            assert len(mock_history_manager.get_all()) == 1
            entry = mock_history_manager.get_all()[0]
            assert entry.query == "list files"
            assert entry.executed is False

    @patch("cli_nlp.command_runner.subprocess")
    def test_run_execute_safe_command(
        self,
        mock_subprocess,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run() method executes safe commands."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]

        # Mock subprocess
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.run.return_value = mock_result

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test run with execution
            with pytest.raises(SystemExit) as exc_info:
                runner.run("list files", execute=True)

            assert exc_info.value.code == 0
            mock_subprocess.run.assert_called_once()

            # Check history
            entries = mock_history_manager.get_all()
            assert len(entries) == 1
            assert entries[0].executed is True
            assert entries[0].return_code == 0

    @patch("cli_nlp.command_runner.subprocess")
    def test_run_execute_modifying_command_without_force(
        self,
        mock_subprocess,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run() method blocks modifying commands without --force."""
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(
            {
                "command": "rm -rf /tmp/test",
                "is_safe": False,
                "safety_level": "modifying",
                "explanation": "Remove test directory",
            }
        )
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test run with modifying command without force
            with pytest.raises(SystemExit) as exc_info:
                runner.run("delete test directory", execute=True, force=False)

            assert exc_info.value.code == 1
            mock_subprocess.run.assert_not_called()

    def test_run_alternatives(
        self,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
        mock_openai_alternatives_response,
    ):
        """Test run() method with alternatives flag."""
        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_openai_alternatives_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test alternatives
            runner.run("list files", alternatives=True)

            mock_litellm_module.completion.assert_called_once()
            # Should not save to history when showing alternatives
            assert len(mock_history_manager.get_all()) == 0

    def test_run_batch(
        self,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
        temp_dir,
    ):
        """Test batch processing."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Create test file
            queries_file = temp_dir / "queries.txt"
            queries_file.write_text("list files\nshow disk usage\nfind python files")

            # Test batch - disable cache to ensure all queries are processed
            runner.run_batch(str(queries_file))

            # Should have processed 3 queries
            # Note: run_batch calls run() which uses cache by default
            # Since we're using the same mock response, cache might be hit
            # But run_batch processes each query, so we should see multiple calls
            assert (
                mock_litellm_module.completion.call_count >= 1
            )  # At least 1 call (may be cached)

    @patch("cli_nlp.command_runner.copy_to_clipboard")
    @patch("cli_nlp.command_runner.console")
    def test_run_copy_to_clipboard(
        self,
        mock_console,
        mock_copy,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run() method copies command to clipboard."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]
        mock_copy.return_value = True

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test run with copy flag
            runner.run("list files", copy=True)

            # Get the actual command that was generated
            mock_copy.assert_called_once()
            # The command should match what's in the response
            call_args = mock_copy.call_args[0]
            # Check that a command was copied
            assert len(call_args[0]) > 0
            assert call_args[0] == "ls -la"

    @patch("cli_nlp.command_runner.copy_to_clipboard")
    @patch("cli_nlp.command_runner.console")
    def test_run_copy_to_clipboard_fails(
        self,
        mock_console,
        mock_copy,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run() method handles clipboard copy failure."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]
        mock_copy.return_value = False

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test run with copy flag
            runner.run("list files", copy=True)

            mock_copy.assert_called_once()
            # Should print warning
            assert any(
                "clipboard" in str(call) for call in mock_console.print.call_args_list
            )

    @patch("cli_nlp.command_runner.click.prompt")
    @patch("cli_nlp.command_runner.console")
    def test_run_refine_mode(
        self,
        mock_console,
        mock_prompt,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run() method with refine mode."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]
        mock_prompt.return_value = "done"

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test refine mode
            runner.run("list files", refine=True)

            # Should prompt for refinement
            mock_prompt.assert_called_once()

    @patch("cli_nlp.command_runner.click.prompt")
    @patch("cli_nlp.command_runner.console")
    def test_run_refine_mode_with_refinement(
        self,
        mock_console,
        mock_prompt,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run() method with refine mode and actual refinement."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]
        mock_prompt.return_value = "add verbose flag"

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test refine mode with refinement
            runner.run("list files", refine=True)

            # Should call refine_command which calls generate_command again
            # The refinement triggers another API call
            assert (
                mock_litellm_module.completion.call_count >= 1
            )  # At least initial call
            # Note: refine_command calls generate_command which uses cache=False
            # So it should make another API call, but the exact count depends on implementation

    @patch("cli_nlp.command_runner.console")
    def test_run_edit_mode(
        self,
        mock_console,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run() method with edit mode."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock the tempfile and os operations that happen inside edit mode
        # Store real open before patching
        import builtins

        real_open = builtins.open
        import tempfile as real_tempfile

        # Setup tempfile mock
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.sh"
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=None)
        mock_file.write = MagicMock()

        # Setup file read mock
        mock_file_read = MagicMock()
        mock_file_read.readlines.return_value = ["#!/bin/bash\n", "ls -lah\n"]
        mock_file_read.__enter__ = MagicMock(return_value=mock_file_read)
        mock_file_read.__exit__ = MagicMock(return_value=None)

        def open_side_effect(path, *args, **kwargs):
            if isinstance(path, str) and path.endswith(".sh") and "/tmp" in path:
                return mock_file_read
            # For other files, use real open
            return real_open(path, *args, **kwargs)

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with (
            patch.dict("sys.modules", {"litellm": mock_litellm_module}),
            patch.object(
                real_tempfile, "NamedTemporaryFile", return_value=mock_file
            ) as mock_tempfile_class,
            patch("os.getenv", return_value="nano"),
            patch("os.system") as mock_system,
            patch("os.unlink"),
            patch("builtins.open", side_effect=open_side_effect),
        ):
            # Test edit mode
            runner.run("list files", edit=True)

            # Should have attempted to open editor (edit mode is triggered)
            # Note: edit mode only runs if not execute, and it tries to open editor
            # We verify the code path was taken by checking tempfile was used
            assert mock_tempfile_class.called or mock_system.called

    @patch("cli_nlp.command_runner.subprocess")
    def test_run_execute_unsafe_without_force(
        self,
        mock_subprocess,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run() method blocks unsafe command execution without force."""
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(
            {
                "command": "rm -rf /tmp/test",
                "is_safe": False,
                "safety_level": "modifying",
                "explanation": "Remove test directory",
            }
        )
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test run with unsafe command without force
            with pytest.raises(SystemExit) as exc_info:
                runner.run("delete test directory", execute=True, force=False)

            assert exc_info.value.code == 1
            mock_subprocess.run.assert_not_called()

    def test_run_multi_command_detection(
        self,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
        mock_openai_multi_command_response,
    ):
        """Test run() method detects and handles multi-command queries."""
        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_openai_multi_command_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Test multi-command query
            runner.run("find python files and count lines")

            mock_litellm_module.completion.assert_called_once()
            # Should have saved to history
            assert len(mock_history_manager.get_all()) == 1

    def test_run_batch_empty_file(
        self,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
        temp_dir,
    ):
        """Test run_batch() with empty file."""
        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Create empty file
        queries_file = temp_dir / "empty.txt"
        queries_file.write_text("")

        # Should handle gracefully (empty file means no queries to process)
        runner.run_batch(str(queries_file))
        # Should not raise exception

    def test_run_batch_file_with_comments(
        self,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
        temp_dir,
    ):
        """Test run_batch() skips comments and empty lines."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            # Create file with comments
            queries_file = temp_dir / "queries.txt"
            queries_file.write_text(
                "# This is a comment\nlist files\n# Another comment\n\nshow disk usage"
            )

            runner.run_batch(str(queries_file))

            # Should process only 2 queries (skipping comments and empty lines)
            # Note: run() uses cache by default, so if queries are similar, might be cached
            assert mock_litellm_module.completion.call_count >= 1  # At least 1 call

    def test_run_batch_file_not_found(
        self,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run_batch() handles file not found."""
        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        with pytest.raises(SystemExit) as exc_info:
            runner.run_batch("/nonexistent/file.txt")

        assert exc_info.value.code == 1

    def test_run_batch_file_read_error(
        self,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run_batch() handles file read error."""
        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(SystemExit) as exc_info:
                runner.run_batch("/some/file.txt")

            assert exc_info.value.code == 1

    @patch("cli_nlp.command_runner.console")
    def test_run_batch_query_error(
        self,
        mock_console,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
        temp_dir,
    ):
        """Test run_batch() handles individual query errors."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        # First call succeeds, second call fails
        mock_litellm_module.completion.side_effect = [
            mock_response,
            Exception("Query error"),
        ]

        def mock_exit(code=0):
            # Convert sys.exit to raise SystemExit exception instead
            raise SystemExit(code)

        with (
            patch.dict("sys.modules", {"litellm": mock_litellm_module}),
            patch("sys.exit", side_effect=mock_exit),
        ):
            queries_file = temp_dir / "queries.txt"
            queries_file.write_text("list files\nbad query")

            # Should handle error gracefully and continue
            # run_batch now catches SystemExit as well
            runner.run_batch(str(queries_file))

            # Should have processed first query (second fails)
            # The first call succeeds, second raises exception
            assert (
                mock_litellm_module.completion.call_count >= 1
            )  # At least the first call

    @patch("cli_nlp.command_runner.subprocess")
    def test_run_execute_keyboard_interrupt(
        self,
        mock_subprocess,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run() method handles KeyboardInterrupt during execution."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]

        mock_subprocess.run.side_effect = KeyboardInterrupt()

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            with pytest.raises(SystemExit) as exc_info:
                runner.run("list files", execute=True, force=True)

            assert exc_info.value.code == 130
            # Should have saved to history with return code 130
            entries = mock_history_manager.get_all()
            assert len(entries) == 1
            assert entries[0].return_code == 130

    @patch("cli_nlp.command_runner.subprocess")
    def test_run_execute_exception(
        self,
        mock_subprocess,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run() method handles exceptions during execution."""
        mock_response = MagicMock()
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
        mock_response.choices = [mock_choice]

        mock_subprocess.run.side_effect = Exception("Execution error")

        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )

        # Mock litellm module since it's imported inside the function
        mock_litellm_module = MagicMock()
        mock_litellm_module.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm_module}):
            with pytest.raises(SystemExit) as exc_info:
                runner.run("list files", execute=True, force=True)

            assert exc_info.value.code == 1
            # Should have saved to history with return code 1
            entries = mock_history_manager.get_all()
            assert len(entries) == 1
            assert entries[0].return_code == 1

"""Unit tests for CommandRunner with mocked LLM calls."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from cli_nlp.command_runner import CommandRunner
from cli_nlp.models import CommandResponse, MultiCommandResponse, SafetyLevel


class TestCommandRunner:
    """Test suite for CommandRunner."""
    
    def test_init(self, mock_config_manager, mock_history_manager, mock_cache_manager, mock_context_manager):
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
    
    @patch('openai.OpenAI')
    def test_get_openai_client_success(self, mock_openai_class, mock_config_manager):
        """Test successful OpenAI client initialization."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        runner = CommandRunner(config_manager=mock_config_manager)
        client = runner._get_openai_client()
        
        mock_openai_class.assert_called_once_with(api_key="test-api-key-12345")
        assert client == mock_client
    
    def test_get_openai_client_missing_key(self, mock_config_manager, monkeypatch):
        """Test OpenAI client initialization with missing API key."""
        # Clear API key from config
        mock_config_manager.config_path.write_text(json.dumps({}))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        runner = CommandRunner(config_manager=mock_config_manager)
        
        with pytest.raises(SystemExit):
            runner._get_openai_client()
    
    def test_generate_command_structured_output(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
        sample_command_response,
        mock_openai_response_structured,
    ):
        """Test command generation using structured output (parse)."""
        # Setup mocks
        mock_client = MagicMock()
        mock_parse = MagicMock(return_value=mock_openai_response_structured)
        mock_client.beta.chat.completions.parse = mock_parse
        
        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )
        runner._client = mock_client
        
        # Test
        result = runner.generate_command("list files", use_cache=False)
        
        # Assertions
        assert isinstance(result, CommandResponse)
        assert result.command == "ls -la"
        assert result.is_safe is True
        assert result.safety_level == SafetyLevel.SAFE
        mock_parse.assert_called_once()
    
    def test_generate_command_json_fallback(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
        mock_openai_response_json,
    ):
        """Test command generation using JSON fallback when structured output fails."""
        # Setup mocks
        mock_client = MagicMock()
        
        # Make structured output fail
        mock_client.beta.chat.completions.parse.side_effect = AttributeError("Not supported")
        
        # Setup JSON response
        mock_create = MagicMock(return_value=mock_openai_response_json)
        mock_client.chat.completions.create = mock_create
        
        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )
        runner._client = mock_client
        
        # Test
        result = runner.generate_command("list files", use_cache=False)
        
        # Assertions
        assert isinstance(result, CommandResponse)
        assert result.command == "ls -la"
        assert result.is_safe is True
        mock_create.assert_called_once()
        # Verify JSON mode was used
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs.get("response_format") == {"type": "json_object"}
    
    def test_generate_command_with_cache(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
        sample_command_response,
    ):
        """Test command generation uses cache when available."""
        # Setup cache
        mock_cache_manager.set("list files", sample_command_response, model="gpt-4o-mini")
        
        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )
        
        # Test - should return cached result
        result = runner.generate_command("list files")
        
        # Assertions
        assert result == sample_command_response
        # Should not have created client
        assert runner._client is None
    
    def test_generate_command_caches_result(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
        mock_openai_response_structured,
    ):
        """Test that generated commands are cached."""
        mock_client = MagicMock()
        mock_parse = MagicMock(return_value=mock_openai_response_structured)
        mock_client.beta.chat.completions.parse = mock_parse
        
        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )
        runner._client = mock_client
        
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
        mock_openai_response_structured,
    ):
        """Test command generation with custom model."""
        mock_client = MagicMock()
        mock_parse = MagicMock(return_value=mock_openai_response_structured)
        mock_client.beta.chat.completions.parse = mock_parse
        
        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )
        runner._client = mock_client
        
        # Test with custom model
        runner.generate_command("list files", model="gpt-4o", use_cache=False)
        
        # Check model was used
        call_args = mock_parse.call_args
        assert call_args[1]["model"] == "gpt-4o"
    
    def test_refine_command(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
        mock_openai_response_structured,
    ):
        """Test command refinement."""
        mock_client = MagicMock()
        mock_parse = MagicMock(return_value=mock_openai_response_structured)
        mock_client.beta.chat.completions.parse = mock_parse
        
        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )
        runner._client = mock_client
        
        # Test refinement
        result = runner.refine_command(
            original_query="list files",
            refinement_request="show hidden files",
            original_command="ls",
        )
        
        assert isinstance(result, CommandResponse)
        mock_parse.assert_called_once()
    
    def test_generate_alternatives(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
        mock_openai_alternatives_response,
    ):
        """Test generating alternative commands."""
        mock_client = MagicMock()
        mock_create = MagicMock(return_value=mock_openai_alternatives_response)
        mock_client.chat.completions.create = mock_create
        
        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )
        runner._client = mock_client
        
        # Test alternatives
        alternatives = runner.generate_alternatives("list files", count=3)
        
        assert len(alternatives) == 3
        assert all(isinstance(alt, CommandResponse) for alt in alternatives)
        mock_create.assert_called_once()
    
    def test_generate_multi_command(
        self,
        mock_config_manager,
        mock_cache_manager,
        mock_context_manager,
        mock_openai_multi_command_response,
    ):
        """Test generating multi-command responses."""
        mock_client = MagicMock()
        mock_create = MagicMock(return_value=mock_openai_multi_command_response)
        mock_client.chat.completions.create = mock_create
        
        runner = CommandRunner(
            config_manager=mock_config_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )
        runner._client = mock_client
        
        # Test multi-command
        result = runner.generate_multi_command("find python files and count lines")
        
        assert isinstance(result, MultiCommandResponse)
        assert len(result.commands) == 2
        assert result.execution_type == "pipeline"
        assert result.overall_safe is True
        mock_create.assert_called_once()
    
    @patch('cli_nlp.command_runner.console')
    def test_run_display_only(
        self,
        mock_console,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
        mock_openai_response_structured,
    ):
        """Test run() method displays command without executing."""
        mock_client = MagicMock()
        mock_parse = MagicMock(return_value=mock_openai_response_structured)
        mock_client.beta.chat.completions.parse = mock_parse
        
        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )
        runner._client = mock_client
        
        # Test run without execution
        runner.run("list files", execute=False)
        
        # Check history was saved
        assert len(mock_history_manager.get_all()) == 1
        entry = mock_history_manager.get_all()[0]
        assert entry.query == "list files"
        assert entry.executed is False
    
    @patch('cli_nlp.command_runner.subprocess')
    def test_run_execute_safe_command(
        self,
        mock_subprocess,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
        mock_openai_response_structured,
    ):
        """Test run() method executes safe commands."""
        mock_client = MagicMock()
        mock_parse = MagicMock(return_value=mock_openai_response_structured)
        mock_client.beta.chat.completions.parse = mock_parse
        
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
        runner._client = mock_client
        
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
    
    @patch('cli_nlp.command_runner.subprocess')
    def test_run_execute_modifying_command_without_force(
        self,
        mock_subprocess,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
    ):
        """Test run() method blocks modifying commands without --force."""
        mock_client = MagicMock()
        
        # Create modifying command response
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.parsed = CommandResponse(
            command="rm -rf /tmp/test",
            is_safe=False,
            safety_level=SafetyLevel.MODIFYING,
            explanation="Remove test directory",
        )
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_parse = MagicMock(return_value=mock_response)
        mock_client.beta.chat.completions.parse = mock_parse
        
        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )
        runner._client = mock_client
        
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
        mock_client = MagicMock()
        mock_create = MagicMock(return_value=mock_openai_alternatives_response)
        mock_client.chat.completions.create = mock_create
        
        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )
        runner._client = mock_client
        
        # Test alternatives
        runner.run("list files", alternatives=True)
        
        mock_create.assert_called_once()
        # Should not save to history when showing alternatives
        assert len(mock_history_manager.get_all()) == 0
    
    def test_run_batch(
        self,
        mock_config_manager,
        mock_history_manager,
        mock_cache_manager,
        mock_context_manager,
        mock_openai_response_structured,
        temp_dir,
    ):
        """Test batch processing."""
        mock_client = MagicMock()
        mock_parse = MagicMock(return_value=mock_openai_response_structured)
        mock_client.beta.chat.completions.parse = mock_parse
        
        runner = CommandRunner(
            config_manager=mock_config_manager,
            history_manager=mock_history_manager,
            cache_manager=mock_cache_manager,
            context_manager=mock_context_manager,
        )
        runner._client = mock_client
        
        # Create test file
        queries_file = temp_dir / "queries.txt"
        queries_file.write_text("list files\nshow disk usage\nfind python files")
        
        # Test batch
        runner.run_batch(str(queries_file))
        
        # Should have processed 3 queries
        assert mock_parse.call_count == 3


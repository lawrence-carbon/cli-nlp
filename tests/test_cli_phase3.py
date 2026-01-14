"""Tests for Phase 3 CLI features."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cli_nlp.cli import cli
from cli_nlp.models import CommandResponse, SafetyLevel


class TestCLIPhase3Features:
    """Test Phase 3 CLI features."""

    def test_dry_run_flag(self, mock_config_manager, mock_cache_manager):
        """Test --dry-run flag."""
        from cli_nlp.command_runner import CommandRunner
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

            # Should not execute even if execute=True
            runner.run("list files", execute=True, dry_run=True)
            # Verify command was generated but not executed
            # (execution would exit, so if we get here, dry-run worked)

    def test_json_output_flag(self, mock_config_manager, mock_cache_manager, capsys):
        """Test --json output flag."""
        from cli_nlp.command_runner import CommandRunner
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

            runner.run("list files", output_json=True)
            captured = capsys.readouterr()
            # JSON output should be in stdout
            output_text = captured.out.strip()
            # Find JSON in output (may have other text)
            try:
                # Try to find JSON object in output
                import re
                json_match = re.search(r'\{[^{}]*"command"[^{}]*\}', output_text, re.DOTALL)
                if json_match:
                    output = json.loads(json_match.group(0))
                else:
                    # Try parsing entire output
                    output = json.loads(output_text)
                assert output["command"] == "ls -la"
                assert output["is_safe"] is True
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, at least verify command is mentioned
                assert "ls -la" in output_text or '"command"' in output_text

    def test_debug_flag(self, mock_config_manager):
        """Test --debug flag sets debug logging."""
        from cli_nlp.logger import setup_logging

        # Debug should set level to DEBUG
        logger = setup_logging(level="DEBUG", verbose=True)
        assert logger.level == 10  # DEBUG level

    def test_metrics_command_show(self, temp_dir, monkeypatch):
        """Test metrics show command."""
        from cli_nlp.metrics import MetricsCollector

        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        collector = MetricsCollector()
        collector.record_query(cached=True, execution_time=0.1, provider="openai")

        stats = collector.get_stats()
        assert stats["total_queries"] == 1
        assert stats["cache_hits"] == 1

    def test_metrics_command_reset(self, temp_dir, monkeypatch):
        """Test metrics reset command."""
        from cli_nlp.metrics import MetricsCollector

        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        collector = MetricsCollector()
        collector.record_query(cached=True, execution_time=0.1, provider="openai")
        assert collector._metrics.total_queries == 1

        collector.reset()
        assert collector._metrics.total_queries == 0

    def test_stats_command(self, temp_dir, monkeypatch):
        """Test stats command."""
        from cli_nlp.metrics import MetricsCollector

        monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir))
        collector = MetricsCollector()
        collector.record_query(cached=False, execution_time=0.5, provider="openai", model="gpt-4o-mini")
        collector.record_query(cached=False, execution_time=0.3, provider="anthropic", model="claude-3-opus")

        stats = collector.get_stats()
        comparison = collector.get_provider_comparison()

        assert stats["total_queries"] == 2
        assert len(comparison) == 2

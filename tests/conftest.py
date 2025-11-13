"""Pytest configuration and fixtures for CLI-NLP tests."""

import json
from unittest.mock import MagicMock

import pytest

from cli_nlp.cache_manager import CacheManager
from cli_nlp.config_manager import ConfigManager
from cli_nlp.context_manager import ContextManager
from cli_nlp.history_manager import HistoryManager
from cli_nlp.models import CommandResponse, MultiCommandResponse, SafetyLevel
from cli_nlp.template_manager import TemplateManager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def temp_config_file(temp_dir):
    """Create a temporary config file with new multi-provider structure."""
    config_file = temp_dir / "config.json"
    config_data = {
        "providers": {
            "openai": {
                "api_key": "test-api-key-12345",
                "models": ["gpt-4o-mini", "gpt-4o"]
            }
        },
        "active_provider": "openai",
        "active_model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 200,
        "cache_ttl_seconds": 86400,
        "include_git_context": True,
    }
    config_file.write_text(json.dumps(config_data))
    return config_file


@pytest.fixture
def mock_config_manager(temp_config_file, monkeypatch):
    """Create a ConfigManager with a temporary config file."""
    manager = ConfigManager()
    # Override the config path to use our temp file
    monkeypatch.setattr(manager, "config_path", temp_config_file)
    return manager


@pytest.fixture
def temp_cache_file(temp_dir):
    """Create a temporary cache file."""
    return temp_dir / "command_cache.json"


@pytest.fixture
def mock_cache_manager(temp_cache_file, monkeypatch):
    """Create a CacheManager with a temporary cache file."""
    manager = CacheManager(ttl_seconds=86400)
    monkeypatch.setattr(manager, "cache_path", temp_cache_file)
    return manager


@pytest.fixture
def temp_history_file(temp_dir):
    """Create a temporary history file."""
    return temp_dir / "history.json"


@pytest.fixture
def mock_history_manager(temp_history_file, monkeypatch):
    """Create a HistoryManager with a temporary history file."""
    manager = HistoryManager()
    monkeypatch.setattr(manager, "history_path", temp_history_file)
    # Clear any existing history
    manager._history = []
    manager._save_history()
    return manager


@pytest.fixture
def temp_templates_file(temp_dir):
    """Create a temporary templates file."""
    return temp_dir / "templates.json"


@pytest.fixture
def mock_template_manager(temp_templates_file, monkeypatch):
    """Create a TemplateManager with a temporary templates file."""
    manager = TemplateManager()
    monkeypatch.setattr(manager, "templates_path", temp_templates_file)
    return manager


@pytest.fixture
def mock_context_manager():
    """Create a ContextManager."""
    return ContextManager()


@pytest.fixture
def mock_openai_client():
    """Create a mocked OpenAI client."""
    client = MagicMock()

    # Mock the chat completions API
    mock_chat = MagicMock()
    client.chat = mock_chat
    client.beta = MagicMock()
    client.beta.chat = MagicMock()

    return client


@pytest.fixture
def sample_command_response():
    """Create a sample CommandResponse for testing."""
    return CommandResponse(
        command="ls -la",
        is_safe=True,
        safety_level=SafetyLevel.SAFE,
        explanation="List files in current directory",
    )


@pytest.fixture
def sample_modifying_command_response():
    """Create a sample modifying CommandResponse for testing."""
    return CommandResponse(
        command="rm -rf /tmp/test",
        is_safe=False,
        safety_level=SafetyLevel.MODIFYING,
        explanation="Remove test directory",
    )


@pytest.fixture
def sample_multi_command_response():
    """Create a sample MultiCommandResponse for testing."""
    return MultiCommandResponse(
        commands=[
            CommandResponse(
                command="find . -name '*.py'",
                is_safe=True,
                safety_level=SafetyLevel.SAFE,
                explanation="Find Python files",
            ),
            CommandResponse(
                command="wc -l",
                is_safe=True,
                safety_level=SafetyLevel.SAFE,
                explanation="Count lines",
            ),
        ],
        execution_type="pipeline",
        combined_command="find . -name '*.py' | wc -l",
        overall_safe=True,
        explanation="Find Python files and count lines",
    )


@pytest.fixture
def mock_openai_response_structured(sample_command_response):
    """Mock OpenAI structured response (using parse)."""
    mock_message = MagicMock()
    mock_message.parsed = sample_command_response

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    return mock_response


@pytest.fixture
def mock_openai_response_json():
    """Mock OpenAI JSON response."""
    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "command": "ls -la",
        "is_safe": True,
        "safety_level": "safe",
        "explanation": "List files in current directory",
    })

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    return mock_response


@pytest.fixture
def mock_openai_alternatives_response():
    """Mock OpenAI response for alternatives."""
    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "alternatives": [
            {
                "command": "ls -la",
                "is_safe": True,
                "safety_level": "safe",
                "explanation": "List files with details",
            },
            {
                "command": "ls -lah",
                "is_safe": True,
                "safety_level": "safe",
                "explanation": "List files with human-readable sizes",
            },
            {
                "command": "find . -maxdepth 1 -type f",
                "is_safe": True,
                "safety_level": "safe",
                "explanation": "Find files in current directory",
            },
        ]
    })

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    return mock_response


@pytest.fixture
def mock_openai_multi_command_response():
    """Mock OpenAI response for multi-command."""
    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "commands": [
            {
                "command": "find . -name '*.py'",
                "is_safe": True,
                "safety_level": "safe",
                "explanation": "Find Python files",
            },
            {
                "command": "wc -l",
                "is_safe": True,
                "safety_level": "safe",
                "explanation": "Count lines",
            },
        ],
        "execution_type": "pipeline",
        "combined_command": "find . -name '*.py' | wc -l",
        "overall_safe": True,
        "explanation": "Find Python files and count lines",
    })

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    return mock_response


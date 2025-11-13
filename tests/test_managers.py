"""Unit tests for managers (ConfigManager, CacheManager, HistoryManager, TemplateManager, ContextManager)."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cli_nlp.cache_manager import CacheEntry, CacheManager
from cli_nlp.config_manager import ConfigManager
from cli_nlp.context_manager import ContextManager
from cli_nlp.history_manager import HistoryEntry, HistoryManager
from cli_nlp.models import CommandResponse, SafetyLevel
from cli_nlp.template_manager import TemplateManager


class TestConfigManager:
    """Test suite for ConfigManager."""
    
    def test_init(self, temp_dir, monkeypatch):
        """Test ConfigManager initialization."""
        config_file = temp_dir / "config.json"
        manager = ConfigManager()
        monkeypatch.setattr(manager, "config_path", config_file)
        
        assert manager.config_path == config_file
    
    def test_load_existing_config(self, temp_config_file):
        """Test loading existing config file."""
        manager = ConfigManager()
        # Override path
        manager.config_path = temp_config_file
        
        config = manager.load()
        assert config["providers"]["openai"]["api_key"] == "test-api-key-12345"
        assert config["active_provider"] == "openai"
        assert config["active_model"] == "gpt-4o-mini"
    
    def test_load_nonexistent_config(self, temp_dir, monkeypatch):
        """Test loading non-existent config file."""
        config_file = temp_dir / "nonexistent.json"
        manager = ConfigManager()
        monkeypatch.setattr(manager, "config_path", config_file)
        
        config = manager.load()
        # Should return default config structure
        assert "providers" in config
        assert config["providers"] == {}
        assert config["active_provider"] is None
    
    def test_create_default(self, temp_dir, monkeypatch):
        """Test creating default config file."""
        config_file = temp_dir / "new_config.json"
        manager = ConfigManager()
        monkeypatch.setattr(manager, "config_path", config_file)
        
        result = manager.create_default()
        assert result is True
        assert config_file.exists()
        
        config = manager.load()
        assert "providers" in config
        assert config["providers"] == {}
        assert config["active_provider"] is None
        assert config["active_model"] == "gpt-4o-mini"
    
    def test_create_default_existing(self, temp_config_file):
        """Test creating default config when file already exists."""
        manager = ConfigManager()
        manager.config_path = temp_config_file
        
        result = manager.create_default()
        assert result is False
    
    def test_get_api_key_from_config(self, temp_config_file):
        """Test getting API key from config file."""
        manager = ConfigManager()
        manager.config_path = temp_config_file
        
        api_key = manager.get_api_key()
        assert api_key == "test-api-key-12345"
    
    def test_get_api_key_from_env(self, temp_dir, monkeypatch):
        """Test getting API key from environment variable."""
        config_file = temp_dir / "config.json"
        config_file.write_text(json.dumps({
            "providers": {},
            "active_provider": "openai",
            "active_model": "gpt-4o-mini"
        }))
        
        manager = ConfigManager()
        monkeypatch.setattr(manager, "config_path", config_file)
        monkeypatch.setenv("OPENAI_API_KEY", "env-api-key")
        
        api_key = manager.get_api_key()
        assert api_key == "env-api-key"
    
    def test_migrate_old_config(self, temp_dir, monkeypatch):
        """Test migration of old config format to new format."""
        config_file = temp_dir / "old_config.json"
        # Write old format
        old_config = {
            "openai_api_key": "old-key-123",
            "default_model": "gpt-4",
            "temperature": 0.5
        }
        config_file.write_text(json.dumps(old_config))
        
        manager = ConfigManager()
        monkeypatch.setattr(manager, "config_path", config_file)
        
        config = manager.load()
        # Should be migrated
        assert "providers" in config
        assert config["providers"]["openai"]["api_key"] == "old-key-123"
        assert config["active_provider"] == "openai"
        assert config["active_model"] == "gpt-4"
        assert config["temperature"] == 0.5
    
    def test_get_active_provider(self, temp_config_file):
        """Test getting active provider."""
        manager = ConfigManager()
        manager.config_path = temp_config_file
        
        provider = manager.get_active_provider()
        assert provider == "openai"
    
    def test_get_active_model(self, temp_config_file):
        """Test getting active model."""
        manager = ConfigManager()
        manager.config_path = temp_config_file
        
        model = manager.get_active_model()
        assert model == "gpt-4o-mini"
    
    def test_add_provider(self, temp_dir, monkeypatch):
        """Test adding a provider."""
        config_file = temp_dir / "config.json"
        config_file.write_text(json.dumps({
            "providers": {},
            "active_provider": None,
            "active_model": "gpt-4o-mini"
        }))
        
        manager = ConfigManager()
        monkeypatch.setattr(manager, "config_path", config_file)
        
        result = manager.add_provider("anthropic", "sk-ant-test", ["claude-3-opus"])
        assert result is True
        
        config = manager.load()
        assert "anthropic" in config["providers"]
        assert config["providers"]["anthropic"]["api_key"] == "sk-ant-test"
    
    def test_set_active_provider(self, temp_config_file):
        """Test setting active provider."""
        manager = ConfigManager()
        manager.config_path = temp_config_file
        
        # Add another provider first
        manager.add_provider("anthropic", "sk-ant-test", ["claude-3-opus"])
        
        result = manager.set_active_provider("anthropic")
        assert result is True
        
        assert manager.get_active_provider() == "anthropic"
    
    def test_remove_provider(self, temp_config_file):
        """Test removing a provider."""
        manager = ConfigManager()
        manager.config_path = temp_config_file
        
        # Add a provider
        manager.add_provider("anthropic", "sk-ant-test", ["claude-3-opus"])
        
        result = manager.remove_provider("anthropic")
        assert result is True
        
        config = manager.load()
        assert "anthropic" not in config["providers"]
    
    def test_get_config_value(self, temp_config_file):
        """Test getting config value."""
        manager = ConfigManager()
        manager.config_path = temp_config_file
        
        model = manager.get("active_model")
        assert model == "gpt-4o-mini"
    
    def test_get_config_value_default(self, temp_dir, monkeypatch):
        """Test getting config value with default."""
        config_file = temp_dir / "config.json"
        config_file.write_text(json.dumps({
            "providers": {},
            "active_provider": None,
            "active_model": "gpt-4o-mini"
        }))
        
        manager = ConfigManager()
        monkeypatch.setattr(manager, "config_path", config_file)
        
        value = manager.get("nonexistent_key", "default_value")
        assert value == "default_value"


class TestCacheManager:
    """Test suite for CacheManager."""
    
    def test_init(self, temp_cache_file, monkeypatch):
        """Test CacheManager initialization."""
        manager = CacheManager()
        monkeypatch.setattr(manager, "cache_path", temp_cache_file)
        
        assert manager.cache_path == temp_cache_file
        assert manager._stats["hits"] == 0
        assert manager._stats["misses"] == 0
    
    def test_cache_entry_not_expired(self):
        """Test cache entry is not expired."""
        entry = CacheEntry(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
            timestamp=datetime.now(),
            ttl_seconds=86400,
        )
        assert entry.is_expired() is False
    
    def test_cache_entry_expired(self):
        """Test cache entry is expired."""
        entry = CacheEntry(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
            timestamp=datetime.now() - timedelta(days=2),
            ttl_seconds=86400,
        )
        assert entry.is_expired() is True
    
    def test_cache_entry_to_dict(self):
        """Test cache entry serialization."""
        entry = CacheEntry(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
            timestamp=datetime.now(),
        )
        data = entry.to_dict()
        assert data["command"] == "ls -la"
        assert data["is_safe"] is True
        assert data["safety_level"] == "safe"
    
    def test_cache_entry_from_dict(self):
        """Test cache entry deserialization."""
        data = {
            "command": "ls -la",
            "is_safe": True,
            "safety_level": "safe",
            "explanation": "List files",
            "timestamp": datetime.now().isoformat(),
            "ttl_seconds": 86400,
        }
        entry = CacheEntry.from_dict(data)
        assert entry.command == "ls -la"
        assert entry.is_safe is True
    
    def test_cache_get_miss(self, mock_cache_manager):
        """Test cache get on miss."""
        result = mock_cache_manager.get("nonexistent query")
        assert result is None
        assert mock_cache_manager._stats["misses"] == 1
    
    def test_cache_set_and_get(self, mock_cache_manager, sample_command_response):
        """Test cache set and get."""
        mock_cache_manager.set("list files", sample_command_response)
        
        result = mock_cache_manager.get("list files")
        assert result is not None
        assert result.command == sample_command_response.command
        assert mock_cache_manager._stats["hits"] == 1
    
    def test_cache_get_expired(self, mock_cache_manager, sample_command_response):
        """Test cache get returns None for expired entries."""
        # Create expired entry manually
        entry = CacheEntry(
            command=sample_command_response.command,
            is_safe=sample_command_response.is_safe,
            safety_level=sample_command_response.safety_level,
            explanation=sample_command_response.explanation,
            timestamp=datetime.now() - timedelta(days=2),
            ttl_seconds=86400,
        )
        cache_key = mock_cache_manager._query_hash("list files")
        mock_cache_manager._cache[cache_key] = entry
        
        result = mock_cache_manager.get("list files")
        assert result is None
        assert cache_key not in mock_cache_manager._cache
    
    def test_cache_clear(self, mock_cache_manager, sample_command_response):
        """Test cache clear."""
        mock_cache_manager.set("query1", sample_command_response)
        mock_cache_manager.set("query2", sample_command_response)
        
        assert len(mock_cache_manager._cache) > 0
        mock_cache_manager.clear()
        assert len(mock_cache_manager._cache) == 0
    
    def test_cache_stats(self, mock_cache_manager, sample_command_response):
        """Test cache statistics."""
        # Generate some hits and misses
        mock_cache_manager.get("miss1")
        mock_cache_manager.get("miss2")
        mock_cache_manager.set("hit1", sample_command_response)
        mock_cache_manager.get("hit1")
        mock_cache_manager.get("hit1")
        
        stats = mock_cache_manager.get_stats()
        assert stats["misses"] == 2
        assert stats["hits"] == 2
        assert stats["total"] == 4
        assert stats["hit_rate"] == 50.0


class TestHistoryManager:
    """Test suite for HistoryManager."""
    
    def test_init(self, temp_history_file, monkeypatch):
        """Test HistoryManager initialization."""
        manager = HistoryManager()
        monkeypatch.setattr(manager, "history_path", temp_history_file)
        # Clear any existing history that might have been loaded
        manager._history = []
        manager._save_history()
        
        assert manager.history_path == temp_history_file
        assert len(manager._history) == 0
    
    def test_add_entry(self, mock_history_manager):
        """Test adding history entry."""
        entry = mock_history_manager.add_entry(
            query="list files",
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )
        
        assert isinstance(entry, HistoryEntry)
        assert entry.query == "list files"
        assert len(mock_history_manager.get_all()) == 1
    
    def test_get_all(self, mock_history_manager):
        """Test getting all history entries."""
        mock_history_manager.add_entry(
            query="query1",
            command="cmd1",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
        )
        mock_history_manager.add_entry(
            query="query2",
            command="cmd2",
            is_safe=False,
            safety_level=SafetyLevel.MODIFYING,
        )
        
        entries = mock_history_manager.get_all()
        assert len(entries) == 2
        # Most recent first
        assert entries[0].query == "query2"
    
    def test_get_all_with_limit(self, mock_history_manager):
        """Test getting history entries with limit."""
        for i in range(5):
            mock_history_manager.add_entry(
                query=f"query{i}",
                command=f"cmd{i}",
                is_safe=True,
                safety_level=SafetyLevel.SAFE,
            )
        
        entries = mock_history_manager.get_all(limit=3)
        assert len(entries) == 3
    
    def test_search(self, mock_history_manager):
        """Test searching history."""
        mock_history_manager.add_entry(
            query="list python files",
            command="find . -name '*.py'",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
        )
        mock_history_manager.add_entry(
            query="show disk usage",
            command="df -h",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
        )
        
        results = mock_history_manager.search("python")
        assert len(results) == 1
        assert "python" in results[0].query.lower()
    
    def test_get_by_id(self, mock_history_manager):
        """Test getting entry by ID."""
        mock_history_manager.add_entry(
            query="query1",
            command="cmd1",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
        )
        mock_history_manager.add_entry(
            query="query2",
            command="cmd2",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
        )
        
        entry = mock_history_manager.get_by_id(0)
        assert entry.query == "query2"  # Most recent first
        
        entry = mock_history_manager.get_by_id(1)
        assert entry.query == "query1"
    
    def test_get_by_id_invalid(self, mock_history_manager):
        """Test getting entry with invalid ID."""
        assert mock_history_manager.get_by_id(999) is None
        assert mock_history_manager.get_by_id(-1) is None
    
    def test_clear(self, mock_history_manager):
        """Test clearing history."""
        mock_history_manager.add_entry(
            query="query1",
            command="cmd1",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
        )
        
        mock_history_manager.clear()
        assert len(mock_history_manager.get_all()) == 0
    
    def test_export_json(self, mock_history_manager):
        """Test exporting history as JSON."""
        mock_history_manager.add_entry(
            query="list files",
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
        )
        
        json_str = mock_history_manager.export(format="json")
        data = json.loads(json_str)
        assert len(data) == 1
        assert data[0]["query"] == "list files"
    
    def test_export_csv(self, mock_history_manager):
        """Test exporting history as CSV."""
        mock_history_manager.add_entry(
            query="list files",
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
        )
        
        csv_str = mock_history_manager.export(format="csv")
        assert "list files" in csv_str
        assert "ls -la" in csv_str


class TestTemplateManager:
    """Test suite for TemplateManager."""
    
    def test_init(self, temp_templates_file, monkeypatch):
        """Test TemplateManager initialization."""
        manager = TemplateManager()
        monkeypatch.setattr(manager, "templates_path", temp_templates_file)
        
        assert manager.templates_path == temp_templates_file
    
    def test_save_template(self, mock_template_manager):
        """Test saving template."""
        result = mock_template_manager.save_template(
            name="test",
            command="ls -la",
            description="List files",
        )
        
        assert result is True
        assert mock_template_manager.template_exists("test")
    
    def test_save_template_invalid(self, mock_template_manager):
        """Test saving invalid template."""
        result = mock_template_manager.save_template(name="", command="ls")
        assert result is False
        
        result = mock_template_manager.save_template(name="test", command="")
        assert result is False
    
    def test_get_template(self, mock_template_manager):
        """Test getting template."""
        mock_template_manager.save_template("test", "ls -la", "List files")
        
        command = mock_template_manager.get_template("test")
        assert command == "ls -la"
    
    def test_get_template_nonexistent(self, mock_template_manager):
        """Test getting non-existent template."""
        command = mock_template_manager.get_template("nonexistent")
        assert command is None
    
    def test_list_templates(self, mock_template_manager):
        """Test listing templates."""
        # Clear any existing templates first
        existing = mock_template_manager.list_templates()
        for name in list(existing.keys()):
            mock_template_manager.delete_template(name)
        
        mock_template_manager.save_template("t1", "cmd1", "Desc1")
        mock_template_manager.save_template("t2", "cmd2", "Desc2")
        
        templates = mock_template_manager.list_templates()
        assert len(templates) == 2
        assert "t1" in templates
        assert "t2" in templates
    
    def test_delete_template(self, mock_template_manager):
        """Test deleting template."""
        mock_template_manager.save_template("test", "ls -la")
        
        result = mock_template_manager.delete_template("test")
        assert result is True
        assert not mock_template_manager.template_exists("test")
    
    def test_delete_template_nonexistent(self, mock_template_manager):
        """Test deleting non-existent template."""
        result = mock_template_manager.delete_template("nonexistent")
        assert result is False
    
    def test_template_exists(self, mock_template_manager):
        """Test checking template existence."""
        assert mock_template_manager.template_exists("test") is False
        
        mock_template_manager.save_template("test", "ls -la")
        assert mock_template_manager.template_exists("test") is True


class TestContextManager:
    """Test suite for ContextManager."""
    
    def test_init(self):
        """Test ContextManager initialization."""
        manager = ContextManager()
        assert manager._context_cache == {}
    
    def test_get_current_directory(self, mock_context_manager):
        """Test getting current directory."""
        cwd = mock_context_manager.get_current_directory()
        assert isinstance(cwd, str)
        assert len(cwd) > 0
    
    def test_get_environment_context(self, mock_context_manager):
        """Test getting environment context."""
        context = mock_context_manager.get_environment_context()
        assert isinstance(context, dict)
        # Should have some environment variables
        assert "HOME" in context or "USER" in context
    
    def test_get_shell_context(self, mock_context_manager):
        """Test getting shell context."""
        context = mock_context_manager.get_shell_context()
        assert "shell" in context
        assert "shell_name" in context
    
    def test_build_context_string(self, mock_context_manager):
        """Test building context string."""
        context_str = mock_context_manager.build_context_string(include_git=False)
        assert isinstance(context_str, str)
        assert "Current directory:" in context_str
        assert "Shell:" in context_str
    
    def test_get_full_context(self, mock_context_manager):
        """Test getting full context."""
        context = mock_context_manager.get_full_context()
        assert "current_directory" in context
        assert "environment" in context
        assert "filesystem" in context
        assert "shell" in context


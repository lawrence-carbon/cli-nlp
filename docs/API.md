# API Reference

API documentation for QTC's Python modules.

## Table of Contents

- [CommandRunner](#commandrunner)
- [Managers](#managers)
- [Models](#models)
- [Utilities](#utilities)

## CommandRunner

### `CommandRunner`

Main class for command generation and execution.

```python
from cli_nlp.command_runner import CommandRunner
from cli_nlp.config_manager import ConfigManager
from cli_nlp.history_manager import HistoryManager
from cli_nlp.cache_manager import CacheManager
from cli_nlp.context_manager import ContextManager

runner = CommandRunner(
    config_manager=ConfigManager(),
    history_manager=HistoryManager(),
    cache_manager=CacheManager(),
    context_manager=ContextManager(),
)
```

#### Methods

##### `generate_command(query, model=None, temperature=None, max_tokens=None, use_cache=True)`

Generate a shell command from natural language query.

**Parameters:**
- `query` (str): Natural language query
- `model` (str, optional): LLM model to use
- `temperature` (float, optional): Generation temperature
- `max_tokens` (int, optional): Maximum tokens
- `use_cache` (bool): Whether to use cache (default: True)

**Returns:**
- `CommandResponse`: Command and safety information

**Raises:**
- `ValidationError`: If input validation fails
- `APIError`: If API call fails

**Example:**
```python
response = runner.generate_command("list python files")
print(response.command)  # "find . -name '*.py'"
print(response.is_safe)  # True
```

##### `run(query, execute=False, model=None, copy=False, force=False, refine=False, alternatives=False, edit=False, dry_run=False, output_json=False)`

Generate and optionally execute a command.

**Parameters:**
- `query` (str): Natural language query
- `execute` (bool): Whether to execute command
- `model` (str, optional): LLM model to use
- `copy` (bool): Copy to clipboard
- `force` (bool): Bypass safety checks
- `refine` (bool): Enter refinement mode
- `alternatives` (bool): Show alternatives
- `edit` (bool): Edit before execution
- `dry_run` (bool): Preview without executing
- `output_json` (bool): Output in JSON format

**Example:**
```python
runner.run("list files", execute=False, dry_run=True)
```

## Managers

### `ConfigManager`

Manages configuration with XDG-compliant storage.

```python
from cli_nlp.config_manager import ConfigManager

manager = ConfigManager()
```

#### Methods

- `load()`: Load configuration
- `save(config)`: Save configuration
- `get(key, default=None)`: Get config value
- `get_active_provider()`: Get active provider name
- `get_active_model()`: Get active model name
- `set_active_provider(provider)`: Set active provider
- `add_provider(name, api_key, models)`: Add provider
- `remove_provider(name)`: Remove provider

### `CacheManager`

Manages response caching.

```python
from cli_nlp.cache_manager import CacheManager

cache = CacheManager(ttl_seconds=86400)
```

#### Methods

- `get(query, model=None)`: Get cached response
- `set(query, response, model=None)`: Cache response
- `clear()`: Clear all cache
- `get_stats()`: Get cache statistics

### `HistoryManager`

Manages command history.

```python
from cli_nlp.history_manager import HistoryManager

history = HistoryManager()
```

#### Methods

- `add_entry(query, command, ...)`: Add history entry
- `get_all(limit=None)`: Get all entries
- `search(query)`: Search history
- `clear()`: Clear history

### `MetricsCollector`

Collects and reports metrics.

```python
from cli_nlp.metrics import MetricsCollector

collector = MetricsCollector()
```

#### Methods

- `record_query(cached, execution_time, provider, model)`: Record query
- `record_error(provider)`: Record error
- `record_command_execution(executed)`: Record execution
- `get_stats()`: Get statistics
- `get_provider_comparison()`: Get provider comparison
- `reset()`: Reset all metrics

## Models

### `CommandResponse`

Response model for generated commands.

```python
from cli_nlp.models import CommandResponse, SafetyLevel

response = CommandResponse(
    command="ls -la",
    is_safe=True,
    safety_level=SafetyLevel.SAFE,
    explanation="List files"
)
```

**Fields:**
- `command` (str): The shell command
- `is_safe` (bool): Whether command is safe
- `safety_level` (SafetyLevel): Safety level enum
- `explanation` (str, optional): Explanation

### `SafetyLevel`

Enum for command safety levels.

- `SAFE`: Read-only operations
- `MODIFYING`: Operations that modify system

## Utilities

### Logging

```python
from cli_nlp.logger import get_logger, setup_logging

# Setup logging
setup_logging(level="INFO", log_file=None, verbose=False)

# Get logger
logger = get_logger(__name__)
logger.info("Message")
```

### Validation

```python
from cli_nlp.validation import (
    validate_query,
    validate_model_name,
    validate_temperature,
    validate_max_tokens,
)

validate_query("list files")
validate_model_name("gpt-4o-mini")
validate_temperature(0.3)
validate_max_tokens(200)
```

### Retry Logic

```python
from cli_nlp.retry import RetryConfig, retry_with_backoff

config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=60.0,
)

@retry_with_backoff(config)
def api_call():
    # API call code
    pass
```

### Exceptions

```python
from cli_nlp.exceptions import (
    QTCError,
    ConfigurationError,
    APIError,
    CacheError,
    CommandExecutionError,
    ValidationError,
)

try:
    # Code
    pass
except APIError as e:
    print(f"API Error: {e.message}")
    print(f"Provider: {e.provider}")
```

## Examples

### Basic Usage

```python
from cli_nlp.command_runner import CommandRunner
from cli_nlp.config_manager import ConfigManager

config = ConfigManager()
runner = CommandRunner(config)

response = runner.generate_command("list python files")
print(response.command)
```

### With Custom Configuration

```python
from cli_nlp.command_runner import CommandRunner
from cli_nlp.config_manager import ConfigManager
from cli_nlp.cache_manager import CacheManager

config = ConfigManager()
cache = CacheManager(ttl_seconds=3600)  # 1 hour TTL
runner = CommandRunner(config, cache_manager=cache)

response = runner.generate_command("show disk usage", model="gpt-4o")
```

### Metrics Collection

```python
from cli_nlp.metrics import MetricsCollector

collector = MetricsCollector()
stats = collector.get_stats()
print(f"Total queries: {stats['total_queries']}")
print(f"Cache hit rate: {stats['cache_hit_rate']:.1%}")
```

### Error Handling

```python
from cli_nlp.command_runner import CommandRunner
from cli_nlp.exceptions import APIError, ValidationError

try:
    response = runner.generate_command("")
except ValidationError as e:
    print(f"Invalid input: {e.message}")
except APIError as e:
    print(f"API error: {e.message}")
    print(f"Provider: {e.provider}")
```

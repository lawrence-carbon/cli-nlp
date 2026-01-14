# Developer Guide

This guide is for developers who want to contribute to QTC or understand its internals.

## Table of Contents

- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Code Structure](#code-structure)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Adding New Features](#adding-new-features)
- [Code Style](#code-style)

## Getting Started

### Prerequisites

- Python 3.12+
- Poetry (for dependency management)
- Git

### Setup

1. Clone the repository:
```bash
git clone https://github.com/lawrence-carbon/cli-nlp.git
cd cli-nlp
```

2. Install dependencies:
```bash
poetry install
```

3. Run tests:
```bash
poetry run pytest
```

## Architecture

### Overview

QTC follows a modular architecture with clear separation of concerns:

```
cli_nlp/
├── cli.py              # CLI interface (Click commands)
├── command_runner.py  # Core command generation logic
├── config_manager.py  # Configuration management
├── cache_manager.py   # Response caching
├── history_manager.py  # Command history
├── context_manager.py  # Context building (Git, env, etc.)
├── template_manager.py # Command templates
├── provider_manager.py # LLM provider management
├── metrics.py         # Metrics collection
├── logger.py          # Structured logging
├── retry.py           # Retry logic
├── validation.py      # Input validation
├── exceptions.py       # Custom exceptions
└── models.py          # Pydantic models
```

### Key Components

#### CommandRunner

The core component that orchestrates command generation:
- Validates input
- Checks cache
- Builds context
- Calls LLM API
- Handles retries
- Records metrics

#### Managers

Each manager handles a specific concern:
- **ConfigManager**: XDG-compliant config storage
- **CacheManager**: Response caching with TTL
- **HistoryManager**: Command history tracking
- **ContextManager**: Builds context (Git, filesystem, env)
- **TemplateManager**: Command templates/aliases
- **ProviderManager**: LLM provider discovery

#### Metrics

Metrics are collected automatically:
- Query counts
- Cache hit rates
- API call counts
- Execution times
- Error rates
- Provider performance

## Code Structure

### Manager Pattern

All managers follow a consistent pattern:

```python
class SomeManager:
    def __init__(self):
        self.data_path = self._get_data_path()
        self._load_data()
    
    def _get_data_path(self) -> Path:
        # XDG-compliant path resolution
    
    def _load_data(self):
        # Load from disk
    
    def _save_data(self):
        # Save to disk (atomic writes)
```

### Error Handling

Custom exception hierarchy:

```python
QTCError (base)
├── ConfigurationError
├── APIError
├── CacheError
├── CommandExecutionError
└── ValidationError
```

### Logging

Structured logging with Rich:

```python
from cli_nlp.logger import get_logger

logger = get_logger(__name__)
logger.info("Message")
logger.error("Error", exc_info=True)
```

## Development Workflow

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=cli_nlp --cov-report=html

# Run specific test file
poetry run pytest tests/test_command_runner.py
```

### Code Quality

```bash
# Format code
poetry run black .

# Lint code
poetry run ruff check .
poetry run ruff check --fix .
```

### Adding a New Feature

1. Create a feature branch
2. Write tests first (TDD)
3. Implement the feature
4. Ensure tests pass
5. Update documentation
6. Submit PR

## Testing

### Test Structure

```
tests/
├── test_*.py          # Unit tests
├── integration/       # Integration tests
└── benchmarks/        # Performance benchmarks
```

### Writing Tests

```python
import pytest
from cli_nlp.command_runner import CommandRunner

def test_something(mock_config_manager):
    runner = CommandRunner(mock_config_manager)
    # Test code
```

### Fixtures

Common fixtures in `conftest.py`:
- `mock_config_manager`
- `mock_cache_manager`
- `mock_history_manager`
- `temp_dir`

## Adding New Features

### Adding a New CLI Flag

1. Add option to `cli()` function:
```python
@click.option("--new-flag", is_flag=True, help="Description")
```

2. Pass to `command_runner.run()`:
```python
command_runner.run(query, new_flag=new_flag)
```

3. Implement in `CommandRunner.run()`:
```python
def run(self, ..., new_flag: bool = False):
    if new_flag:
        # Handle flag
```

4. Add tests
5. Update documentation

### Adding a New Manager

1. Create `cli_nlp/new_manager.py`:
```python
from cli_nlp.logger import get_logger
from cli_nlp.exceptions import QTCError

logger = get_logger(__name__)

class NewManager:
    def __init__(self):
        self.data_path = self._get_data_path()
        self._load_data()
    
    def _get_data_path(self) -> Path:
        # XDG path resolution
    
    def _load_data(self):
        # Load logic
    
    def _save_data(self):
        # Atomic save logic
```

2. Add to CLI initialization
3. Add tests
4. Document usage

## Code Style

### Formatting

- Use Black (line length: 88)
- Target Python 3.12+

### Type Hints

Always use type hints:

```python
def function(param: str) -> int:
    return len(param)
```

### Docstrings

Google-style docstrings:

```python
def function(param: str) -> int:
    """
    Brief description.
    
    Args:
        param: Parameter description
    
    Returns:
        Return value description
    
    Raises:
        ValueError: When param is invalid
    """
```

### Error Handling

- Use custom exceptions
- Log errors appropriately
- Provide user-friendly messages
- Never expose internal details

## Common Tasks

### Debugging

Enable verbose logging:
```bash
qtc --verbose "your query"
```

Or debug mode:
```bash
qtc --debug "your query"
```

### Viewing Metrics

```bash
# Show metrics
qtc metrics show

# Show stats
qtc stats

# JSON output
qtc metrics show --json
```

### Testing Locally

```bash
# Install in development mode
poetry install

# Run CLI
poetry run qtc "your query"

# Run tests
poetry run pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Ensure all tests pass
6. Update documentation
7. Submit a PR

## Resources

- [Click Documentation](https://click.palletsprojects.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [LiteLLM Documentation](https://docs.litellm.ai/)

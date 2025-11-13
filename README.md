# QTC: Query to Command - Natural Language to Shell Command Converter

[![Tests](https://github.com/lawrence-carbon/cli-nlp/workflows/Tests/badge.svg)](https://github.com/lawrence-carbon/cli-nlp/actions)
[![codecov](https://codecov.io/gh/lawrence-carbon/cli-nlp/branch/master/graph/badge.svg)](https://codecov.io/gh/lawrence-carbon/cli-nlp)
[![PyPI version](https://badge.fury.io/py/query-to-command.svg)](https://badge.fury.io/py/query-to-command)
[![PyPI downloads](https://img.shields.io/pypi/dm/query-to-command.svg)](https://pypi.org/project/query-to-command/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)

A command-line utility that converts natural language requests into shell commands using OpenAI's API.

## Features

- 🚀 Convert natural language to shell commands
- ⚡ Fast responses using GPT-4o-mini (or any OpenAI model)
- 🔧 Execute commands directly with `--execute` flag
- 📋 Copy commands to clipboard with `--copy` flag
- ⚙️ JSON config file for API keys and customization
- 🎨 Beautiful CLI with Rich formatting (via Typer)
- 📦 Poetry-based dependency management
- 🎯 Simple and intuitive interface

## Installation

### Install from PyPI (Recommended)

```bash
pip install query-to-command
```

After installation, you can use the `qtc` command directly:

```bash
qtc "list all python files in current directory"
```

### Install from Source

### Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/docs/#installation) (recommended)

### Install with Poetry (Recommended)

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install dependencies and the CLI tool:**
   ```bash
   poetry install
   ```

3. **Activate the Poetry shell and use the tool:**
   ```bash
   poetry shell
   qtc "your query here"
   ```

   Or run directly without activating the shell:
   ```bash
   poetry run qtc "your query here"
   ```

### Project Structure

The project is organized into a clean, maintainable structure:

```
cli-nlp/
├── cli_nlp/
│   ├── __init__.py          # Package initialization
│   ├── cli.py               # Main CLI interface
│   ├── config_manager.py    # Configuration management
│   ├── command_runner.py    # Command generation and execution
│   └── utils.py             # Utility functions
├── pyproject.toml           # Poetry configuration
└── README.md                # This file
```

### Set up LLM Provider

**Option A: Interactive configuration (recommended):**
```bash
# Configure a provider interactively
qtc config providers set
# or: poetry run qtc config providers set

# This will guide you through:
# 1. Selecting a provider (OpenAI, Anthropic, Google, etc.)
# 2. Choosing a model
# 3. Entering your API key securely
```

**Option B: Using environment variables:**
```bash
# Set provider-specific environment variable
export OPENAI_API_KEY='your-api-key-here'
# or
export ANTHROPIC_API_KEY='your-api-key-here'
# etc.
```

Note: The config file takes precedence over environment variables.

## Usage

### Basic Usage

```bash
qtc "list all python files in current directory"
# Output: find . -name "*.py"
```

If using Poetry without installing globally:
```bash
poetry run qtc "list all python files in current directory"
```

### Interactive Mode with Tab Completion

When you run `qtc` without a query, it enters interactive mode with tab completion enabled:

```bash
qtc
Query: list files in /home/user/Documents<TAB>
```

**Tab completion features:**
- **File paths**: Tab-complete file and directory paths (e.g., `/home/user/`, `./`, `~/`)
- **Command names**: Tab-complete common command words and system commands
- **History**: Previous queries are saved and can be accessed with arrow keys
- **Bash-style completion**: Works just like bash completion for paths and commands

**Examples:**
```bash
# Interactive mode - press Tab to complete paths
qtc
Query: find all python files in ~/projects<TAB>

# Tab completion works for:
# - Absolute paths: /home/user/Documents<TAB>
# - Relative paths: ./src<TAB>
# - Home directory: ~/Documents<TAB>
# - Command names: git<TAB>, docker<TAB>
```

### Execute Command Directly

```bash
qtc "show disk usage" --execute
# Generates and executes: df -h
```

### Copy to Clipboard

```bash
qtc "find files larger than 100MB" --copy
# Generates command and copies it to clipboard
```

### Switch Active Model

```bash
qtc config model claude-3-opus-20240229
# Updates the active model used for all subsequent queries
```

### Combine Options

```bash
qtc "kill process on port 3000" --execute --force
```

## Examples

```bash
# File operations
qtc "find all .txt files modified today"
qtc "count lines in all python files"
qtc "delete all .pyc files recursively"

# System information
qtc "show disk usage"
qtc "list running processes"
qtc "show network connections"

# Git operations
qtc "show git status"
qtc "list all git branches"

# Process management
qtc "find process using port 8080"
qtc "kill all python processes"
```

## Configuration

The tool uses a JSON config file located at `~/.config/cli-nlp/config.json` (or `$XDG_CONFIG_HOME/cli-nlp/config.json`).

### Config File Structure

```json
{
  "providers": {
    "openai": {
      "api_key": "sk-your-api-key-here",
      "models": ["gpt-4o-mini", "gpt-4o"]
    },
    "anthropic": {
      "api_key": "sk-ant-your-api-key-here",
      "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"]
    }
  },
  "active_provider": "openai",
  "active_model": "gpt-4o-mini",
  "temperature": 0.3,
  "max_tokens": 200
}
```

### Creating Config File

The config file is created automatically when you configure your first provider:

```bash
qtc config providers set
```

This interactive command will:
- Create the config file if it doesn't exist
- Guide you through provider selection
- Help you choose a model
- Securely store your API key

The config file has restrictive permissions (600) to protect your API keys.

### Provider Management

Configure and manage multiple LLM providers:

```bash
# Configure a new provider interactively
qtc config providers set

# List all configured providers
qtc config providers list

# Show active provider
qtc config providers show

# Switch active provider
qtc config providers switch openai

# Remove a provider
qtc config providers remove anthropic
```

### Config Options

- `providers`: Dictionary of provider configurations (each with `api_key` and `models`)
- `active_provider`: Currently active provider name
- `active_model`: Currently active model string
- `temperature`: Temperature for command generation (default: 0.3)
- `max_tokens`: Maximum tokens for response (default: 200)

### Supported Providers

The tool supports 100+ LLM providers through LiteLLM, including:
- OpenAI (GPT-4, GPT-3.5, etc.)
- Anthropic (Claude 3)
- Google (Gemini)
- Cohere
- Mistral
- Azure OpenAI
- AWS Bedrock
- Ollama (local models)
- And many more...

Run `qtc config providers set` to see all available providers.

## Options

- `--execute, -e`: Execute the generated command automatically
- `--force, -f`: Bypass safety check for modifying commands (use with caution)
- `--copy, -c`: Copy command to clipboard (requires xclip or xsel)
- `config providers`: Manage LLM provider configurations (subcommand)
- `--help, -h`: Show help message

## Safety Features

The tool includes built-in safety checks to protect your system:

- **Automatic Safety Analysis**: Every generated command is analyzed to determine if it will modify your system or only read/display information
- **Visual Warnings**: Commands that modify the system are displayed with a yellow warning panel
- **Execution Protection**: Modifying commands cannot be executed with `--execute` unless you use the `--force` flag
- **Safety Levels**:
  - **Safe (Green)**: Read-only operations (listing files, showing status, etc.)
  - **Modifying (Yellow)**: Operations that alter system state (writing files, changing config, etc.)

### Example Safety Warnings

```bash
# Safe command (read-only)
qtc "list all python files"
# Shows: Generated Command (Safe - Read Only)

# Modifying command (requires --force to execute)
qtc "delete all .pyc files" --execute
# Shows: ⚠️ Safety Check Failed: This command will modify your system!
#        Use --force flag to execute modifying commands.

qtc "delete all .pyc files" --execute --force
# Executes the command after bypassing safety check
```

## Requirements

- Python 3.12+
- Poetry (required for installation)
- LLM provider API key (OpenAI, Anthropic, Google, etc.)
- (Optional) xclip or xsel for clipboard functionality

## Development

### Setup Development Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/lawrence-carbon/cli-nlp.git
   cd cli-nlp
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Activate the virtual environment**:
   ```bash
   poetry shell
   ```

4. **Run tests**:
   ```bash
   poetry run pytest
   ```

5. **Run tests with coverage**:
   ```bash
   poetry run pytest --cov=cli_nlp --cov-report=html
   ```

6. **Format code**:
   ```bash
   poetry run black .
   ```

7. **Lint code**:
   ```bash
   poetry run ruff check .
   poetry run ruff check --fix .  # Auto-fix issues
   ```

### Project Structure

The codebase is organized into modular classes:

- **ConfigManager** (`config_manager.py`): Handles configuration file operations (loading, saving, multi-provider API key management)
- **CommandRunner** (`command_runner.py`): Handles command generation using LiteLLM with safety analysis and command execution
- **ProviderManager** (`provider_manager.py`): Provider and model discovery utilities
- **Models** (`models.py`): Pydantic models for structured LLM responses (CommandResponse with safety information)
- **CLI** (`cli.py`): Main interface using Click for argument parsing and command routing
- **Utils** (`utils.py`): Utility functions (help text, clipboard operations)

This structure makes the code maintainable and easy to extend.

### Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- 📝 [Contributing Guidelines](CONTRIBUTING.md)
- 📋 [Code of Conduct](CODE_OF_CONDUCT.md)
- 🔒 [Security Policy](SECURITY.md)
- 📜 [Changelog](CHANGELOG.md)

## Notes

- The tool uses LiteLLM to support 100+ LLM providers
- Default model is gpt-4o-mini (cost-efficient) but can be changed via config
- Commands are generated based on standard Unix/Linux commands
- **Safety First**: The tool automatically analyzes commands and warns you about modifying operations
- Always review generated commands before executing, especially for destructive operations
- Use `--force` flag only when you're certain the command is safe to execute
- API key priority: config file > environment variable
- The config file is automatically created with secure permissions (600)
- Old config files are automatically migrated to the new multi-provider format

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


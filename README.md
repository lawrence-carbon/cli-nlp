# QTC: Query to Command - Natural Language to Shell Command Converter

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

### Set up OpenAI API key

**Option A: Using config file (recommended):**
```bash
# Create config file template
qtc init-config
# or: poetry run qtc init-config

# Edit the config file and add your API key
# Location: ~/.config/cli-nlp/config.json
nano ~/.config/cli-nlp/config.json
```

**Option B: Using environment variable:**
```bash
export OPENAI_API_KEY='your-api-key-here'
```

Or add it to your `~/.zshrc` or `~/.bashrc`:
```bash
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
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

### Use Different Model

```bash
qtc "complex query" --model gpt-4o
```

### Combine Options

```bash
qtc "kill process on port 3000" --execute --model gpt-4o-mini
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
  "openai_api_key": "your-api-key-here",
  "default_model": "gpt-4o-mini",
  "temperature": 0.3,
  "max_tokens": 200
}
```

### Creating Config File

```bash
qtc init-config
# or: poetry run qtc init-config
```

This creates a template config file that you can edit. The config file has restrictive permissions (600) to protect your API key.

### Config Options

- `openai_api_key`: Your OpenAI API key (required)
- `default_model`: Default model to use (default: "gpt-4o-mini")
- `temperature`: Temperature for command generation (default: 0.3)
- `max_tokens`: Maximum tokens for response (default: 200)

## Options

- `--execute, -e`: Execute the generated command automatically
- `--force, -f`: Bypass safety check for modifying commands (use with caution)
- `--model MODEL, -m MODEL`: Specify OpenAI model (overrides config default)
- `--copy, -c`: Copy command to clipboard (requires xclip or xsel)
- `init-config`: Create a default config file template (subcommand)
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
- OpenAI API key
- (Optional) xclip or xsel for clipboard functionality

## Development

The codebase is organized into modular classes:

- **ConfigManager** (`config_manager.py`): Handles configuration file operations (loading, saving, API key management)
- **CommandRunner** (`command_runner.py`): Handles command generation using OpenAI with safety analysis and command execution
- **Models** (`models.py`): Pydantic models for structured LLM responses (CommandResponse with safety information)
- **CLI** (`cli.py`): Main interface using Typer for argument parsing and command routing
- **Utils** (`utils.py`): Utility functions (help text, clipboard operations)

This structure makes the code maintainable and easy to extend.

## Notes

- The tool uses GPT-4o-mini by default for cost efficiency
- Commands are generated based on standard Unix/Linux commands
- **Safety First**: The tool automatically analyzes commands and warns you about modifying operations
- Always review generated commands before executing, especially for destructive operations
- Use `--force` flag only when you're certain the command is safe to execute
- API key priority: config file > environment variable
- The config file is automatically created with secure permissions (600)

## License

MIT


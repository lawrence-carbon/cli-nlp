# CLI-NLP: Natural Language to Shell Command Converter

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
   nlp "your query here"
   ```

   Or run directly without activating the shell:
   ```bash
   poetry run nlp "your query here"
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
nlp init-config
# or: poetry run nlp init-config

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
nlp "list all python files in current directory"
# Output: find . -name "*.py"
```

If using Poetry without installing globally:
```bash
poetry run nlp "list all python files in current directory"
```

### Execute Command Directly

```bash
nlp "show disk usage" --execute
# Generates and executes: df -h
```

### Copy to Clipboard

```bash
nlp "find files larger than 100MB" --copy
# Generates command and copies it to clipboard
```

### Use Different Model

```bash
nlp "complex query" --model gpt-4o
```

### Combine Options

```bash
nlp "kill process on port 3000" --execute --model gpt-4o-mini
```

## Examples

```bash
# File operations
nlp "find all .txt files modified today"
nlp "count lines in all python files"
nlp "delete all .pyc files recursively"

# System information
nlp "show disk usage"
nlp "list running processes"
nlp "show network connections"

# Git operations
nlp "show git status"
nlp "list all git branches"

# Process management
nlp "find process using port 8080"
nlp "kill all python processes"
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
nlp init-config
# or: poetry run nlp init-config
```

This creates a template config file that you can edit. The config file has restrictive permissions (600) to protect your API key.

### Config Options

- `openai_api_key`: Your OpenAI API key (required)
- `default_model`: Default model to use (default: "gpt-4o-mini")
- `temperature`: Temperature for command generation (default: 0.3)
- `max_tokens`: Maximum tokens for response (default: 200)

## Options

- `--execute, -e`: Execute the generated command automatically
- `--model MODEL, -m MODEL`: Specify OpenAI model (overrides config default)
- `--copy, -c`: Copy command to clipboard (requires xclip or xsel)
- `init-config`: Create a default config file template (subcommand)
- `--help, -h`: Show help message

## Requirements

- Python 3.12+
- Poetry (required for installation)
- OpenAI API key
- (Optional) xclip or xsel for clipboard functionality

## Development

The codebase is organized into modular classes:

- **ConfigManager**: Handles configuration file operations (loading, saving, API key management)
- **CommandRunner**: Handles command generation using OpenAI and command execution
- **CLI**: Main interface using Typer for argument parsing and command routing

This structure makes the code maintainable and easy to extend.

## Notes

- The tool uses GPT-4o-mini by default for cost efficiency
- Commands are generated based on standard Unix/Linux commands
- Always review generated commands before executing, especially for destructive operations
- API key priority: config file > environment variable
- The config file is automatically created with secure permissions (600)

## License

MIT


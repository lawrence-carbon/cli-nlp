# CLI Feature Suggestions

## Overview
Feature suggestions for enhancing the CLI-NLP (qtc) tool, organized by category and priority. These suggestions aim to improve usability, efficiency, and functionality.

## High Priority Features

### 1. Command History Management
**Files to modify:** `cli_nlp/cli.py`, `cli_nlp/command_runner.py`, new `cli_nlp/history_manager.py`

- **View history**: `qtc history` - List recent queries and generated commands
- **Search history**: `qtc history --search "python"` - Search past queries
- **Re-execute from history**: `qtc history --execute 5` - Re-run command from history by ID
- **Export/import**: `qtc history --export` - Export history to JSON/CSV
- Store both query and generated command with timestamps and safety level

### 2. Command Refinement/Editing
**Files to modify:** `cli_nlp/cli.py`, `cli_nlp/command_runner.py`

- **Edit before execution**: After generation, allow editing the command in an editor
- **Refine command**: `qtc "query" --refine` - Ask follow-up questions to improve command
- **Multi-step refinement**: Interactive mode to iteratively improve commands
- **Command alternatives**: Show 2-3 alternative command options

### 3. Command Caching
**Files to modify:** `cli_nlp/command_runner.py`, new `cli_nlp/cache_manager.py`

- Cache generated commands for identical queries (hash-based)
- Reduce API calls for repeated queries
- Configurable cache TTL
- `qtc cache --clear` - Clear command cache
- `qtc cache --stats` - Show cache hit/miss statistics

### 4. Multi-Command Support
**Files to modify:** `cli_nlp/command_runner.py`, `cli_nlp/models.py`

- **Command chaining**: `qtc "list files and then count lines"` - Generate multiple commands
- **Pipeline support**: Support for pipes and command sequences
- **Batch mode**: `qtc --batch queries.txt` - Process multiple queries from file
- Return structured response with multiple commands

## Medium Priority Features

### 5. Context Awareness
**Files to modify:** `cli_nlp/command_runner.py`, new `cli_nlp/context_manager.py`

- **Current directory context**: Include pwd in prompt
- **Git context**: Detect git repo and include git status in context
- **Environment context**: Include relevant env vars (e.g., $VIRTUAL_ENV)
- **Shell history integration**: Learn from user's actual shell history
- **File system context**: Understand current working directory structure

### 6. Command Templates/Aliases
**Files to modify:** `cli_nlp/config_manager.py`, `cli_nlp/cli.py`

- **Save templates**: `qtc template save "clean-pyc" "find . -name '*.pyc' -delete"`
- **Use templates**: `qtc template use "clean-pyc"`
- **List templates**: `qtc template list`
- Store in config file or separate templates.json

### 7. Enhanced Safety Features
**Files to modify:** `cli_nlp/command_runner.py`, `cli_nlp/models.py`

- **Dry-run mode**: `qtc "query" --dry-run` - Show what would happen without executing
- **Confirmation prompts**: Interactive confirmation for modifying commands
- **Safety whitelist/blacklist**: User-defined safe/dangerous command patterns
- **Command validation**: Pre-validate commands before execution (syntax checking)

### 8. Multi-Provider Support
**Files to modify:** `cli_nlp/command_runner.py`, `cli_nlp/config_manager.py`

- Support for Anthropic Claude, Google Gemini, local LLMs (via Ollama)
- Provider abstraction layer
- `qtc --provider anthropic` or configure in config.json
- Fallback mechanism if primary provider fails

### 9. Command Explanation Mode
**Files to modify:** `cli_nlp/command_runner.py`, `cli_nlp/cli.py`

- **Learn mode**: `qtc "query" --explain` - Detailed explanation of each part
- **Step-by-step breakdown**: Explain flags, options, and command structure
- **Educational output**: Help users learn shell commands
- **Interactive Q&A**: Answer follow-up questions about the command

### 10. Integration Features
**Files to modify:** `cli_nlp/cli.py`, new integration modules

- **Git integration**: `qtc git "query"` - Git-specific command generation
- **Docker integration**: `qtc docker "query"` - Docker-specific commands
- **Package manager shortcuts**: Quick commands for npm, pip, poetry, etc.
- **Tool-specific context**: Better understanding of tool-specific workflows

## Lower Priority Features

### 11. Undo/Redo Functionality
**Files to modify:** `cli_nlp/command_runner.py`, new `cli_nlp/undo_manager.py`

- Track executed commands and their effects
- `qtc undo` - Attempt to reverse last modifying command
- Store command metadata for undo operations
- Limited to file operations (create/delete/move)

### 12. Command Suggestions
**Files to modify:** `cli_nlp/completer.py`, `cli_nlp/command_runner.py`

- **Smart suggestions**: Based on current directory and context
- **Query completion**: Suggest common queries based on history
- **Command prediction**: Suggest likely next commands

### 13. Output Formatting
**Files to modify:** `cli_nlp/command_runner.py`, `cli_nlp/utils.py`

- **JSON output**: `qtc "query" --json` - Machine-readable output
- **Markdown output**: `qtc "query" --markdown` - Formatted markdown
- **Export formats**: Export commands to scripts, aliases, or configs

### 14. Performance Optimizations
**Files to modify:** `cli_nlp/command_runner.py`

- **Streaming responses**: Show command as it's generated
- **Parallel processing**: For batch operations
- **Rate limiting**: Respect API rate limits
- **Retry logic**: Automatic retry on API failures

### 15. Shell-Specific Support
**Files to modify:** `cli_nlp/command_runner.py`, `cli_nlp/config_manager.py`

- **Shell detection**: Auto-detect user's shell (bash, zsh, fish)
- **Shell-specific commands**: Generate commands appropriate for detected shell
- **Shell config integration**: Generate aliases/functions for user's shell

### 16. Interactive Command Builder
**Files to modify:** `cli_nlp/cli.py`, new `cli_nlp/builder.py`

- **Wizard mode**: `qtc --wizard` - Step-by-step command building
- **Guided queries**: Ask clarifying questions before generating
- **Parameter prompts**: Interactive prompts for command parameters

### 17. Statistics and Analytics
**Files to modify:** `cli_nlp/cli.py`, new `cli_nlp/stats.py`

- **Usage stats**: `qtc stats` - Show command usage statistics
- **Most used queries**: Track popular queries
- **Time saved**: Estimate time saved vs manual command writing
- **API usage**: Track API calls and costs

### 18. Configuration Enhancements
**Files to modify:** `cli_nlp/config_manager.py`, `cli_nlp/cli.py`

- **Config validation**: Validate config file on load
- **Config editor**: `qtc config edit` - Open config in editor
- **Config migration**: Auto-migrate config on version updates
- **Multiple profiles**: Support for different config profiles

### 19. Testing and Validation
**Files to modify:** `cli_nlp/command_runner.py`

- **Command syntax validation**: Validate before execution
- **Test mode**: Test commands in sandbox environment
- **Command preview**: Show expected output without executing

### 20. Documentation and Help
**Files to modify:** `cli_nlp/utils.py`, `cli_nlp/cli.py`

- **Interactive help**: `qtc help <topic>` - Contextual help
- **Examples database**: `qtc examples` - Browse example queries
- **Command reference**: Built-in command reference guide
- **Tutorial mode**: Guided tutorial for new users

## Implementation Notes

- Most features can be added incrementally without breaking existing functionality
- Consider creating a plugin system for extensibility (integration features)
- Use dependency injection for provider abstraction
- Store history/cache in XDG-compliant directories
- Maintain backward compatibility with existing config format
- Add comprehensive tests for new features
- Update README.md with new feature documentation

## Priority Ranking

1. **Command History Management** - High user value, moderate complexity
2. **Command Caching** - High efficiency gain, low complexity
3. **Command Refinement** - High user value, moderate complexity
4. **Context Awareness** - Medium value, moderate complexity
5. **Multi-Command Support** - Medium value, high complexity
6. **Command Templates** - Medium value, low complexity
7. **Multi-Provider Support** - Medium value, high complexity
8. **Enhanced Safety** - High value, moderate complexity
9. **Command Explanation** - Medium value, low complexity
10. **Integration Features** - Medium value, high complexity


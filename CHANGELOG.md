# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2025-11-14

### Changed
- **Removed `--model` CLI option**: Queries now always use the active provider/model configured via `qtc config`, simplifying the command surface and avoiding per-invocation overrides.
- **Removed `init-config` command**: The `init-config` command has been removed as it's redundant. The `config providers set` command now automatically creates the config file if it doesn't exist, providing a better interactive onboarding experience.
- **Enhanced onboarding**: Fresh installations now show a welcoming message guiding users to run `qtc config providers set` for initial setup.

### Added
- Test coverage badge in README
- License file (MIT)
- Contributing guidelines
- Code of Conduct
- Security policy
- GitHub issue and PR templates
- Code quality CI workflow (linting/formatting)
- Ruff and Black configuration

## [0.3.1] - 2025-11-12

### Added
- Comprehensive test suite with 94 passing tests
- 68% code coverage with comprehensive mocking of all LLM/OpenAI API calls
- Unit tests for all core components:
  - `CommandRunner` with mocked LLM interactions
  - All managers (`ConfigManager`, `CacheManager`, `HistoryManager`, `TemplateManager`, `ContextManager`)
  - CLI commands and subcommands
  - Pydantic models
- Tests run automatically on every push and pull request via GitHub Actions
- Test status badge in README

### Changed
- Removed Typer, now uses native Click
- Builds are blocked if tests fail, ensuring code quality

### Fixed
- Fixed missing dependency: Added `rich` package to dependencies (was causing import errors)
- Fixed GitHub Actions: Removed Poetry cache from setup-python step (Poetry is installed later)

### Documentation
- Added badges to README for tests, PyPI version, and Python version
- Updated `.gitignore` to exclude test artifacts

## [0.3.0] - 2025-11-12

### Added
- **Command History Management**:
  - View history: `qtc history list` - Browse recent queries and generated commands
  - Search history: `qtc history search <query>` - Find past commands by query or command text
  - Re-execute: `qtc history execute <id>` - Re-run commands from history
  - Export: `qtc history export` - Export history to JSON or CSV format
  - Clear: `qtc history clear` - Clear all history entries
- **Command Caching**:
  - Automatic caching of generated commands to reduce API calls
  - Cache statistics: `qtc cache stats` - View hit rates and performance metrics
  - Cache management: `qtc cache clear` - Clear cached commands
  - Configurable TTL (default: 24 hours)
- **Command Refinement & Editing**:
  - Refinement mode: `qtc --refine` - Iteratively improve commands with follow-up questions
  - Alternatives: `qtc --alternatives` - View 2-3 alternative command options
  - Edit mode: `qtc --edit` - Edit commands in your default editor before execution
- **Multi-Command Support**:
  - Automatic detection of multi-step queries (e.g., "list files and then count lines")
  - Support for command chaining (`&&`), pipelines (`|`), and parallel execution (`&`)
  - Batch mode: `qtc batch <file>` - Process multiple queries from a file
  - Detailed breakdown of multi-command sequences
- **Context Awareness**:
  - Git repository context detection (branch, status, remotes)
  - Environment variable awareness (virtual environments, shell type)
  - Filesystem context (current directory structure)
  - Automatic inclusion of context in command generation for better accuracy
- **Command Templates/Aliases**:
  - Save templates: `qtc template save <name> <command>` - Save frequently used commands
  - List templates: `qtc template list` - View all saved templates
  - Use templates: `qtc template use <name>` - Execute saved templates
  - Delete templates: `qtc template delete <name>` - Remove templates

### Changed
- Enhanced help text with comprehensive documentation of all new features
- Better error handling and user feedback
- Improved command safety analysis
- XDG-compliant data directory usage for history and cache

### Technical Changes
- New modules: `history_manager.py`, `cache_manager.py`, `context_manager.py`, `template_manager.py`
- Extended `models.py` with `MultiCommandResponse` for complex queries
- Enhanced `command_runner.py` with new capabilities
- Improved CLI interface with subcommand groups
- 1,758+ lines of new code

## [0.2.0] - 2025-11-11

### Added
- Initial PyPI release
- Convert natural language to shell commands
- Fast responses using GPT-4o-mini (or any OpenAI model)
- Execute commands directly with `--execute` flag
- Copy commands to clipboard with `--copy` flag
- JSON config file for API keys and customization
- Beautiful CLI with Rich formatting
- Safety checks for modifying commands
- Interactive mode with tab completion for paths and commands
- Basic command generation
- Configuration management

[Unreleased]: https://github.com/lawrence-carbon/cli-nlp/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/lawrence-carbon/cli-nlp/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/lawrence-carbon/cli-nlp/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/lawrence-carbon/cli-nlp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/lawrence-carbon/cli-nlp/releases/tag/v0.2.0


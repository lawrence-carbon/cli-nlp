# Product Brief: QTC (Query to Command)

**Version:** 0.4.0  
**Date:** 2025-01-27  
**Status:** Active Development  
**License:** MIT

---

## Executive Summary

**QTC (Query to Command)** is a command-line utility that converts natural language requests into shell commands using Large Language Models (LLMs). The tool bridges the gap between human intent and shell command syntax, making command-line operations more accessible while maintaining the power and flexibility of traditional CLI tools.

### Key Value Propositions

- **Accessibility**: Convert natural language to shell commands without memorizing syntax
- **Efficiency**: Reduce time spent searching for correct command syntax
- **Safety**: Built-in safety analysis prevents accidental system modifications
- **Flexibility**: Support for 100+ LLM providers via LiteLLM
- **Productivity**: History, caching, and templates for repeated workflows

---

## Problem Statement

### The Problem

Command-line interfaces are powerful but have a steep learning curve. Users often:
- Forget exact command syntax and flags
- Spend time searching documentation or Stack Overflow
- Make mistakes that could modify or damage their system
- Struggle with complex command chaining and pipelines
- Repeat the same queries multiple times, wasting API calls

### Target Users

1. **Developers**: Need quick command generation without context switching
2. **DevOps Engineers**: Require accurate commands for system administration
3. **Data Scientists**: Need shell commands for file operations and data processing
4. **Power Users**: Want to leverage CLI power without syntax memorization
5. **Beginners**: Learning shell commands through natural language interaction

### Market Opportunity

- Growing adoption of CLI tools in development workflows
- Increasing demand for AI-assisted productivity tools
- Large community of developers using shell commands daily
- Opportunity to reduce learning curve for new CLI users

---

## Product Features

### Core Features (Implemented)

#### 1. Natural Language to Command Conversion
- Convert plain English queries to shell commands
- Support for complex multi-step operations
- Automatic detection of command chaining (`&&`), pipelines (`|`), and parallel execution (`&`)
- Interactive mode with tab completion for paths and commands

#### 2. Multi-Provider LLM Support
- Support for 100+ LLM providers via LiteLLM
- Providers include: OpenAI, Anthropic Claude, Google Gemini, Cohere, Mistral, Azure OpenAI, AWS Bedrock, Ollama (local models)
- Easy provider switching and configuration
- Interactive provider setup with secure API key storage

#### 3. Safety Features
- Automatic safety analysis of generated commands
- Visual warnings for modifying commands (yellow panels)
- Execution protection requiring `--force` flag for modifying operations
- Safety levels: Safe (read-only) vs. Modifying (system-altering)

#### 4. Command History Management
- Persistent history of queries and generated commands
- Search functionality across history
- Re-execute commands from history by ID
- Export history to JSON or CSV format
- XDG-compliant storage (`~/.local/share/cli-nlp/`)

#### 5. Command Caching
- Automatic caching of generated commands
- Hash-based cache keys for identical queries
- Configurable TTL (default: 24 hours)
- Cache statistics (hit rates, performance metrics)
- Reduces API calls and costs

#### 6. Command Refinement & Editing
- Refinement mode (`--refine`) for iterative improvement
- Alternative command suggestions (`--alternatives`)
- Edit mode (`--edit`) to modify commands before execution
- Interactive follow-up questions

#### 7. Context Awareness
- Git repository context detection (branch, status, remotes)
- Environment variable awareness (virtual environments, shell type)
- Filesystem context (current directory structure)
- Automatic context inclusion in command generation

#### 8. Command Templates/Aliases
- Save frequently used commands as templates
- List, use, and delete templates
- Quick access to common workflows
- Stored in XDG-compliant config directory

#### 9. Batch Processing
- Process multiple queries from a file
- One query per line format
- Efficient batch API calls

#### 10. Rich CLI Experience
- Beautiful formatting with Rich library
- Color-coded safety indicators
- Interactive prompts with tab completion
- Clear error messages and help text

### Planned Features (Roadmap)

#### High Priority
- Enhanced safety features (dry-run mode, confirmation prompts)
- Command explanation mode (`--explain`) for educational purposes
- Shell-specific command generation (bash, zsh, fish)
- Command syntax validation before execution

#### Medium Priority
- Git integration (`qtc git "query"`)
- Docker integration (`qtc docker "query"`)
- Package manager shortcuts (npm, pip, poetry)
- Undo/redo functionality for file operations

#### Lower Priority
- Statistics and analytics dashboard
- Plugin system for extensibility
- Shell config integration (aliases/functions)
- Interactive command builder wizard

---

## Technical Architecture

### Technology Stack

- **Language**: Python 3.12+
- **Package Manager**: Poetry
- **CLI Framework**: Click
- **LLM Integration**: LiteLLM (100+ provider support)
- **Data Models**: Pydantic v2
- **Formatting**: Rich
- **Testing**: pytest with pytest-mock and pytest-cov
- **Code Quality**: Black (formatting), Ruff (linting)

### Architecture Components

```
cli_nlp/
├── cli.py                 # Main CLI interface (Click)
├── command_runner.py       # Command generation & execution
├── config_manager.py       # Configuration management
├── provider_manager.py     # Provider & model discovery
├── cache_manager.py        # Command caching
├── history_manager.py      # Command history
├── context_manager.py      # Context awareness
├── template_manager.py     # Command templates
├── completer.py           # Tab completion
├── models.py              # Pydantic data models
└── utils.py               # Utility functions
```

### Key Design Patterns

- **Manager Pattern**: Separate managers for different concerns (config, cache, history, etc.)
- **XDG Compliance**: Uses XDG directories for config, data, and cache
- **Provider Abstraction**: LiteLLM provides unified interface to multiple LLM providers
- **Safety-First**: Built-in safety analysis before command execution
- **Modular Design**: Each feature is self-contained and testable

### Data Storage

- **Config**: `~/.config/cli-nlp/config.json` (or `$XDG_CONFIG_HOME/cli-nlp/`)
- **Data**: `~/.local/share/cli-nlp/` (history, templates)
- **Cache**: `~/.cache/cli-nlp/` (command cache)
- **Permissions**: Config files use 600 permissions for security

---

## User Experience

### Primary Use Cases

1. **Quick Command Generation**
   ```bash
   qtc "list all python files modified today"
   # Output: find . -name "*.py" -mtime -1
   ```

2. **Safe Command Execution**
   ```bash
   qtc "show disk usage" --execute
   # Automatically executes: df -h
   ```

3. **Command Refinement**
   ```bash
   qtc "find python files" --refine
   # Interactive refinement with follow-up questions
   ```

4. **History Management**
   ```bash
   qtc history list
   qtc history search "python"
   qtc history execute 5
   ```

5. **Template Usage**
   ```bash
   qtc template save "clean-pyc" "find . -name '*.pyc' -delete"
   qtc template use "clean-pyc" --execute
   ```

### User Journey

1. **Installation**: `pip install query-to-command` or `poetry install`
2. **Configuration**: `qtc config providers set` (interactive setup)
3. **First Use**: `qtc "your query here"`
4. **Advanced Usage**: History, templates, refinement, batch processing
5. **Optimization**: Caching reduces API calls, templates speed up workflows

---

## Success Metrics

### Key Performance Indicators (KPIs)

1. **Adoption Metrics**
   - PyPI downloads (currently tracked)
   - GitHub stars and forks
   - Active users (via telemetry, if implemented)

2. **Usage Metrics**
   - Commands generated per user
   - Cache hit rate (target: >50%)
   - Average queries per session
   - Most common query types

3. **Quality Metrics**
   - Command accuracy rate (user feedback)
   - Safety check effectiveness
   - API call reduction via caching
   - Test coverage (currently 80%+)

4. **Performance Metrics**
   - Average response time
   - API call costs per user
   - Cache performance impact

### Success Criteria

- **Short-term (3 months)**:
  - 1,000+ PyPI downloads
  - 100+ GitHub stars
  - 80%+ test coverage maintained
  - Zero critical security issues

- **Medium-term (6 months)**:
  - 5,000+ PyPI downloads
  - Active community contributions
  - Plugin system implemented
  - Integration with popular tools (Git, Docker)

- **Long-term (12 months)**:
  - 20,000+ PyPI downloads
  - Featured in developer tool lists
  - Enterprise adoption
  - Self-sustaining community

---

## Competitive Analysis

### Direct Competitors

1. **ShellGPT** / **Aider**: AI-powered CLI assistants
   - **Differentiator**: QTC focuses specifically on command generation, not code editing
   - **Advantage**: Simpler interface, better safety features, multi-provider support

2. **GitHub Copilot CLI**: Command generation via GitHub Copilot
   - **Differentiator**: QTC is provider-agnostic, supports local models (Ollama)
   - **Advantage**: No vendor lock-in, more flexible pricing

3. **Cheat.sh**: Command-line cheat sheets
   - **Differentiator**: QTC generates commands dynamically, not static examples
   - **Advantage**: Context-aware, learns from user patterns

### Indirect Competitors

- **Man pages**: Traditional documentation
- **Stack Overflow**: Community-driven solutions
- **Command-line tutorials**: Educational resources

### Competitive Advantages

1. **Multi-Provider Support**: Not locked to a single LLM provider
2. **Safety-First Design**: Built-in safety analysis prevents accidents
3. **Productivity Features**: History, caching, templates reduce friction
4. **Open Source**: MIT license, community-driven development
5. **Extensibility**: Plugin system planned for custom integrations

---

## Business Model

### Current Model

- **Open Source**: MIT License
- **Free to Use**: No cost for end users
- **Self-Hosted**: Users provide their own API keys
- **Community-Driven**: Open source development model

### Potential Revenue Streams (Future)

1. **Enterprise Features**: Advanced features for teams/organizations
   - Team templates and shared history
   - Usage analytics and reporting
   - Priority support

2. **Hosted Service**: Managed API service
   - Pre-configured providers
   - Usage-based pricing
   - No API key management required

3. **Professional Services**: Consulting and customization
   - Custom integrations
   - Training and workshops
   - Enterprise deployments

### Cost Structure

- **Development**: Volunteer contributors + maintainer time
- **Infrastructure**: GitHub Actions (CI/CD), PyPI hosting (free)
- **API Costs**: Users bear their own LLM API costs
- **Maintenance**: Community-driven with maintainer oversight

---

## Risks and Mitigation

### Technical Risks

1. **LLM API Reliability**
   - **Risk**: API outages or rate limits
   - **Mitigation**: Multi-provider support, caching, retry logic

2. **Command Accuracy**
   - **Risk**: Incorrect commands could damage systems
   - **Mitigation**: Safety analysis, visual warnings, `--force` requirement

3. **API Cost Escalation**
   - **Risk**: Users face high API costs
   - **Mitigation**: Caching, local model support (Ollama), cost tracking

### Business Risks

1. **Competition from Big Tech**
   - **Risk**: Large companies build similar tools
   - **Mitigation**: Focus on open source, community, extensibility

2. **Adoption Challenges**
   - **Risk**: Users prefer traditional methods
   - **Mitigation**: Education, examples, ease of use

3. **Maintenance Burden**
   - **Risk**: Project becomes unmaintained
   - **Mitigation**: Clear contribution guidelines, multiple maintainers

### Security Risks

1. **API Key Exposure**
   - **Risk**: Config files with API keys could be exposed
   - **Mitigation**: 600 file permissions, secure storage, env var support

2. **Command Injection**
   - **Risk**: Malicious commands executed
   - **Mitigation**: Safety analysis, user confirmation, sandboxing (future)

3. **Supply Chain Attacks**
   - **Risk**: Compromised dependencies
   - **Mitigation**: Dependency scanning, pinned versions, security audits

---

## Roadmap

### Version 0.5.0 (Next Release)

- Enhanced safety features (dry-run, confirmation prompts)
- Command explanation mode (`--explain`)
- Shell-specific command generation
- Improved error handling and user feedback

### Version 0.6.0 (Future)

- Git integration (`qtc git`)
- Docker integration (`qtc docker`)
- Plugin system architecture
- Enhanced analytics and statistics

### Version 1.0.0 (Future)

- Stable API
- Comprehensive documentation
- Enterprise features
- Self-hosted option

---

## Conclusion

QTC fills a critical gap in the developer toolchain by making command-line interfaces more accessible through natural language processing. With its safety-first design, multi-provider support, and productivity features, QTC is positioned to become an essential tool for developers, DevOps engineers, and power users.

The open-source model, combined with a clear roadmap and strong technical foundation, provides a sustainable path for growth and community adoption.

---

## Appendix

### Resources

- **GitHub**: https://github.com/lawrence-carbon/cli-nlp
- **PyPI**: https://pypi.org/project/query-to-command/
- **Documentation**: README.md, CONTRIBUTING.md, CHANGELOG.md
- **License**: MIT (see LICENSE file)

### Contact

- **Maintainer**: Lawrence Carbon
- **Email**: lawrence.carbon@gmail.com
- **GitHub**: @lawrence-carbon

---

*This product brief is a living document and will be updated as the product evolves.*

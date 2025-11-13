# Contributing to QTC (Query to Command)

Thank you for your interest in contributing to QTC! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

- **Check existing issues**: Before creating a new issue, check if it's already reported
- **Use the issue template**: Provide as much detail as possible
- **Include reproduction steps**: Help us reproduce the bug
- **Environment details**: Python version, OS, package version

### Suggesting Features

- **Check the roadmap**: See if your feature is already planned
- **Open a discussion**: For major features, start a discussion first
- **Be specific**: Describe the use case and expected behavior

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**: Follow the coding standards below
4. **Add tests**: Ensure your code is covered by tests
5. **Run tests locally**: `poetry run pytest`
6. **Check code quality**: `poetry run ruff check .` and `poetry run black --check .`
7. **Commit your changes**: Use clear, descriptive commit messages
8. **Push to your fork**: `git push origin feature/amazing-feature`
9. **Open a Pull Request**: Use the PR template

## Development Setup

### Prerequisites

- Python 3.12+
- Poetry (see [Poetry installation guide](https://python-poetry.org/docs/#installation))

### Setup Steps

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/your-username/cli-nlp.git
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

5. **Run with coverage**:
   ```bash
   poetry run pytest --cov=cli_nlp --cov-report=html
   ```

## Coding Standards

### Code Style

- **Formatter**: We use [Black](https://black.readthedocs.io/) for code formatting
  ```bash
  poetry run black .
  ```

- **Linter**: We use [Ruff](https://docs.astral.sh/ruff/) for linting
  ```bash
  poetry run ruff check .
  poetry run ruff check --fix .  # Auto-fix issues
  ```

- **Type hints**: Use type hints where appropriate
- **Docstrings**: Follow Google-style docstrings for public functions/classes

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Example:
```
feat: add support for custom command templates
fix: resolve config file permission issue
docs: update installation instructions
```

### Testing

- **Write tests**: All new features should include tests
- **Test coverage**: Aim for high test coverage
- **Run tests**: Always run tests before submitting PR
- **Test structure**: Follow existing test patterns in `tests/`

### Documentation

- **Update README**: If adding new features or changing behavior
- **Docstrings**: Add docstrings to new functions/classes
- **Examples**: Include usage examples for new features
- **CHANGELOG**: Update CHANGELOG.md with your changes

## Project Structure

```
cli-nlp/
├── cli_nlp/          # Main package
├── tests/            # Test suite
├── .github/          # GitHub workflows and templates
├── pyproject.toml    # Project configuration
└── README.md         # Project documentation
```

## Review Process

1. **Automated checks**: All PRs must pass CI checks (tests, linting)
2. **Code review**: At least one maintainer will review your PR
3. **Feedback**: Address any feedback or requested changes
4. **Merge**: Once approved, your PR will be merged

## Questions?

- **Open an issue**: For bugs or feature requests
- **Start a discussion**: For questions or ideas
- **Check existing issues**: Your question might already be answered

Thank you for contributing! 🎉


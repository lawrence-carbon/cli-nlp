# AGENTS.md

## Cursor Cloud specific instructions

This is a Python CLI tool (`qtc` / `query-to-command`) that converts natural language to shell commands via LLM providers. It is a single-process CLI app with no databases, Docker, or web servers.

### Running the project

- **Install deps**: `poetry install`
- **Run CLI**: `poetry run qtc --help`
- **Lint**: `poetry run black --check .` and `poetry run ruff check .`
- **Tests**: `poetry run pytest` (199 tests, all mocked — no API keys needed)
- **Format**: `poetry run black .` / `poetry run ruff check --fix .`

See `README.md` "Development" section and `.cursor/rules/project-context.mdc` for the full quick-reference.

### Non-obvious caveats

- Poetry must be on `$PATH`. In cloud VMs it installs to `~/.local/bin`, so ensure `export PATH="$HOME/.local/bin:$PATH"` is in the shell profile.
- The `qtc` entry point that converts queries requires a configured LLM provider API key (e.g. `OPENAI_API_KEY`). All tests mock external calls, so tests run without any API key.
- Config, cache, and history are stored in XDG directories (`~/.config/cli-nlp/`, `~/.cache/cli-nlp/`, `~/.local/share/cli-nlp/`). These are created on first use.
- The `pyproject.toml` pins `ruff = "^0.1.0"` (an older version). Do not upgrade without checking for rule-set compatibility.

### CI / PR workflow

- Owner PRs are auto-approved by `.github/workflows/auto-approve-owner.yml` (checks `author_association == 'OWNER'`). External contributor PRs still require manual review.
- This requires the repo setting **Settings → Actions → General → Workflow permissions → "Allow GitHub Actions to create and approve pull requests"** to be enabled.

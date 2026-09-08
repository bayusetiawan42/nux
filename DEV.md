# Developer Guide

## Project Structure

```
sharkyo/
  core/           # Core logic: agent, config, LLM, errors, protocols
  storage/        # Persistence layer: DB, API keys, history, knowledge
  tools/          # Tool implementations: CMD, KNOWLEDGE, SKILL, QUESTIONARY
  ui/             # Display and terminal output
  server/         # Client/server daemon mode
  search/         # BM25 search engine for skills
  skills/         # Built-in skill definitions (markdown files)
```

## Breaking Changes Policy

Sharkyo is pre-release (no stable version released yet). **Breaking changes are allowed.**

Backward compatibility is **not recommended** because:
- Compat shims add maintenance burden with no real benefit at this stage
- No API stability guarantee until v1.0
- Import paths must follow the correct package structure

## Import Paths

Always import from the canonical module location. Do NOT import from top-level shim modules.

| Module | Import Path |
|---|---|
| Agent | `from sharkyo.core.agent import Agent` |
| Config | `from sharkyo.core.config import Config, load_config, RC_FILE` |
| Constants | `from sharkyo.core.constants import DB_FILE, SHARKYO_DIR, SKILLS_DIR, SYSTEM_PROMPT, setup_dirs` |
| Context | `from sharkyo.core.context import get_environment_context` |
| Errors | `from sharkyo.core.errors import SharkyoError, NoAPIKeyError, ...` |
| LLM | `from sharkyo.core.llm import ChatCompletion, Groq, errors` |
| RequestManager | `from sharkyo.core.request_manager import RequestManager` |
| API Keys | `from sharkyo.storage.apikeys import ApiKey, active_key, add_key, ...` |
| DB | `from sharkyo.storage.db import get_connection` |
| History | `from sharkyo.storage.history import HistoryManager` |
| Knowledge | `from sharkyo.storage.knowledge import KnowledgeManager` |
| Display | `from sharkyo.ui.display import console, print_error, print_info, ...` |

## Development Rules

### Code Style

- Python 3.10+ required
- Line length: 100 characters max
- Use `ruff` for linting and formatting
- No comments unless absolutely necessary
- Follow existing patterns in the codebase

### Testing

- Framework: `pytest`
- Test directory: `tests/`
- Run tests: `python -m pytest tests/`
- Run with verbose: `python -m pytest tests/ -v`
- Run specific test: `python -m pytest tests/test_config.py`

#### Runtime Tests

Always do a fresh start before runtime testing:

```bash
sharkyo --clear --clear-knowledge && sharkyo server stop
```

Then install and run:

```bash
pip install .
sharkyo "your test prompt"
```

### Package Management

- Build system: `setuptools`
- Dependencies defined in `pyproject.toml`
- Dev dependencies: `pytest`, `ruff`
- Install in editable mode: `pip install -e ".[dev]"`

### Error Handling

- All custom errors inherit from `SharkyoError`
- Define new errors in `sharkyo/core/errors.py`
- Use specific error classes, not generic exceptions

### Storage Layer

- SQLite-based storage
- Schema migrations managed in `sharkyo/storage/schema.py`
- Use `get_connection()` for DB access
- API keys stored in system keyring

### Tools

- Each tool is a callable class in `sharkyo/tools/`
- Tool schema defined in `sharkyo/tools/schema.py`
- Tools receive `args` dict and `config` object
- Tools return result objects

### Skills

- Skills are markdown files in `sharkyo/skills/`
- Skill search uses BM25 algorithm
- Each skill file should contain clear execution instructions

## Commands Reference

```bash
# Install
pip install -e ".[dev]"

# Lint
ruff check .

# Format
ruff format .

# Test (unit)
python -m pytest tests/

# Fresh start (before runtime tests)
sharkyo --clear --clear-knowledge && sharkyo server stop

# Runtime test
pip install .
sharkyo "your test prompt"

# Run sharkyo
sharkyo
sharkyo --add-key gsk_XXXX
```

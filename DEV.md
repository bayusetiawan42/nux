# Developer Guide

## Project Structure

```
nux/
  core/           # Core logic: agent, config, LLM, errors, protocols
  storage/        # Persistence layer: DB, API keys, history, knowledge
  tools/          # Tool implementations: CMD, KNOWLEDGE, SKILL, QUESTIONARY
  ui/             # Display and terminal output
  server/         # Client/server daemon mode
  search/         # BM25 search engine for skills
  skills/         # Built-in skill definitions (markdown files)
```

## Breaking Changes Policy

Nux is pre-release (no stable version released yet). **Breaking changes are allowed.**

Backward compatibility is **not recommended** because:
- Compat shims add maintenance burden with no real benefit at this stage
- No API stability guarantee until v1.0
- Import paths must follow the correct package structure

## Import Paths

Always import from the canonical module location. Do NOT import from top-level shim modules.

| Module | Import Path |
|---|---|
| Agent | `from nux.core.agent import Agent` |
| Config | `from nux.core.config import Config, load_config, RC_FILE` |
| Constants | `from nux.core.constants import DB_FILE, NUX_DIR, SKILLS_DIR, SYSTEM_PROMPT, setup_dirs` |
| Context | `from nux.core.context import get_environment_context` |
| Errors | `from nux.core.errors import NuxError, NoAPIKeyError, ...` |
| LLM | `from nux.core.llm import ChatCompletion, Groq, errors` |
| RequestManager | `from nux.core.request_manager import RequestManager` |
| API Keys | `from nux.storage.apikeys import ApiKey, active_key, add_key, ...` |
| DB | `from nux.storage.db import get_connection` |
| History | `from nux.storage.history import HistoryManager` |
| Knowledge | `from nux.storage.knowledge import KnowledgeManager` |
| Display | `from nux.ui.display import console, print_error, print_info, ...` |

## Development Rules

### Code Style

- Python 3.10+ required
- Line length: 100 characters max
- Use `ruff` for linting and formatting
- No comments unless absolutely necessary
- Follow existing patterns in the codebase

### Comments

- Use `#` for all comments, never `"""`
- Multiline comments use multiple `#` lines:
  ```python
  # Line 1
  # Line 2
  ```

### Language

- All code, comments, docstrings, variable names, and text must be in English
- No mixed languages in code files

### Testing

- Framework: `pytest`
- Test directory: `tests/`
- Run tests: `python -m pytest tests/`
- Run with verbose: `python -m pytest tests/ -v`
- Run specific test: `python -m pytest tests/test_config.py`

#### Runtime Tests

Always do a fresh start before runtime testing:

```bash
nux --clear --clear-knowledge && nux server stop
```

Then install and run:

```bash
pip install .
nux "your test prompt"
```

### Package Management

- Build system: `setuptools`
- Dependencies defined in `pyproject.toml`
- Dev dependencies: `pytest`, `ruff`
- Install in editable mode: `pip install -e ".[dev]"`

### Error Handling

- All custom errors inherit from `NuxError`
- Define new errors in `nux/core/errors.py`
- Use specific error classes, not generic exceptions

### Error Logging

All errors are logged to `~/.nux/error/`:
- `error.log` - Tracebacks, error messages, context
- `history.json` - Conversation history at time of error (RAM, not SQLite)

Use `nux.core.error_logger.log_error()` to log errors:
```python
from nux.core.error_logger import log_error

try:
    ...
except Exception as e:
    log_error(e, context="what was happening", messages=conversation_messages)
```

### Storage Layer

- SQLite-based storage
- Schema migrations managed in `nux/storage/schema.py`
- Use `get_connection()` for DB access
- API keys stored in system keyring

### Tools

- Each tool is a callable class in `nux/tools/`
- Tool schema defined in `nux/tools/schema.py`
- Tools receive `args` dict and `config` object
- Tools return result objects

### Skills

- Skills are markdown files in `nux/skills/`
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
nux --clear --clear-knowledge && nux server stop

# Runtime test
pip install .
nux "your test prompt"

# Run nux
nux
nux --add-key gsk_XXXX
```

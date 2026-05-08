# AGENTS.md

## Project Structure
- Package source: `src/tkzs_structlog/` (hatchling expects this layout)
- Config versions 1.0-4.0, all backward compatible
- Entry points: `init_structlog(config_path=None)`, `get_logger(name=None)`
- Config file format: JSONC (JSON with `//` comments), loaded as `structlog_config.json` or `structlog_config.{env}.json`
- Multi-env: set `STRUCTLOG_ENV=prod` to load `structlog_config.prod.json`

## Critical Commands
```bash
# Install (all extras)
uv sync --all-extras

# Verify before claiming work done
ruff check . --fix
ruff format .
mypy src/tkzs_structlog
pytest --cov=tkzs_structlog tests/

# Single test
pytest tests/unit/test_config.py::test_validate_config_v1 -v

# Run tests in parallel
pytest -n auto tests/

# Build package
uv build
```

## Key Gotchas

### Config loading
- `init_structlog()` auto-loads config from working directory
- If config is missing/invalid, falls back to built-in `DEFAULT_CONFIG` instead of crashing

### Version management
- Hatchling vcs versioning generates `src/tkzs_structlog/_version.py` at build time
- Do not manually edit `_version.py`; it is overwritten on `uv build`

### pyproject.toml quirks
- Uses `[dependency-groups]` (uv), not `[tool.uv] dev-dependencies` or `[project.dependencies]`
- mypy excludes `tests/` by default (set in pyproject.toml)

### Windows execution
- Use PowerShell commands; `&&` chaining not supported
- Test commands: `pytest tests/unit/test_config.py -v` (pass paths directly)

### Test isolation
- `tests/conftest.py` has `autouse` fixture that calls `reset_structlog()` after every test
- Do not manually reset between tests unless testing reset behavior itself

### Logging behavior
- structlog is configured once globally; `get_logger()` reuses the same config
- After `init_structlog()`, any standard logging calls (`logging.info()` etc.) also route through structlog processors (bridge)

## Commit Policy (from CLAUDE.md)
- Commit after each feature implementation (functional commit)
- Commit after each test implementation (test commit with coverage details, mock strategy)
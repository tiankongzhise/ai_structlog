# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

tkzs-structlog is a configuration-driven automation tool for structlog that provides production-grade logging capabilities: log truncation, composite rotation, multi-environment support, sensitive data masking, and third-party output adapters (PostgreSQL, Redis, Kafka, Sentry). Configuration uses JSONC files with versioning (1.0 through 4.0).

## Common Commands

```bash
# Install project with all optional dependencies
uv sync --all-extras

# Run all tests with coverage
pytest --cov=tkzs_structlog tests/

# Run a single test file
pytest tests/unit/test_config.py -v

# Run a specific test
pytest tests/unit/test_config.py::test_validate_config_v1 -v

# Run tests in parallel
pytest -n auto tests/

# Lint and format
ruff check . --fix
ruff format .

# Type checking
mypy src/tkzs_structlog

# Build package
uv build
```

## Architecture

The codebase follows a 4-layer architecture under `src/tkzs_structlog/`:

### API Layer (`api/`)
Public interface. Main entry points:
- `init_structlog(config_path=None)` - Initialize logging with optional config file
- `get_logger(name=None)` - Get a configured structlog logger
- `bind_context()` / `unbind_context()` / `clear_context()` - Context variable management

### Config Layer (`config/`)
Handles configuration loading, validation, and parsing:
- `loader.py` - Loads JSONC config files, supports `STRUCTLOG_ENV` env var for multi-environment (`structlog_config.{env}.json`)
- `validator.py` - Pydantic v2 models for each config version (`StructlogV1Config` through `StructlogV4Config`), `validate_config()`
- `parser.py` - Parses validated config into processor/handler parameters
- `defaults.py` - `DEFAULT_CONFIG` and `merge_config()` for fallback behavior

Config versioning: 1.0 (basic), 2.0 (truncate/rotation/masking), 2.1 (performance), 3.0 (CLI/hot-reload), 4.0 (ecosystem adapters). Higher versions are backward compatible.

### Core Layer (`core/`)
Internal machinery:
- `initializer.py` - `StructlogInitializer` configures structlog once
- `processor_builder.py` - `ProcessorBuilder` assembles processors based on config
- `logger_factory.py` - `LoggerFactory` creates loggers with proper configuration

### Extensions Layer (`extensions/`)
Processors and handlers:
- `processors.py` - `TruncateProcessor`, `SensitiveDataProcessor`, `FilterProcessor`
- `handlers.py` - `setup_console_handler()`, `setup_file_handler()`, `ColoredConsoleHandler`
- `rotation.py` - `CustomRotatingFileHandler` with size/time-based rotation, compression backends (gzip/lz4/zstd)
- `hotreload.py` - `ConfigHotReloader` using watchdog for config file monitoring
- `pgsql_handler.py`, `redis_handler.py` - Third-party output adapters

### Exceptions (`exceptions/`)
All custom exceptions inherit from `StructlogBaseError` with fields: `error_type`, `error_field`, `reason`, `fix_suggestion`. Key subclasses: `StructlogConfigError`, `StructlogProcessorError`, `StructlogHandlerError`, `StructlogNotInitedError`.

## Key Patterns

- **Default degradation**: When config is invalid/missing, the system falls back to `DEFAULT_CONFIG` rather than crashing
- **Configuration-driven**: All behavior controlled via JSONC config files, no code changes needed for most adjustments
- **Processor chain**: Processors are built by `ProcessorBuilder` and applied in order during log initialization
- **Test isolation**: `conftest.py` auto-resets structlog state after each test via `reset_structlog()`

## Dependencies

- Core: `structlog>=23.1.0`, `pyjson5>=2.0.0`, `pydantic>=2.0`, `psycopg2-binary>=2.9.12`
- Optional: `lz4`, `zstandard` (compress), `redis`, `kafka-python`, `sentry-sdk`, `python-dotenv` (ecosystem), `watchdog`, `click` (CLI)
- Dev: `pytest`, `pytest-cov`, `pytest-xdist`, `mypy`, `ruff`

## 及时更新
- **及时提交功能性commit** 每当实现一个功能，都应当提交一个commit详述本功能是如何实现的
- **及时提交测试性commit** 每完成一个功能的测试，都应当提交一个commit详述本测试测试了哪些边界情况，原功能的代码覆盖率如何，通过率如何。是否存在mock。如果mock是怎么mock的。
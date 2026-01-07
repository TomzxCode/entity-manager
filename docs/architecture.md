# Architecture

## Overview

Entity Manager is built with a modular architecture that separates concerns and allows for easy extension.

## Project Structure

```
entity-manager/
├── src/
│   └── entity_manager/
│       ├── __init__.py
│       ├── cli.py          # CLI interface
│       ├── entities/       # Entity management
│       ├── github/         # GitHub integration
│       └── notion/         # Notion integration
├── tests/                  # Test suite
├── docs/                   # Documentation
└── pyproject.toml         # Project configuration
```

## Core Components

### CLI Interface

The CLI is built using [Cyclopts](https://cyclopts.readthedocs.io/), providing a clean and intuitive command-line interface.

### Entity Management

Entities are the core abstraction in Entity Manager. Each entity represents a logical unit that can be tracked, managed, and synchronized across different platforms.

### Integrations

#### GitHub

Entity Manager integrates with GitHub using the [PyGithub](https://github.com/PyGithub/PyGithub) library. This allows tracking entities such as issues, pull requests, and repositories.

#### Notion

The Notion integration uses the [notion-client](https://github.com/ramnes/notion-sdk-py) library to sync entities with Notion databases.

## Design Principles

1. **Modularity**: Each integration is self-contained and can be used independently
2. **Extensibility**: New integrations can be added without modifying core functionality
3. **Type Safety**: Type hints are used throughout for better IDE support and error checking
4. **Testing**: Comprehensive test coverage ensures reliability

## Logging

Entity Manager uses [structlog](https://www.structlog.org/) for structured logging, providing rich and parseable log output.

## Development

### Running Tests

```bash
uv run pytest
```

### Code Quality

```bash
# Run linter
uv run ruff check

# Format code
uv run ruff format
```

### Building Documentation

```bash
uv run mkdocs build
```

To serve documentation locally:

```bash
uv run mkdocs serve
```

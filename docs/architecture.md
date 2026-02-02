# Architecture

## Overview

Entity Manager is built with a modular, plugin-based architecture that separates the CLI interface from storage backends. This design allows easy extension with new storage systems while maintaining a consistent API.

## Project Structure

```
entity-manager/
├── src/
│   └── entity_manager/
│       ├── __init__.py
│       ├── cli.py              # Main CLI entry point
│       ├── backend.py          # Abstract backend interface
│       ├── models.py           # Data models (Entity, Link)
│       ├── config.py           # Configuration management
│       ├── config_commands.py  # Configuration CLI commands
│       ├── link_commands.py    # Link CLI commands
│       └── backends/           # Backend implementations
│           ├── github.py       # GitHub Issues backend
│           ├── notion.py       # Notion Database backend
│           ├── beads.py        # Beads backend
│           ├── backlog.py      # Backlog.md backend
│           ├── sqlite.py       # SQLite backend
│           ├── markdown.py     # Markdown files backend
│           └── redis.py        # Redis backend
├── tests/                      # Test suite
│   ├── backends/              # Backend-specific tests
│   └── integration/           # Integration tests
├── docs/                       # Documentation
├── spec/                       # Feature specifications
└── pyproject.toml             # Project configuration
```

## Core Components

### CLI Interface

The CLI is built using [Cyclopts](https://cyclopts.readthedocs.io/), providing a clean and intuitive command-line interface with:

- **Entity commands**: CRUD operations (create, read, update, delete, list)
- **Link commands**: Relationship management (add, remove, list, tree, cycle)
- **Config commands**: Configuration management (set, get, unset, list, init)
- **Global options**: Log level control

### Data Models

#### Entity

The `Entity` model represents a task, issue, or requirement with:

- `id`: Unique identifier (format varies by backend)
- `title`: Entity title
- `description`: Detailed description
- `status`: Current state (open, in_progress, closed)
- `labels`: Key-value pairs for categorization
- `assignee`: Assigned user or agent
- `metadata`: Backend-specific additional data

#### Link

The `Link` model represents directed relationships between entities:

- `source_id`: Source entity ID
- `target_id`: Target entity ID
- `link_type`: Relationship type (blocking, parent, depends-on, etc.)

### Backend Interface

The abstract `Backend` class defines the contract all backends must implement:

- **CRUD operations**: create, read, update, delete, list_entities
- **Link operations**: add_link, remove_link, list_links
- **Graph operations**: get_link_tree, find_cycles

This abstraction allows Entity Manager to work with any storage system by implementing the `Backend` interface.

### Configuration Management

Hierarchical configuration system with:

- **Local config**: `.entity-manager/config.yaml` in project directory
- **Global config**: `~/.entity-manager/config.yaml` in home directory
- **Precedence**: Local settings override global defaults
- **Format**: YAML key-value pairs with dot notation

### Backends

#### Backlog Backend

Reads/writes backlog.md markdown task files:
- Task IDs in format task-N
- Markdown files in backlog/tasks/ directory
- Status mapping (To Do, In Progress, Done)

#### Beads Backend

Integrates with the beads task management system:
- Beads hash format (bd-xxxx) for entity IDs
- Direct file-system integration

#### GitHub Backend

Uses [PyGithub](https://github.com/PyGithub/PyGithub) to map GitHub Issues to entities:
- Issue numbers as entity IDs
- Labels mapped to entity labels
- Issue descriptions and status tracked
- Custom fields for dependencies (blocked by, blocking, parent)

#### Markdown Backend

Stores entities as individual markdown files:
- File-based entity IDs
- Links stored in separate YAML file (_links.yaml in the content directory)
- Supports arbitrary link types with automatic inverse mapping

#### Notion Backend

Uses [notion-client](https://github.com/ramnes/notion-sdk-py) to map Notion pages to entities:
- Page UUIDs as entity IDs
- Database properties mapped to entity fields
- Relation properties for links

#### Redis Backend

In-memory backend for fast operations:
- Key-value storage for entities
- Set-based link tracking
- Ideal for temporary or high-performance scenarios

#### SQLite Backend

Uses SQLite for local relational storage:
- Integer entity IDs
- Efficient SQL queries for filtering and sorting
- Full-text search capabilities

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

# Entity Manager

An entity manager for LLMs.

## Overview

Entity Manager is a tool designed to enable LLMs to work efficiently with structured data in a directed graph format. It provides a unified interface for managing entities (tasks, requirements, issues) and their relationships across multiple storage backends.

## Purpose

Entity Manager addresses two key use cases:

1. **External Data Source Integration** - Interact with external services (GitHub, Notion, etc.) with a local synchronized copy for fast queries
2. **LLM Collaboration** - Enable multiple LLM agents to collaborate on complex projects by tracking task assignment, dependencies, and preventing duplicate work

## Features

- **Unified Entity Management**: Create, read, update, delete, and list entities with consistent API across backends
- **Link Management**: Track relationships between entities (parent/child, blocking/blocked by, custom types)
- **Multiple Backend Support**:
  - Backlog.md
  - Beads
  - GitHub Issues
  - Markdown Files
  - Notion Databases
  - Redis
  - SQLite
- **Configuration Management**: Local and global configuration with hierarchical fallback
- **Cycle Detection**: Identify circular dependencies in entity relationships
- **CLI Interface**: Intuitive command-line interface for all operations

## Quick Start

```bash
# Install the tool
uv tool install git+https://github.com/TomzxCode/entity-manager

# Run the CLI
entity-manager --help
```

For more detailed installation and usage instructions, see the [Getting Started](getting-started.md) guide.

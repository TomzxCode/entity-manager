# Getting Started

## Installation

### Using uv

```bash
uv tool install git+https://github.com/TomzxCode/entity-manager
```

## Initial Setup

Entity Manager uses a hierarchical configuration system with both local (project-specific) and global (user-wide) settings.

### Quick Setup with Interactive Init

The easiest way to get started is using the interactive `init` command:

```bash
# Setup global configuration (recommended for tokens)
em init --global

# Or setup local configuration for this project
em init
```

This will guide you through:
1. Selecting a backend (backlog, beads, github, markdown, notion, redis, sqlite)
2. Configuring backend-specific settings
3. Setting authentication tokens (if needed)

### Manual Configuration

Alternatively, configure manually using config commands:

#### Backlog.md Backend

```bash
em config set backend backlog
em config set backlog.path ./backlog
```

#### GitHub Backend

```bash
# Set backend and repository (local, project-specific)
em config set backend github
em config set github.owner your-username
em config set github.repository your-repo

# Set token (global, reused across projects)
em config set github.token ghp_your_token_here --global
```

Create a GitHub personal access token with `repo` scope at [https://github.com/settings/tokens](https://github.com/settings/tokens)

#### Markdown Backend (File-based)

```bash
em config set backend markdown
em config set markdown.directory_path ./entities
```

#### Redis Backend (In-Memory)

```bash
em config set backend redis
# Optional: configure connection (defaults shown)
em config set redis.host localhost
em config set redis.port 6379
```

#### SQLite Backend (Local Storage)

```bash
em config set backend sqlite
em config set sqlite.db_path .em.db
```

See [README.md](../README.md) for complete backend setup instructions.

## Basic Usage

Once configured, you can use the CLI:

```bash
# Show help
em --help

# Create an entity
em create "Fix login bug" --labels "type:bug,priority:high"

# List entities
em list

# Read entity details
em read 123

## Next Steps

- Check out the [Usage](usage.md) guide for detailed command examples
- Read the [Architecture](architecture.md) documentation to understand how it works

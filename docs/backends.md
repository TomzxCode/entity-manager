# Backends

Entity Manager supports multiple storage backends, each with its own strengths and use cases. This page provides detailed information about configuring and using each backend.

## Overview

A backend determines where and how entity data is stored. All backends implement the same interface, providing consistent CRUD operations, link management, and graph traversal capabilities.

## Available Backends

- **Backlog** - Use backlog.md markdown task files
- **Beads** - Integrate with the beads task management system
- **GitHub** - Use GitHub Issues as entities
- **Markdown** - Individual markdown files with YAML link storage
- **Notion** - Use Notion Database pages as entities
- **Redis** - In-memory key-value storage for high-performance scenarios
- **SQLite** - Local relational database storage

## Backlog Backend

### Overview

The Backlog backend integrates with backlog.md, reading and writing markdown task files directly.

### Features

- Compatible with backlog.md format
- Task IDs in format `task-N`
- Automatic ID normalization
- Status mapping to backlog.md states
- No backlog CLI required for entity-manager operations

### Setup

```bash
# Set backend type
em config set backend backlog

# Configure backlog path (optional, defaults to ./backlog)
em config set backlog.path ./backlog
```

### ID Format

- Full format: `task-10`, `task-42`
- Short format: `10`, `42` (automatically normalized to full format)

### File Structure

```
backlog/
└── tasks/
    ├── task-1.md
    ├── task-2.md
    └── task-3.md
```

### Status Mapping

- `open` → "To Do"
- `in_progress` → "In Progress"
- `closed` → "Done"

### Example Usage

```bash
# Create task
em create "Implement user login"

# Update task status
em update task-10 --status "in_progress"

# Add dependency
em link add task-10 task-5 --type "blocked_by"

# Works with both formats
em read task-10
em read 10  # Same as task-10
```

### Best For

- Projects already using backlog.md
- Markdown-based task management
- Team collaboration with backlog.md

## Beads Backend

### Overview

The Beads backend integrates with the beads task management system.

### Features

- Beads hash format entity IDs
- Direct file-system integration
- Beads database format compatibility

### Setup

```bash
# Set backend type
em config set backend beads

# Configure project path (optional, defaults to current directory)
em config set beads.project_path /path/to/project

# Initialize beads in your project (if not already done)
cd /path/to/project
bd init
```

Install beads from [https://github.com/steveyegge/beads](https://github.com/steveyegge/beads)

### ID Format

Entity IDs use beads hash format (e.g., `bd-a1b2`, `bd-c3d4`).

### Example Usage

```bash
# Create entity
em create "Refactor authentication"

# Read entity (using beads hash)
em read bd-a1b2
```

### Best For

- Projects using beads
- Beads workflow integration

## GitHub Backend

### Overview

The GitHub backend maps GitHub Issues to entities, allowing you to manage tasks directly in your repository's issue tracker.

### Features

- Issue numbers as entity IDs
- Automatic label creation
- Issue descriptions and status tracking
- Link management via custom issue fields
- Direct GitHub API integration

### Setup

```bash
# Set backend type
em config set backend github

# Configure repository (local, project-specific)
em config set github.owner your-username
em config set github.repository your-repo

# Set authentication token (global, reused across projects)
em config set github.token ghp_your_token_here --global
```

Create a GitHub personal access token with `repo` scope at [https://github.com/settings/tokens](https://github.com/settings/tokens)

### ID Format

Entity IDs are GitHub issue numbers (e.g., `123`, `456`).

### Status Mapping

- `open` → Issue is open
- `closed` → Issue is closed
- `in_progress` → Custom label-based status

### Supported Link Types

- `blocked by` - This issue is blocked by another
- `blocking` - This issue blocks another
- `parent` - Parent issue relationship

### Example Usage

```bash
# Create a new issue
em create "Fix authentication bug" --labels "type:bug,priority:high"

# Read issue details
em read 42

# Update issue status
em update 42 --status "closed"

# Add blocking relationship
em link add 42 35 --type "blocking"
```

## Markdown Backend

### Overview

The Markdown backend stores entities as individual markdown files with a separate YAML file for link storage. This approach provides human-readable, version-control-friendly storage.

### Features

- File-based entity storage
- Markdown format for easy editing
- YAML link storage (`_links.yaml` in the content directory)
- Arbitrary link types with automatic inverse mapping
- Git-friendly format

### Setup

```bash
# Set backend type (optional, markdown is the default)
em config set backend markdown

# Configure directory path (optional, defaults to .entity-manager/content)
em config set markdown.directory_path .entity-manager/content
```

### ID Format

Entity IDs are based on filenames (e.g., `entity-123.md` → `entity-123`).

### File Structure

```
project/
└── .entity-manager/
    └── content/
        ├── _links.yaml
        ├── entity-1.md
        ├── entity-2.md
        └── entity-3.md
```

### Link Inverse Mapping

The Markdown backend automatically handles inverse relationships:

- `blocking` ↔ `blocked by`
- `parent` ↔ `children`
- `depends-on` ↔ `depended-on-by`
- Custom types get automatic inverse names (e.g., `custom-link` → `custom-link-inverse`)

### Example Usage

```bash
# Create entity (creates markdown file)
em create "Document API endpoints"

# View entity (reads markdown file)
em read entity-1

# Add custom link type
em link add entity-1 entity-2 --type "references"

# View link tree (shows both "references" and "references-inverse")
em link tree entity-1
```

### Best For

- Documentation-heavy projects
- Version control tracking
- Human review of entity data
- Projects requiring custom link types

## Notion Backend

### Overview

The Notion backend maps Notion Database pages to entities, enabling task management within Notion.

### Features

- Page UUIDs as entity IDs
- Database properties mapped to entity fields
- Relation properties for links
- Rich text support
- Notion's collaborative features

### Setup

```bash
# Set backend type
em config set backend notion

# Set authentication token (global)
em config set notion.token secret_xxx --global

# Set database ID (local or global)
em config set notion.database_id abc123...
```

Create a Notion integration at [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)

### Database Schema Requirements

Your Notion database must have these properties:

- `Name` (Title) - Entity title
- `Description` (Rich Text) - Entity description
- `Status` (Status) - Entity status
- `Labels` (Multi-select) - Entity labels/tags
- `Assignee` (People) - Entity assignee
- `Blocked By` (Relation) - Blocking entities
- `Blocking` (Relation) - Blocked entities
- `Parent` (Relation) - Parent entity
- `Children` (Relation) - Child entities

### ID Format

Entity IDs are Notion page UUIDs with hyphens (e.g., `abc123-def456-...`).

### Example Usage

```bash
# Create page in database
em create "Q1 Planning" --labels "priority:high,type:epic"

# Update page
em update abc123... --status "in_progress"

# Add parent relationship
em link add abc123... def456... --type "parent"
```

### Best For

- Teams using Notion
- Projects requiring rich formatting
- Collaborative task management
- Visual project tracking

## Redis Backend

### Overview

The Redis backend provides in-memory key-value storage for high-performance, distributed scenarios. Ideal for temporary storage, caching, or applications requiring extremely fast access.

### Features

- UUID-based entity IDs
- In-memory storage for sub-millisecond operations
- Distributed architecture support
- Optional persistence (if Redis is configured for it)
- Set-based link tracking for efficient relationship queries
- Connection pooling support

### Setup

```bash
# Set backend type
em config set backend redis

# Configure Redis connection (optional, defaults shown)
em config set redis.host localhost
em config set redis.port 6379
em config set redis.db 0

# If authentication is required
em config set redis.password your-redis-password --global
```

Ensure Redis server is running:
```bash
# Start Redis (varies by OS)
redis-server
```

### ID Format

Entity IDs are UUIDs (e.g., `550e8400-e29b-41d4-a716-446655440000`).

### Connection Parameters

- `redis.host` - Redis server hostname (default: `localhost`)
- `redis.port` - Redis server port (default: `6379`)
- `redis.db` - Redis database number (default: `0`)
- `redis.password` - Redis authentication password (optional)

### Example Usage

```bash
# Create entity (generates UUID)
em create "Cache user session data"

# Read entity (using UUID)
em read 550e8400-e29b-41d4-a716-446655440000

# List all entities (fast in-memory scan)
em list

# Add relationships
em link add 550e8400-... 660e8400-... --type "depends-on"
```

### Data Persistence

By default, Redis stores data in memory only. For persistence:

1. **RDB (Snapshotting)**: Configure Redis to periodically save snapshots
2. **AOF (Append-Only File)**: Configure Redis to log every write operation

Configure persistence in `redis.conf`:
```conf
# RDB snapshots
save 900 1
save 300 10
save 60 10000

# AOF persistence
appendonly yes
```

### Best For

- High-performance temporary storage
- Real-time applications requiring sub-millisecond latency
- Distributed systems with shared state
- Caching layer for other backends
- Development and testing with fast iteration
- Applications requiring concurrent access from multiple processes

### Considerations

- **Data Volatility**: Data is lost on Redis restart unless persistence is configured
- **Memory Limits**: Limited by available RAM
- **Scaling**: Requires Redis Cluster for horizontal scaling
- **Cost**: In-memory storage can be expensive at scale

## SQLite Backend

### Overview

The SQLite backend provides fast, local relational database storage with efficient querying and filtering capabilities.

### Features

- Integer entity IDs
- SQL-based filtering and sorting
- Full-text search support
- No external dependencies
- Offline-first design

### Setup

```bash
# Set backend type
em config set backend sqlite

# Configure database path (optional, defaults to .em.db)
em config set sqlite.db_path .em.db
```

### ID Format

Entity IDs are integers (e.g., `1`, `2`, `3`).

### Database Schema

The backend automatically creates tables for entities and links on first use.

### Example Usage

```bash
# Create entity
em create "Implement feature X"

# List with SQL-powered filtering
em list --filter "status=open" --sort "id" --limit 10

# Add dependencies
em link add 1 2 --type "depends-on"
```

### Best For

- Local development and testing
- Offline work
- Projects requiring fast queries
- Personal task management

## Choosing a Backend

### Decision Factors

**Use Backlog if:**
- You're already using backlog.md
- You want markdown-based task management
- You need compatibility with backlog.md tools

**Use Beads if:**
- You're already using beads for task management
- You want beads integration

**Use GitHub if:**
- You want entities synced with GitHub Issues
- Your team already uses GitHub for project management
- You need public issue tracking

**Use Markdown if:**
- You want human-readable entity files
- You need version control for entity data
- You want custom link types
- You prefer file-based storage

**Use Notion if:**
- Your team uses Notion for documentation
- You need rich text and visual features
- You want collaborative editing
- You prefer a web-based interface

**Use Redis if:**
- You need extremely fast, sub-millisecond operations
- You're building a distributed system with shared state
- You need a caching layer or temporary storage
- You require concurrent access from multiple processes
- You're developing/testing and want fast iteration

**Use SQLite if:**
- You need fast local storage
- You want efficient querying and filtering
- You're working offline
- You need a simple, zero-config solution

## Switching Backends

You can switch backends by changing the `backend` configuration:

```bash
# Switch to SQLite
em config set backend sqlite
em config set sqlite.db_path .em.db

# Switch to Markdown
em config set backend markdown
em config set markdown.directory_path ./entities
```

Note: Entity data is not automatically migrated between backends. You'll need to manually recreate entities or write a migration script.

## Multiple Backends

You can use different backends for different projects by using local configuration:

```bash
# Project A uses GitHub
cd ~/projects/project-a
em config set backend github
em config set github.repository project-a

# Project B uses SQLite
cd ~/projects/project-b
em config set backend sqlite
em config set sqlite.db_path .em.db
```

Global configuration provides defaults, while local configuration overrides for specific projects.

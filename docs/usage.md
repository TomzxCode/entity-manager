# Usage

## CLI Commands

Entity Manager provides a comprehensive CLI interface. The CLI is accessible via two commands:

- `entity-manager` - Full command name
- `em` - Short alias (recommended)

## Entity Management

### Create Entities

```bash
# Create with title only
em create "Fix login bug"

# Create with all options
em create "Add user authentication" \
  --description "Implement JWT-based authentication" \
  --labels "type:feature,priority:high,area:security" \
  --assignee alice
```

### Read Entity Details

```bash
# View full entity information
em read 123
```

Output includes: ID, title, description, status, labels, assignee, and URL (if available).

### Update Entities

```bash
# Update specific fields (only provided fields are changed)
em update 123 --status "in-progress"
em update 123 --title "New title" --assignee bob
em update 123 --labels "type:bug,priority:critical"
```

### Delete Entities

```bash
# Delete single entity
em delete 123

# Delete multiple entities
em delete 123 456 789
```

### List Entities

```bash
# List all entities
em list

# Filter by status
em list --filter "status=open"

# Sort by a property
em list --sort "created_at"

# Limit results
em list --limit 10

# Combine options
em list --filter "status=open" --sort "priority" --limit 20
```

## Link Management

Links represent directed relationships between entities.

### Add Links

```bash
# Add a single link
em link add 123 456 --type "blocking"

# Add multiple links of the same type
em link add 123 456 789 --type "children"

# Default link type is "relates-to"
em link add 123 456
```

Common link types:
- `blocking` / `blocked by`
- `parent` / `children`
- `depends-on` / `depended-on-by`
- `relates-to` (default)

### Remove Links

```bash
# Remove specific link
em link remove 123 456 --type "blocking"

# Remove link recursively (includes transitive links)
em link remove 123 456 --type "blocking" --recursive
```

### List Links

```bash
# List all links for an entity
em link list 123

# List links of specific type
em link list 123 --type "blocking"
```

### View Link Tree

```bash
# Display hierarchical view of all relationships
em link tree 123
```

Output shows the entity and all its relationships organized by type.

### Find Cycles

```bash
# Detect circular dependencies
em link cycle
```

Identifies cycles in the link graph to prevent circular dependencies.

## Configuration

Configuration can be local (project-specific) or global (user-wide).

### Interactive Setup

```bash
# Interactive configuration wizard
em init             # Local configuration
em init --global    # Global configuration
```

### Set Configuration

```bash
# Set local configuration
em config set backend github
em config set github.repository my-repo

# Set global configuration
em config set github.token ghp_xxx --global
```

### Get Configuration

```bash
# Get value with fallback (local → global)
em config get backend

# Get global value only
em config get backend --global
```

### List Configuration

```bash
# List merged configuration
em config list

# List global configuration only
em config list --global
```

Note: Sensitive values (tokens, passwords) are automatically redacted in output.

### Unset Configuration

```bash
# Remove from local configuration
em config unset github.repository

# Remove from global configuration
em config unset github.token --global
```

## Advanced Usage

### Logging

Control log verbosity with `--log-level`:

```bash
em --log-level debug list
em --log-level info create "Test entity"
```

Levels: `debug`, `info`, `warning`, `error`, `critical` (default: `critical`)

### Working with Multiple Projects

Use local configuration for project-specific settings and global for user-wide defaults:

```bash
# Global setup (once per user)
em config set github.token ghp_xxx --global
em config set backend github --global

# Project A
cd ~/projects/project-a
em config set github.repository project-a

# Project B
cd ~/projects/project-b
em config set github.repository project-b
em config set backend sqlite  # Use different backend
em config set sqlite.db_path .em.db
```

### Backend-Specific ID Formats

Different backends use different ID formats:
- **Backlog**: Task format (e.g., `task-10`, or just `10`)
- **Beads**: Hash format (e.g., `bd-a1b2`)
- **GitHub**: Issue numbers (e.g., `123`, `456`)
- **Markdown**: String IDs (e.g., `entity-123`)
- **Notion**: Page UUIDs (e.g., `abc123-def456...`)
- **Redis**: UUIDs (e.g., `550e8400-e29b-41d4-a716-446655440000`)
- **SQLite**: Integer IDs (e.g., `1`, `2`, `3`)

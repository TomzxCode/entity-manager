# Usage

## CLI Commands

Entity Manager provides a CLI interface with multiple commands. The CLI is accessible via two commands:

- `entity-manager` - Full command name
- `em` - Short alias

## Available Commands

### Help

To see all available commands and options:

```bash
entity-manager --help
```

### Entity Management

```bash
# List entities
entity-manager entities list

# Add a new entity
entity-manager entities add

# Update an entity
entity-manager entities update

# Delete an entity
entity-manager entities delete
```

## GitHub Integration

Entity Manager can integrate with GitHub to track entities across repositories:

```bash
# Sync with GitHub
entity-manager github sync
```

## Notion Integration

Entity Manager can sync entities with Notion databases:

```bash
# Sync with Notion
entity-manager notion sync
```

## Configuration File

You can also configure Entity Manager using a YAML configuration file (`.entity-manager.yml`):

```yaml
github:
  token: ${GITHUB_TOKEN}
  repos:
    - owner/repo1
    - owner/repo2

notion:
  token: ${NOTION_TOKEN}
  database_id: ${NOTION_DATABASE_ID}
```

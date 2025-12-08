# Entity Manager

An entity manager for LLMs.

## Installation

```bash
uv tool install git+https://github.com/TomzxCode/entity-manager
```

## Setup

Configuration can be stored in two locations:
- **Local config**: `.entity-manager/config.yaml` in the current directory (repository-specific)
- **Global config**: `~/.entity-manager/config.yaml` in your home directory (user-wide)

By default, commands use local config with global fallback. Use the `--global` flag to explicitly target global config.

### GitHub Backend

1. Set the backend type to GitHub (global):
```bash
em config set backend github --global
```

2. Configure GitHub repository (can be local or global):
```bash
# Local (repository-specific)
em config set github.owner your-username
em config set github.repository your-repo

# Or global (user-wide default)
em config set github.owner your-username --global
em config set github.repository your-repo --global
```

3. Set your GitHub token:
```bash
em config set github.token your-github-personal-access-token --global
```

Create a GitHub personal access token with `repo` scope at https://github.com/settings/tokens

### Beads Backend

1. Set the backend type to Beads:
```bash
em config set backend beads --global
```

2. Configure project path (optional, defaults to current directory):
```bash
em config set beads.project_path /path/to/project
```

3. Install beads from https://github.com/steveyegge/beads and initialize in your project:
```bash
cd /path/to/project
bd init
```

**Note:** With beads backend, entity IDs use the beads hash format (e.g., `bd-a1b2` instead of numeric IDs)

## Concepts

- **Entity**: A core object that holds data and metadata.
- **Attributes**: Key-value pairs that store information about an entity.
- **Links**: Relationships between entities, which can be of various types.

## Usage

### Create

```bash
em create "title"
em create "title" --description "description" --labels "type:bug,priority:0,status:open" --assignee alice
```

### Read

```bash
em read 123
```

### Update

```bash
em update 123 --title "new title"
em update 123 --description "new description"
em update 123 --labels "x,y,z"
em update 123 --status "open/in-progress/closed"
em update 123 --title "new title" --description "new description" --labels "x,y,z" --status "open/in-progress/closed"
```

### Delete

```bash
em delete 123
em delete 123 456 789
```

### List
```bash
em list --filter "status=open" --sort "property" --limit n
```

### Link

```bash
em link add 123 456 789 --type "relation-type"
em link remove 123 456 789 --type "relation-type" --recursive
em link list 123 --type "relation-type"

# Displays the link tree of an entity
em link tree 123

# Finds and displays cycles in links
em link cycle
```

## Configuration

Configuration supports both local (`.entity-manager/config.yaml`) and global (`~/.entity-manager/config.yaml`) scopes.
Use `--global` to target global config, otherwise local config is used with global fallback.

```bash
# Sets a configuration setting
em config set key value           # Local
em config set key value --global  # Global

# Unsets a configuration setting
em config unset key           # Local
em config unset key --global  # Global

# Gets the value of a configuration setting
em config get key           # Local with global fallback
em config get key --global  # Global only

# Lists all configuration settings
em config list           # Merged local + global
em config list --global  # Global only
```

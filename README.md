# Entity Manager

An entity manager for LLMs.

## Installation

```bash
uv tool install git+https://github.com/TomzxCode/entity-manager
```

## Setup

1. Copy `.env.example` to `.env` and configure your backend:

```bash
cp .env.example .env
```

### GitHub Backend

For GitHub backend, set these environment variables:
- `EM_BACKEND=github`
- `EM_GITHUB_OWNER=your-username`
- `EM_GITHUB_REPO=your-repo`
- `GITHUB_TOKEN=your-github-personal-access-token`

Create a GitHub personal access token with `repo` scope at https://github.com/settings/tokens

### Beads Backend

For Beads backend, set these environment variables:
- `EM_BACKEND=beads`
- `EM_BEADS_PROJECT_PATH=/path/to/project` (optional, defaults to current directory)

Install beads from https://github.com/steveyegge/beads and initialize in your project:
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

```bash
# Sets a configuration setting
em config set key value

# Unsets a configuration setting
em config unset key

# Gets the value of a configuration setting
em config get key

# Lists all configuration settings
em config list
```

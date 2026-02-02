# CLI Interface Specification

## Overview

The CLI (Command Line Interface) provides the primary user interaction point for the entity manager. It offers intuitive commands for entity CRUD operations, link management, and configuration, designed for both human use and LLM agent integration.

## Purpose

The CLI enables:
- Command-line access to all entity manager features
- Scriptable operations for automation and LLM agents
- Consistent command structure and argument patterns
- Clear, parseable output for both humans and programs
- Integration with external systems (GitHub, Beads, Notion)

## Requirements

### Command Structure

#### Command Naming

- The system MUST provide both `em` and `entity-manager` commands.
- Commands MUST follow a verb-noun pattern for main operations (e.g., `em create`, `em list`).
- Subcommands MUST use a clear hierarchical structure (e.g., `em link add`, `em config set`).

#### Command Groups

The CLI MUST support the following command groups:
- **Entity commands**: `create`, `read`, `update`, `delete`, `list`
- **Link commands**: `link add`, `link remove`, `link list`, `link tree`, `link cycle`
- **Config commands**: `config set`, `config get`, `config unset`, `config list`, `init`

### Global Options

#### Log Level

- The CLI MUST accept a `--log-level` global option.
- The `--log-level` option MUST support values: `debug`, `info`, `warning`, `error`, `critical`.
- The default log level MUST be `critical` (minimal output).
- Log levels control the verbosity of structlog output.

### Entity Commands

#### Create Command

- Syntax: `em create <title> [options]`
- Required argument: `title` (string) - the entity title
- Optional arguments:
  - `--description <text>`: Entity description (default: empty string)
  - `--labels <labels>`: Comma-separated labels, optionally with key:value format (e.g., "type:bug,priority:high")
  - `--assignee <username>`: Assigned user/agent
- Output: MUST print the created entity ID and title
- Example:
  ```bash
  em create "Fix login bug" --description "Users cannot log in" --labels "type:bug,priority:high" --assignee alice
  ```
  Output: `Created entity 123: Fix login bug`

#### Read Command

- Syntax: `em read <entity_id>`
- Required argument: `entity_id` (string) - the entity identifier
- Output: MUST print all entity fields including:
  - Entity ID
  - Title
  - Description
  - Status
  - Labels (if any)
  - Assignee (if assigned)
  - URL (if available in metadata)
- Example:
  ```bash
  em read 123
  ```
  Output:
  ```
  Entity: 123
  Title: Fix login bug
  Description: Users cannot log in
  Status: open
  Labels: type:bug, priority:high
  Assignee: alice
  URL: https://github.com/owner/repo/issues/123
  ```

#### Update Command

- Syntax: `em update <entity_id> [options]`
- Required argument: `entity_id` (string) - the entity to update
- Optional arguments (only specified fields are updated):
  - `--title <text>`: New title
  - `--description <text>`: New description
  - `--labels <labels>`: New labels (replaces all existing labels)
  - `--status <status>`: New status (e.g., "open", "closed", "in-progress")
  - `--assignee <username>`: New assignee (or empty to clear)
- Output: MUST print the updated entity ID and title
- Example:
  ```bash
  em update 123 --status "in-progress"
  ```
  Output: `Updated entity 123: Fix login bug`

#### Delete Command

- Syntax: `em delete <entity_id> [<entity_id> ...]`
- Required arguments: One or more entity IDs
- Output: MUST print the number of entities deleted
- Example:
  ```bash
  em delete 123 456 789
  ```
  Output: `Deleted 3 entity(ies)`

#### List Command

- Syntax: `em list [options]`
- Optional arguments:
  - `--filter <filters>`: Comma-separated key=value filters (e.g., "status=open,assignee=alice")
  - `--sort <property>`: Sort by property (backend-dependent)
  - `--limit <n>`: Maximum number of results
- Output: MUST print a numbered or bulleted list of entities with:
  - Status indicator (● for open, ○ for closed)
  - Entity ID
  - Title
  - Labels (if any)
- Example:
  ```bash
  em list --filter "status=open" --sort "created" --limit 10
  ```
  Output:
  ```
  Found 5 entity(ies):

  ● 123: Fix login bug [type:bug, priority:high]
  ● 124: Add feature X [type:feature]
  ...
  ```

### Link Commands

#### Link Add Command

- Syntax: `em link add <source_id> <target_id> [<target_id> ...] [options]`
- Required arguments:
  - `source_id`: Source entity ID
  - One or more `target_id`: Target entity IDs
- Optional arguments:
  - `--type <link_type>`: Type of link (default: "relates-to")
- Output: MUST print the number of links added
- Example:
  ```bash
  em link add 123 456 789 --type "blocked-by"
  ```
  Output: `Added 2 link(s) from 123`

#### Link Remove Command

- Syntax: `em link remove <source_id> <target_id> [<target_id> ...] [options]`
- Required arguments:
  - `source_id`: Source entity ID
  - One or more `target_id`: Target entity IDs
- Optional arguments:
  - `--type <link_type>`: Type of link to remove (default: "relates-to")
  - `--recursive`: Remove all transitive links as well
- Output: MUST print the number of links removed
- Example:
  ```bash
  em link remove 123 456 --type "blocked-by"
  ```
  Output: `Removed 1 link(s) from 123`

#### Link List Command

- Syntax: `em link list <entity_id> [options]`
- Required argument: `entity_id`: Entity to list links for
- Optional arguments:
  - `--type <link_type>`: Filter by link type (default: show all)
- Output: MUST print all links in format: `source --[type]--> target`
- Example:
  ```bash
  em link list 123 --type "blocked-by"
  ```
  Output:
  ```
  Links for entity 123:

    123 --[blocked by]--> 456
    123 --[blocked by]--> 789
  ```

#### Link Tree Command

- Syntax: `em link tree <entity_id>`
- Required argument: `entity_id`: Entity to display tree for
- Output: MUST print hierarchical tree showing:
  - Main entity (ID, title, state)
  - Related entities grouped by link type (children, blocking, blocked_by, parent)
- Example:
  ```bash
  em link tree 123
  ```
  Output:
  ```
  Entity: 123 Fix login bug (open)

  Children:
    - 456 Sub-task 1 (open)
    - 789 Sub-task 2 (closed)

  Blocking:
    - 321 Dependent feature (open)

  Blocked By:
    - 100 Prerequisite work (closed)
  ```

#### Link Cycle Command

- Syntax: `em link cycle`
- Output: MUST print all cycles found in the link graph
- Example:
  ```bash
  em link cycle
  ```
  Output (if cycles exist):
  ```
  Found 2 cycle(s):

  1. 123 -> 456 -> 789 -> 123
  2. 321 -> 654 -> 321
  ```
  Output (if no cycles):
  ```
  No cycles found
  ```

### Configuration Commands

#### Config Set Command

- Syntax: `em config set <key> <value> [options]`
- Required arguments:
  - `key`: Configuration key (e.g., "backend", "github.token")
  - `value`: Configuration value
- Optional arguments:
  - `--global`: Set global configuration instead of local
- Output: No output on success (or minimal confirmation)
- Example:
  ```bash
  em config set backend github
  em config set github.token ghp_... --global
  ```

#### Config Get Command

- Syntax: `em config get <key> [options]`
- Required argument: `key`: Configuration key to retrieve
- Optional arguments:
  - `--global`: Read only global configuration
- Output: MUST print the configuration value
- Example:
  ```bash
  em config get backend
  ```
  Output: `github`

#### Config Unset Command

- Syntax: `em config unset <key> [options]`
- Required argument: `key`: Configuration key to remove
- Optional arguments:
  - `--global`: Unset from global configuration instead of local
- Output: No output on success
- Example:
  ```bash
  em config unset github.owner
  ```

#### Config List Command

- Syntax: `em config list [options]`
- Optional arguments:
  - `--global`: List only global configuration
- Output: MUST print all configuration settings in key=value format
- Example:
  ```bash
  em config list
  ```
  Output:
  ```
  Configuration settings:

  backend = github
  github.owner = myusername
  github.repository = myrepo
  github.token = ghp_...xxxx
  ```

#### Init Command

- Syntax: `em init [options]`
- Optional arguments:
  - `--global`: Initialize global configuration instead of local
- Behavior:
  - MUST provide interactive prompts for backend selection
  - MUST show list of available backends (backlog, beads, github, markdown, notion, sqlite)
  - MUST validate backend selection
  - MUST prompt for backend-specific configuration fields
  - MUST show existing values as defaults when updating configuration
  - MUST use password-style input for sensitive fields (tokens)
  - MUST save configuration to local or global config based on flag
- Output: MUST print confirmation of backend initialization
- Example:
  ```bash
  em init --global
  ```
  Interactive prompts:
  ```
  Entity Manager Configuration
  Select the backend to use
  Available backends: backlog, beads, github, markdown, notion, sqlite
  Backend [github]: github
  GitHub owner []: myusername
  GitHub repository []: myrepo
  GitHub token: ••••••••

  Initialized github backend (global)
  ```

### Output Format

#### Human-Readable Output

- Default output MUST be human-readable and formatted.
- Output SHOULD use whitespace, indentation, and visual indicators (●/○) for clarity.
- Output headers SHOULD clearly indicate what data is being shown.

#### Machine-Parseable Output

- The CLI MAY provide a `--json` or `--output` flag for machine-parseable output.
- Machine-parseable output MUST be valid JSON or another structured format.
- Machine-parseable output MUST include all relevant data fields.

#### Error Messages

- Error messages MUST be clear and actionable.
- Error messages MUST indicate which operation failed.
- Error messages SHOULD suggest how to fix the error.
- Error messages for missing configuration MUST include example setup commands.

### Argument Parsing

#### Label Parsing

- Labels MUST support comma-separated values.
- Labels MAY use `key:value` format for structured labels.
- Labels without a colon MUST be treated as simple tags (key with empty value).
- Whitespace around labels and colons MUST be trimmed.
- Examples:
  - `"bug,priority:high"` → `{bug: "", priority: "high"}`
  - `" type : feature "` → `{type: "feature"}`

#### Filter Parsing

- Filters MUST use `key=value` format.
- Multiple filters MUST be comma-separated.
- Filters MUST support filtering by entity fields (status, assignee).
- Filters MAY support filtering by label keys.
- Whitespace around keys and values MUST be trimmed.
- Example: `"status=open,assignee=alice"`

#### ID Handling

- Entity IDs MUST be accepted as strings to support different ID formats.
- The CLI MUST pass entity IDs to backends without type conversion.
- Entity IDs MAY contain letters, numbers, and special characters (backend-dependent).

### Backend Selection

#### Automatic Backend Loading

- The CLI MUST determine the backend from configuration.
- The CLI MUST initialize the configured backend with its configuration.
- The CLI MUST provide clear error messages if backend is not configured.

#### Backend-Specific Validation

- The CLI MAY validate arguments against backend capabilities.
- The CLI MUST pass unsupported link types to the backend for validation.

### Exit Codes

- Exit code 0 MUST indicate success.
- Non-zero exit codes MUST indicate errors.
- Exit codes MAY be specific to error types (1 for general errors, 2 for configuration errors, etc.).

### Help and Documentation

#### Help Flag

- All commands MUST support a `--help` flag.
- Help output MUST show command syntax.
- Help output MUST list all arguments and options.
- Help output MUST include examples for common usage.

#### Documentation

- Command help SHOULD include brief descriptions.
- Help text SHOULD show default values for optional arguments.
- Help text SHOULD indicate required vs optional arguments.

### LLM Integration Considerations

#### Command Predictability

- Command output MUST be consistent across runs.
- Command output MUST not include ANSI codes or formatting that interferes with parsing.
- Error messages MUST be clear for LLMs to understand and act on.

#### Example Usage for LLMs

- LLMs SHOULD be able to chain commands (create → list → read).
- LLMs MUST be able to parse output to extract entity IDs.
- LLMs SHOULD use error messages to determine corrective actions.

#### Common Workflows

- Creating and assigning work: `em create "title" --assignee agent-name`
- Claiming work: `em list --filter "status=open" && em update <id> --assignee self --status "in-progress"`
- Checking dependencies: `em link tree <id>`

### Error Handling

#### Configuration Errors

- Missing backend configuration MUST produce an error with setup instructions.
- Missing repository configuration MUST indicate which settings are needed.
- Invalid configuration values MUST produce descriptive error messages.

#### Entity Errors

- Attempting to read a non-existent entity MUST produce an error.
- Attempting to update a non-existent entity MUST produce an error.
- Invalid entity IDs MUST produce appropriate errors from the backend.

#### Link Errors

- Attempting to create unsupported link types MUST list supported types.
- Attempting to link non-existent entities MUST produce an error.
- Cycle-related errors SHOULD suggest using `em link cycle` to diagnose.

### Performance

- Commands SHOULD complete quickly for common operations.
- List commands SHOULD handle large result sets efficiently.
- Backend API calls SHOULD be minimized where possible.

### Shell Completion

- The CLI MAY provide shell completion for commands and options.
- Completion MAY suggest entity IDs for relevant commands.
- Completion MAY suggest configuration keys for config commands.

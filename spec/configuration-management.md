# Configuration Management Specification

## Overview

The Configuration Management feature provides a flexible, hierarchical configuration system for the entity manager. It supports both repository-local (project-specific) and user-global configurations, allowing for both per-project customization and user-wide defaults.

## Purpose

Configuration management enables:
- Project-specific settings for different repositories
- User-wide defaults to avoid repetitive configuration
- Backend selection and configuration (GitHub, Beads, Notion)
- Authentication token management
- Flexible fallback behavior (local overrides global)

## Requirements

### Configuration Storage

#### Configuration Files

- Configuration MUST be stored in YAML format.
- Configuration files MUST be named `config.yaml`.
- Configuration files MUST be stored in a directory named `.entity-manager`.

#### Configuration Locations

- Local (repository-level) configuration MUST be stored in `.entity-manager/config.yaml` in the current working directory.
- Global (user-level) configuration MUST be stored in `.entity-manager/config.yaml` in the user's home directory (`~/.entity-manager/config.yaml`).
- The system MUST automatically create configuration directories if they don't exist.

#### Configuration Format

- Configuration MUST be stored as key-value pairs.
- Configuration keys MUST be strings.
- Configuration values MUST be strings.
- Configuration keys MAY use dot notation for hierarchical organization (e.g., `github.owner`, `github.token`).

### Configuration Hierarchy and Resolution

#### Configuration Scopes

- The system MUST support two configuration scopes: local and global.
- Local configuration applies to a specific repository/project.
- Global configuration applies across all projects for a user.

#### Configuration Precedence

- When reading configuration, the system MUST check local configuration first.
- If a key is not found in local configuration, the system MUST fall back to global configuration.
- If a key is not found in either, the system MUST return a default value or None.
- Local configuration values MUST override global configuration values.

#### Configuration Isolation

- Writing to local configuration MUST NOT modify global configuration.
- Writing to global configuration MUST NOT modify local configuration.
- Explicit global operations MUST use a `--global` flag to target global configuration.

### Configuration Operations

#### Read Configuration (get)

- The `get()` operation MUST accept a configuration key and an optional default value.
- The `get()` operation MUST return the value from local config if present.
- The `get()` operation MUST return the value from global config if not in local config.
- The `get()` operation MUST return the default value if the key is not found in either.
- The `get()` operation MUST return None if no default is provided and the key is not found.

#### Write Configuration (set)

- The `set()` operation MUST accept a configuration key and value.
- By default, the `set()` operation MUST write to local configuration.
- With the `--global` flag, the `set()` operation MUST write to global configuration.
- The `set()` operation MUST persist changes to the configuration file immediately.
- The `set()` operation MUST create the configuration directory if it doesn't exist.

#### Remove Configuration (unset)

- The `unset()` operation MUST accept a configuration key.
- By default, the `unset()` operation MUST remove the key from local configuration.
- With the `--global` flag, the `unset()` operation MUST remove the key from global configuration.
- The `unset()` operation MUST persist changes to the configuration file immediately.
- The `unset()` operation MUST succeed silently if the key doesn't exist (idempotent).

#### List Configuration (list)

- The `list()` operation MUST return all configuration settings.
- By default, the `list()` operation MUST return merged configuration (global + local, with local taking precedence).
- With the `--global` flag, the `list()` operation MUST return only global configuration.
- The `list()` operation MUST return results as a dictionary.
- The `list()` operation MUST redact sensitive values (tokens, passwords, secrets, api_keys, auth) when displaying.
- Redacted values MUST show first 4 and last 4 characters if longer than 8 characters, or "-redacted-" if 8 characters or less.

### Configuration Keys

#### Backend Selection

- The `backend` key MUST specify which backend to use (e.g., "github", "beads", "notion").
- The `backend` key MUST be a required configuration for the system to function.
- The `backend` key defaults to "markdown" if not set.

#### GitHub Backend Configuration

- The `github.owner` key MUST specify the GitHub repository owner (username or organization).
- The `github.repository` key MUST specify the GitHub repository name.
- The `github.token` key MUST specify the GitHub personal access token.
- Both `github.owner` and `github.repository` MUST be set for GitHub backend to function.
- The `github.token` key SHOULD be set globally (in user config) for security and convenience.

#### Backlog Backend Configuration

- The `backlog.path` key MAY specify the path to the backlog directory.
- The `backlog.path` key MAY default to `./backlog` if not set.
- The `backlog.path` key MUST point to a directory containing a `backlog/tasks/` subdirectory.

#### Beads Backend Configuration

- The `beads.project_path` key MAY specify the path to the beads project.
- The `beads.project_path` key MAY default to the current directory if not set.
- The `beads.project_path` key MUST be an absolute or relative path string.

#### Markdown Backend Configuration

- The `markdown.directory_path` key MAY specify the directory path for markdown files.
- The `markdown.directory_path` key MAY default to `.entity-manager/content` if not set.
- The `markdown.directory_path` key MUST be a valid directory path.

#### Notion Backend Configuration

- The `notion.token` key MUST specify the Notion integration token.
- The `notion.database_id` key MUST specify the Notion database ID to use.
- The `notion.token` key SHOULD be set globally (in user config) for security.

#### Redis Backend Configuration

- The `redis.host` key MAY specify the Redis server hostname.
- The `redis.host` key MAY default to `localhost` if not set.
- The `redis.port` key MAY specify the Redis server port.
- The `redis.port` key MAY default to `6379` if not set.
- The `redis.db` key MAY specify the Redis database number.
- The `redis.db` key MAY default to `0` if not set.
- The `redis.password` key MAY specify the Redis authentication password.
- The `redis.password` key SHOULD be set globally (in user config) for security.
- All Redis configuration keys are optional with sensible defaults.

#### SQLite Backend Configuration

- The `sqlite.db_path` key MUST specify the path to the SQLite database file.
- The `sqlite.db_path` key MAY default to `.em.db` if not set.
- The `sqlite.db_path` key MUST be a valid file path.

### Configuration File Format

#### YAML Structure

- Configuration files MUST be valid YAML.
- Configuration files SHOULD use flat key-value pairs for simple keys.
- Configuration files MAY use nested structures for grouped settings.
- Configuration files SHOULD NOT include comments or documentation (keep them minimal).

#### Example Format

```yaml
backend: github
github.owner: myusername
github.repository: myrepo
github.token: ghp_...
```

Or with nesting:

```yaml
backend: github
github:
  owner: myusername
  repository: myrepo
  token: ghp_...
```

### Configuration Loading and Parsing

#### File Loading

- The system MUST load configuration from YAML files at startup.
- The system MUST handle missing configuration files gracefully (treat as empty config).
- The system MUST create configuration files and directories on first write operation.
- The system MUST parse YAML safely (use `yaml.safe_load`).

#### Error Handling

- Invalid YAML in configuration files MUST raise a descriptive error.
- File read errors (permissions, disk full) MUST raise descriptive errors.
- File write errors MUST raise descriptive errors.
- The system MUST NOT crash on configuration errors; it should provide actionable error messages.

#### Configuration Validation

- The system MAY validate configuration values when they are set.
- The system MAY validate configuration values when they are read.
- Validation errors MUST provide clear messages about what's wrong and how to fix it.

### Configuration Caching

#### In-Memory Caching

- The system MAY cache configuration values in memory after loading.
- Cached configuration MUST be invalidated when configuration files are modified.
- Configuration operations MUST always read from or write to disk (no stale data).

#### Configuration Reload

- The system MAY provide a way to reload configuration without restarting.
- The system MAY watch configuration files for changes and reload automatically.

### CLI Integration

#### Config Commands

- The system MUST provide a `config set` command to set configuration values.
- The system MUST provide a `config get` command to read configuration values.
- The system MUST provide a `config unset` command to remove configuration values.
- The system MUST provide a `config list` command to show all configuration.
- The system MUST provide an `init` command for interactive configuration setup.

#### Init Command

- The `init` command MUST provide interactive prompts for backend selection and configuration.
- The `init` command MUST validate backend selection against available backends.
- The `init` command MUST prompt for backend-specific configuration based on the selected backend.
- The `init` command MUST show existing values as defaults when updating configuration.
- The `init` command MUST support password-style input for sensitive fields (tokens).
- The `init` command MUST support both local and global configuration via the `--global` flag.

#### Global Flag

- The `--global` flag MUST be supported on all config commands.
- The `--global` flag MUST target global configuration instead of local.
- The default behavior (without `--global`) MUST target local configuration.

#### Command Examples

```bash
# Set local configuration
em config set github.owner myusername
em config set github.repository myrepo

# Set global configuration
em config set github.token ghp_... --global
em config set backend github --global

# Read configuration (local with global fallback)
em config get backend

# Read global configuration only
em config get backend --global

# List all configuration
em config list

# List global configuration only
em config list --global

# Unset configuration
em config unset github.owner
```

### Security Considerations

#### Token Storage

- Authentication tokens (e.g., `github.token`, `notion.token`) SHOULD be stored in global configuration.
- Authentication tokens MUST NOT be committed to version control.
- The `.entity-manager` directory SHOULD be excluded from version control (in `.gitignore`).

#### File Permissions

- On Unix-like systems, configuration files SHOULD have restrictive permissions (e.g., 600 or 644).
- Global configuration files SHOULD have more restrictive permissions than local files.

#### Environment Variables

- The system MAY support reading configuration from environment variables.
- Environment variables SHOULD take precedence over file-based configuration.
- Environment variable configuration MUST follow naming conventions (e.g., `EM_BACKEND`, `EM_GITHUB_TOKEN`).

### Multi-Repository Support

#### Repository-Specific Configuration

- Local configuration allows different settings per repository.
- Each repository can have its own backend and settings.
- Global configuration provides defaults that apply to all repositories.

#### Configuration Inheritance

- Local configuration inherits from global configuration.
- Local configuration can override any global setting.
- Settings not overridden in local configuration fall back to global values.

### Error Messages and User Guidance

#### Missing Configuration

- When required configuration is missing, the error MUST specify which keys are missing.
- Error messages SHOULD provide example commands to fix the issue.
- Error messages SHOULD differentiate between local and global configuration.

#### Invalid Configuration

- Invalid configuration values MUST produce clear error messages.
- Error messages MUST indicate which key has an invalid value.
- Error messages SHOULD indicate what values are valid.

### Use Cases

#### Initial Setup

- Users MUST be able to set global defaults once (e.g., GitHub token).
- Users MUST be able to configure per-project settings easily.
- Setup SHOULD require minimal commands (3-5 commands maximum).

#### Backend Switching

- Users MUST be able to switch backends by changing the `backend` configuration.
- Switching backends SHOULD NOT require re-entering global credentials.

#### Team Collaboration

- Local configuration MAY be committed to version control for team settings (excluding sensitive data).
- Team members SHOULD use global configuration for personal credentials.
- The `.entity-manager` directory SHOULD be in `.gitignore` to prevent committing sensitive data.

### Configuration Migration

#### Version Compatibility

- The system SHOULD handle changes to configuration format across versions.
- The system MAY provide migration scripts for configuration format changes.
- The system SHOULD warn about deprecated configuration keys.

### Testing Considerations

- The configuration system MUST be testable with mock file systems.
- Configuration operations MUST be thread-safe if the system supports concurrent access.
- The system SHOULD provide a way to reset configuration for testing.

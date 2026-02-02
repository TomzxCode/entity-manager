"""CLI for entity manager."""

from typing import Annotated, Any, Literal

import structlog
from cyclopts import App, Parameter

from entity_manager.backend import Backend
from entity_manager.backends.backlog import BacklogBackend
from entity_manager.backends.beads import BeadsBackend
from entity_manager.backends.github import GitHubBackend
from entity_manager.backends.markdown import MarkdownBackend
from entity_manager.backends.notion import NotionBackend
from entity_manager.backends.redis import RedisBackend
from entity_manager.backends.sqlite import SQLiteBackend
from entity_manager.config import get_config
from entity_manager.config_commands import config_app, init
from entity_manager.link_commands import link_app
from entity_manager.type_commands import type_app
from entity_manager.type_manager import TypeManager
from entity_manager.validation import coerce_property_value

logger = structlog.get_logger()

app = App(
    help="Entity Manager - An entity manager for LLMs",
)

app.command(link_app)
app.command(config_app)
app.command(type_app)
app.command(init)


def configure_logging(log_level: str) -> None:
    """Configure structlog with the specified log level."""
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(min_level=log_level.lower()))


def get_backend() -> Backend:
    """Get the configured backend."""

    config = get_config()
    backend_type = config.get("backend", "markdown")

    if backend_type == "backlog":
        backlog_path = config.get("backlog.path")
        return BacklogBackend(backlog_path=backlog_path)
    elif backend_type == "beads":
        project_path = config.get("beads.project_path")
        return BeadsBackend(project_path=project_path)
    elif backend_type == "github":
        owner = config.get("github.owner")
        repo = config.get("github.repository")
        token = config.get("github.token")

        if not owner or not repo:
            raise ValueError(
                "GitHub owner and repo not configured. Set them using:\n"
                "  em config set github.owner <owner>\n"
                "  em config set github.repository <repo>"
            )
        return GitHubBackend(owner=owner, repo=repo, token=token)
    elif backend_type == "markdown":
        directory_path = config.get("markdown.directory_path", ".entity-manager/content")
        return MarkdownBackend(directory_path=directory_path)
    elif backend_type == "notion":
        token = config.get("notion.token")
        database_id = config.get("notion.database_id")

        if not token or not database_id:
            raise ValueError(
                "Notion token and database ID not configured. Set them using:\n"
                "  em config set notion.token <token> --global\n"
                "  em config set notion.database_id <database_id>"
            )
        return NotionBackend(token=token, database_id=database_id)
    elif backend_type == "redis":
        host = config.get("redis.host", "localhost")
        port = int(config.get("redis.port", "6379"))
        db = int(config.get("redis.db", "0"))
        password = config.get("redis.password")
        return RedisBackend(host=host, port=port, db=db, password=password)
    elif backend_type == "sqlite":
        db_path = config.get("sqlite.db_path")
        return SQLiteBackend(db_path=db_path)
    else:
        raise ValueError(f"Unknown backend: {backend_type}")


def _parse_properties(properties: list[str]) -> dict[str, Any]:
    """Parse property arguments from CLI.

    Supports both key=value format and standalone values.
    """
    result: dict[str, Any] = {}
    i = 0
    while i < len(properties):
        prop = properties[i]
        if "=" in prop:
            key, value = prop.split("=", 1)
            result[key.strip()] = value.strip()
            i += 1
        else:
            # Standalone value - treat as key with empty value
            # Or if next arg starts with -, treat as key without value
            if i + 1 < len(properties) and not properties[i + 1].startswith("-"):
                result[prop] = properties[i + 1]
                i += 2
            else:
                result[prop] = ""
                i += 1
    return result


@app.command
def create(
    *tokens: str,
    type: str = "default",
    properties: list[str] = [],
) -> None:
    """Create a new entity.

    Usage:
      em create type prop=value prop=value
      em create --type type prop=value prop=value
      em create --type type --properties prop=value --properties prop=value
    """
    import sys

    try:
        backend = get_backend()
        type_manager = TypeManager()

        # Handle positional arguments
        # If first token doesn't contain '=', it's the type name
        all_props = [*properties, *tokens]
        entity_type_name = type

        if all_props and "=" not in all_props[0] and not all_props[0].startswith("--"):
            # First positional arg is the type
            entity_type_name = all_props[0]
            all_props = all_props[1:]

        # Get type definition
        entity_type = type_manager.get_type(entity_type_name)

        # Parse properties
        properties_dict = _parse_properties(all_props)

        # Apply type defaults
        defaults = entity_type.get_property_defaults()
        for key, value in defaults.items():
            if key not in properties_dict:
                properties_dict[key] = value

        # Collect required properties
        required_props = [p.name for p in entity_type.properties if p.required]

        # Validate against type
        missing = [p for p in required_props if p not in properties_dict]
        if missing:
            print(
                f"Error: Missing required properties for type '{entity_type_name}': {', '.join(missing)}",
                file=sys.stderr,
            )
            sys.exit(1)

        entity = backend.create(type=entity_type_name, properties=properties_dict)
        title = properties_dict.get("title", "")
        print(f"Created entity {entity.id}: {title}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled", file=sys.stderr)
        sys.exit(1)


@app.command
def read(entity_id: str) -> None:
    """Read an entity by ID."""
    backend = get_backend()
    entity = backend.read(entity_id)

    print(f"Entity: {entity.id}")
    print(f"Type: {entity.type}")
    print("Properties:")
    for key, value in entity.properties.items():
        print(f"  {key}: {value}")
    if entity.metadata:
        print(f"URL: {entity.metadata.get('url', 'N/A')}")


@app.command
def update(
    entity_id: str,
    *properties: str,
    type: str | None = None,
) -> None:
    """Update an entity.

    Properties can be specified as key=value pairs.
    Example: em update abc123 --type bug title="Updated title" severity=low
    """
    import sys

    try:
        backend = get_backend()
        type_manager = TypeManager()

        # Get current entity
        current = backend.read(entity_id)

        # Determine type to use
        entity_type_name = type if type else current.type
        entity_type = type_manager.get_type(entity_type_name)

        # Start with current properties
        properties_dict = current.properties.copy()

        # Parse and update properties
        if properties:
            parsed = _parse_properties(properties)
            properties_dict.update(parsed)

            # Coerce and validate new/updated values
            for prop_def in entity_type.properties:
                if prop_def.name in parsed:
                    value = properties_dict[prop_def.name]
                    try:
                        coerced = coerce_property_value(value, prop_def.type)
                        properties_dict[prop_def.name] = coerced
                    except Exception as e:
                        print(f"Error: Invalid value for property '{prop_def.name}': {e}", file=sys.stderr)
                        sys.exit(1)

                    valid, error = entity_type.validate_property(prop_def.name, coerced)
                    if not valid:
                        print(f"Error: {error}", file=sys.stderr)
                        sys.exit(1)

        entity = backend.update(entity_id=entity_id, type=type, properties=properties_dict)
        title = properties_dict.get("title", "")
        print(f"Updated entity {entity.id}: {title}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled", file=sys.stderr)
        sys.exit(1)


@app.command
def delete(*entity_ids: str) -> None:
    """Delete one or more entities."""
    backend = get_backend()
    backend.delete((*entity_ids,))
    print(f"Deleted {len(entity_ids)} entity(ies)")


@app.command
def list_entities(
    filter: str | None = None,
    sort: str | None = None,
    limit: int | None = None,
) -> None:
    """List entities with optional filtering, sorting, and limiting."""
    backend = get_backend()

    filters = None
    if filter:
        filters = {}
        for f in filter.split(","):
            if "=" in f:
                key, value = f.split("=", 1)
                filters[key.strip()] = value.strip()

    entities = backend.list_entities(filters=filters, sort_by=sort, limit=limit)

    print(f"Found {len(entities)} entity(ies):\n")
    for entity in entities:
        title = entity.properties.get("title", "")
        status = entity.properties.get("status", "open")
        status_marker = "●" if status == "open" else "○"
        print(f"{status_marker} {entity.id}: {title} [{entity.type}]")


@app.meta.default
def main(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "critical",
) -> None:
    """Main entry point with global options."""
    configure_logging(log_level)
    app(tokens)


if __name__ == "__main__":
    app.meta()

"""CLI for entity manager."""

import os
from typing import Annotated, Literal

import structlog
from cyclopts import App, Parameter
from dotenv import load_dotenv

from entity_manager.backend import Backend
from entity_manager.backends import BeadsBackend, GitHubBackend

load_dotenv()

logger = structlog.get_logger()

app = App(
    help="Entity Manager - An entity manager for LLMs",
)
link_app = App(name="link", help="Manage links between entities")
config_app = App(name="config", help="Manage configuration")

app.command(link_app)
app.command(config_app)


def configure_logging(log_level: str) -> None:
    """Configure structlog with the specified log level."""
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(min_level=log_level.lower()))


def get_backend() -> Backend:
    """Get the configured backend."""
    backend_type = os.getenv("EM_BACKEND", "github")
    if backend_type == "github":
        owner = os.getenv("EM_GITHUB_OWNER")
        repo = os.getenv("EM_GITHUB_REPO")
        if not owner or not repo:
            raise ValueError("EM_GITHUB_OWNER and EM_GITHUB_REPO environment variables required")
        return GitHubBackend(owner=owner, repo=repo)
    elif backend_type == "beads":
        project_path = os.getenv("EM_BEADS_PROJECT_PATH")
        return BeadsBackend(project_path=project_path)
    else:
        raise ValueError(f"Unknown backend: {backend_type}")


@app.command
def create(
    title: str,
    description: str = "",
    labels: str = "",
    assignee: str | None = None,
) -> None:
    """Create a new entity."""
    backend = get_backend()
    labels_dict = {}
    if labels:
        for label in labels.split(","):
            label = label.strip()
            if ":" in label:
                key, value = label.split(":", 1)
                labels_dict[key.strip()] = value.strip()
            else:
                labels_dict[label] = ""

    entity = backend.create(
        title=title,
        description=description,
        labels=labels_dict,
        assignee=assignee,
    )
    print(f"Created entity {entity.id}: {entity.title}")


@app.command
def read(entity_id: str) -> None:
    """Read an entity by ID."""
    backend = get_backend()
    entity = backend.read(entity_id)

    print(f"Entity: {entity.id}")
    print(f"Title: {entity.title}")
    print(f"Description: {entity.description}")
    print(f"Status: {entity.status}")
    if entity.labels:
        labels_str = ", ".join([f"{k}:{v}" if v else k for k, v in entity.labels.items()])
        print(f"Labels: {labels_str}")
    if entity.assignee:
        print(f"Assignee: {entity.assignee}")
    if entity.metadata:
        print(f"URL: {entity.metadata.get('url', 'N/A')}")


@app.command
def update(
    entity_id: str,
    title: str | None = None,
    description: str | None = None,
    labels: str | None = None,
    status: str | None = None,
    assignee: str | None = None,
) -> None:
    """Update an entity."""
    backend = get_backend()

    labels_dict = None
    if labels:
        labels_dict = {}
        for label in labels.split(","):
            label = label.strip()
            if ":" in label:
                key, value = label.split(":", 1)
                labels_dict[key.strip()] = value.strip()
            else:
                labels_dict[label] = ""

    entity = backend.update(
        entity_id=entity_id,
        title=title,
        description=description,
        labels=labels_dict,
        status=status,
        assignee=assignee,
    )
    print(f"Updated entity {entity.id}: {entity.title}")


@app.command
def delete(*entity_ids: str) -> None:
    """Delete one or more entities."""
    backend = get_backend()
    backend.delete(list(entity_ids))
    print(f"Deleted {len(entity_ids)} entity(ies)")


@app.command
def list(
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
        status_marker = "●" if entity.status == "open" else "○"
        labels_str = ""
        if entity.labels:
            labels_str = " [" + ", ".join([f"{k}:{v}" if v else k for k, v in entity.labels.items()]) + "]"
        print(f"{status_marker} {entity.id}: {entity.title}{labels_str}")


@link_app.command
def add(
    source_id: str,
    *target_ids: str,
    type: str = "relates-to",
) -> None:
    """Add links from source entity to target entities."""
    backend = get_backend()
    backend.add_link(source_id, list(target_ids), type)
    print(f"Added {len(target_ids)} link(s) from {source_id}")


@link_app.command
def remove(
    source_id: str,
    *target_ids: str,
    type: str = "relates-to",
    recursive: bool = False,
) -> None:
    """Remove links from source entity to target entities."""
    backend = get_backend()
    backend.remove_link(source_id, list(target_ids), type, recursive)
    print(f"Removed {len(target_ids)} link(s) from {source_id}")


@link_app.command(name="list")
def list_links(
    entity_id: str,
    type: str | None = None,
) -> None:
    """List all links for an entity."""
    backend = get_backend()
    links = backend.list_links(entity_id, type)

    if not links:
        print(f"No links found for entity {entity_id}")
        return

    print(f"Links for entity {entity_id}:\n")
    for link in links:
        print(f"  {link.source_id} --[{link.link_type}]--> {link.target_id}")


@link_app.command
def tree(entity_id: str) -> None:
    """Display the link tree of an entity."""
    backend = get_backend()
    tree = backend.get_link_tree(entity_id)

    # Print entity
    entity = tree["entity"]
    print(f"Entity: {entity['id']} {entity['title']} ({entity['state']})\n")

    # Print links dynamically
    links = tree["links"]

    for link_type, link_data in links.items():
        if not link_data:
            continue

        # Format the link type for display
        display_name = link_type.replace("_", " ").title()

        print(f"{display_name}:")
        for item in link_data:
            print(f"  - {item['id']} {item['title']}")
        print()


@link_app.command
def cycle() -> None:
    """Find and display cycles in links."""
    backend = get_backend()
    cycles = backend.find_cycles()

    if not cycles:
        print("No cycles found")
        return

    print(f"Found {len(cycles)} cycle(s):\n")
    for i, cycle in enumerate(cycles, 1):
        cycle_str = " -> ".join([f"{eid}" for eid in cycle])
        print(f"{i}. {cycle_str} -> {cycle[0]}")


@config_app.command
def set_config(key: str, value: str) -> None:
    """Set a configuration setting."""
    backend = get_backend()
    backend.set_config(key, value)
    print(f"Set {key} = {value}")


@config_app.command
def unset_config(key: str) -> None:
    """Unset a configuration setting."""
    backend = get_backend()
    backend.unset_config(key)
    print(f"Unset {key}")


@config_app.command
def get(key: str) -> None:
    """Get the value of a configuration setting."""
    backend = get_backend()
    value = backend.get_config(key)
    if value is None:
        print(f"{key} is not set")
    else:
        print(f"{key} = {value}")


@config_app.command(name="list")
def list_config() -> None:
    """List all configuration settings."""
    backend = get_backend()
    config = backend.list_config()

    if not config:
        print("No configuration settings")
        return

    print("Configuration settings:\n")
    for key, value in config.items():
        print(f"{key} = {value}")


@app.meta.default
def main(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
) -> None:
    """Main entry point with global options."""
    configure_logging(log_level)
    app(tokens)


if __name__ == "__main__":
    app.meta()

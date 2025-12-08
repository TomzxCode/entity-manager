"""CLI for entity manager."""

from typing import Annotated, Literal

import structlog
from cyclopts import App, Parameter

from entity_manager.backend import Backend
from entity_manager.backends import BeadsBackend, GitHubBackend
from entity_manager.config import get_config
from entity_manager.config_commands import config_app
from entity_manager.link_commands import link_app

logger = structlog.get_logger()

app = App(
    help="Entity Manager - An entity manager for LLMs",
)

app.command(link_app)
app.command(config_app)


def configure_logging(log_level: str) -> None:
    """Configure structlog with the specified log level."""
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(min_level=log_level.lower()))


def get_backend() -> Backend:
    """Get the configured backend."""

    config = get_config()
    backend_type = config.get("backend", "github")

    if backend_type == "github":
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
    elif backend_type == "beads":
        project_path = config.get("beads.project_path")
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

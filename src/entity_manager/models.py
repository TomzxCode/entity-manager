"""Data models for entity manager."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Entity:
    """Represents an entity with attributes and metadata."""

    id: str
    title: str
    description: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    assignee: str | None = None
    status: str = "open"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Link:
    """Represents a link between entities."""

    source_id: str
    target_id: str
    link_type: str = "relates_to"

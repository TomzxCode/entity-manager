"""Backend interface for entity management."""

from abc import ABC, abstractmethod
from typing import Any

from entity_manager.models import Entity, Link


class Backend(ABC):
    """Abstract base class for entity management backends."""

    @abstractmethod
    def create(
        self,
        title: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Create a new entity."""
        pass

    @abstractmethod
    def read(self, entity_id: str) -> Entity:
        """Read an entity by ID."""
        pass

    @abstractmethod
    def update(
        self,
        entity_id: str,
        title: str | None = None,
        description: str | None = None,
        labels: dict[str, str] | None = None,
        status: str | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Update an entity."""
        pass

    @abstractmethod
    def delete(self, entity_ids: list[str]) -> None:
        """Delete one or more entities."""
        pass

    @abstractmethod
    def list_entities(
        self,
        filters: dict[str, str] | None = None,
        sort_by: str | None = None,
        limit: int | None = None,
    ) -> list[Entity]:
        """List entities with optional filtering, sorting, and limiting."""
        pass

    @abstractmethod
    def add_link(self, source_id: str, target_ids: list[str], link_type: str) -> None:
        """Add links from source entity to target entities."""
        pass

    @abstractmethod
    def remove_link(self, source_id: str, target_ids: list[str], link_type: str, recursive: bool = False) -> None:
        """Remove links from source entity to target entities."""
        pass

    @abstractmethod
    def list_links(self, entity_id: str, link_type: str | None = None) -> list[Link]:
        """List all links for an entity."""
        pass

    @abstractmethod
    def get_link_tree(self, entity_id: str) -> dict[str, Any]:
        """Get the link tree for an entity.

        Returns:
            Dictionary with structure:
            {
                "entity": {
                    "id": str,
                    "title": str,
                    "state": str
                },
                "links": {
                    "children": list[dict],
                    "blocking": list[dict],
                    "blocked_by": list[dict],
                    "parent": list[dict]
                }
            }
        """
        pass

    @abstractmethod
    def find_cycles(self) -> list[list[str]]:
        """Find and return all cycles in the link graph."""
        pass

    @abstractmethod
    def get_config(self, key: str) -> str | None:
        """Get a configuration value."""
        pass

    @abstractmethod
    def set_config(self, key: str, value: str) -> None:
        """Set a configuration value."""
        pass

    @abstractmethod
    def unset_config(self, key: str) -> None:
        """Unset a configuration value."""
        pass

    @abstractmethod
    def list_config(self) -> dict[str, str]:
        """List all configuration settings."""
        pass

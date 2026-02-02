"""Tests for backend interface."""

from typing import Any

from entity_manager.backend import Backend
from entity_manager.models import Entity, Link


class MockBackend(Backend):
    """Mock backend for testing."""

    def __init__(self) -> None:
        """Initialize mock backend."""
        self.entities: dict[str, Entity] = {}
        self.links: list[Link] = []
        self.config: dict[str, str] = {}
        self._next_id = 1

    def create(
        self,
        type: str = "default",
        properties: dict[str, Any] | None = None,
    ) -> Entity:
        """Create a new entity."""
        entity_id = str(self._next_id)
        entity = Entity(
            id=entity_id,
            type=type,
            properties=properties or {},
        )
        self.entities[entity_id] = entity
        self._next_id += 1
        return entity

    def read(self, entity_id: str) -> Entity:
        """Read an entity by ID."""
        return self.entities[entity_id]

    def update(
        self,
        entity_id: str,
        type: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> Entity:
        """Update an entity."""
        entity = self.entities[entity_id]
        if type is not None:
            entity.type = type
        if properties is not None:
            entity.properties.update(properties)
        return entity

    def delete(self, entity_ids: list[str]) -> None:
        """Delete entities."""
        for eid in entity_ids:
            del self.entities[eid]

    def list_entities(
        self,
        filters: dict[str, str] | None = None,
        sort_by: str | None = None,
        limit: int | None = None,
    ) -> list[Entity]:
        """List entities."""
        entities = list(self.entities.values())
        if filters and "status" in filters:
            entities = [e for e in entities if e.properties.get("status") == filters["status"]]
        if limit:
            entities = entities[:limit]
        return entities

    def add_link(self, source_id: str, target_ids: list[str], link_type: str) -> None:
        """Add links."""
        for target_id in target_ids:
            self.links.append(Link(source_id, target_id, link_type))

    def remove_link(self, source_id: str, target_ids: list[str], link_type: str, recursive: bool = False) -> None:
        """Remove links."""
        self.links = [
            link
            for link in self.links
            if not (link.source_id == source_id and link.target_id in target_ids and link.link_type == link_type)
        ]

    def list_links(self, entity_id: str, link_type: str | None = None) -> list[Link]:
        """List links."""
        links = [link for link in self.links if link.source_id == entity_id]
        if link_type:
            links = [link for link in links if link.link_type == link_type]
        return links

    def get_link_tree(self, entity_id: str) -> dict:
        """Get link tree."""
        entity = self.entities.get(entity_id)
        return {
            "entity": {
                "id": entity_id,
                "title": entity.properties.get("title", "") if entity else "",
                "state": entity.properties.get("status", "open") if entity else "open",
            },
            "links": {
                "children": [],
                "blocking": [],
                "blocked_by": [],
                "parent": [],
            },
        }

    def find_cycles(self) -> list[list[str]]:
        """Find cycles."""
        return []

    def get_config(self, key: str) -> str | None:
        """Get config."""
        return self.config.get(key)

    def set_config(self, key: str, value: str) -> None:
        """Set config."""
        self.config[key] = value

    def unset_config(self, key: str) -> None:
        """Unset config."""
        self.config.pop(key, None)

    def list_config(self) -> dict[str, str]:
        """List config."""
        return self.config.copy()


def test_create_entity() -> None:
    """Test creating an entity."""
    backend = MockBackend()
    entity = backend.create(properties={"title": "Test Task", "description": "Test description"})
    assert entity.id == "1"
    assert entity.properties["title"] == "Test Task"
    assert entity.properties["description"] == "Test description"


def test_read_entity() -> None:
    """Test reading an entity."""
    backend = MockBackend()
    entity = backend.create(properties={"title": "Test Task"})
    read_entity = backend.read(entity.id)
    assert read_entity.id == entity.id
    assert read_entity.properties["title"] == entity.properties["title"]


def test_update_entity() -> None:
    """Test updating an entity."""
    backend = MockBackend()
    entity = backend.create(properties={"title": "Old Title"})
    updated = backend.update(entity.id, properties={"title": "New Title"})
    assert updated.properties["title"] == "New Title"


def test_delete_entity() -> None:
    """Test deleting an entity."""
    backend = MockBackend()
    entity = backend.create(properties={"title": "Test Task"})
    backend.delete([entity.id])
    assert entity.id not in backend.entities


def test_list_entities() -> None:
    """Test listing entities."""
    backend = MockBackend()
    backend.create(properties={"title": "Task 1"})
    backend.create(properties={"title": "Task 2"})
    backend.create(properties={"title": "Task 3"})
    entities = backend.list_entities()
    assert len(entities) == 3


def test_add_link() -> None:
    """Test adding links."""
    backend = MockBackend()
    e1 = backend.create(properties={"title": "Task 1"})
    e2 = backend.create(properties={"title": "Task 2"})
    backend.add_link(e1.id, [e2.id], "blocks")
    links = backend.list_links(e1.id)
    assert len(links) == 1
    assert links[0].target_id == e2.id


def test_config() -> None:
    """Test configuration management."""
    backend = MockBackend()
    backend.set_config("key", "value")
    assert backend.get_config("key") == "value"
    backend.unset_config("key")
    assert backend.get_config("key") is None

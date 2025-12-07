"""Tests for backend interface."""

from entity_manager.backend import Backend
from entity_manager.models import Entity, Link


class MockBackend(Backend):
    """Mock backend for testing."""

    def __init__(self) -> None:
        """Initialize mock backend."""
        self.entities: dict[int, Entity] = {}
        self.links: list[Link] = []
        self.config: dict[str, str] = {}
        self._next_id = 1

    def create(
        self,
        title: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Create a new entity."""
        entity = Entity(
            id=self._next_id,
            title=title,
            description=description,
            labels=labels or {},
            assignee=assignee,
        )
        self.entities[self._next_id] = entity
        self._next_id += 1
        return entity

    def read(self, entity_id: int) -> Entity:
        """Read an entity by ID."""
        return self.entities[entity_id]

    def update(
        self,
        entity_id: int,
        title: str | None = None,
        description: str | None = None,
        labels: dict[str, str] | None = None,
        status: str | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Update an entity."""
        entity = self.entities[entity_id]
        if title:
            entity.title = title
        if description is not None:
            entity.description = description
        if labels:
            entity.labels = labels
        if status:
            entity.status = status
        if assignee:
            entity.assignee = assignee
        return entity

    def delete(self, entity_ids: list[int]) -> None:
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
            entities = [e for e in entities if e.status == filters["status"]]
        if limit:
            entities = entities[:limit]
        return entities

    def add_link(self, source_id: int, target_ids: list[int], link_type: str) -> None:
        """Add links."""
        for target_id in target_ids:
            self.links.append(Link(source_id, target_id, link_type))

    def remove_link(self, source_id: int, target_ids: list[int], link_type: str, recursive: bool = False) -> None:
        """Remove links."""
        self.links = [
            link
            for link in self.links
            if not (link.source_id == source_id and link.target_id in target_ids and link.link_type == link_type)
        ]

    def list_links(self, entity_id: int, link_type: str | None = None) -> list[Link]:
        """List links."""
        links = [link for link in self.links if link.source_id == entity_id]
        if link_type:
            links = [link for link in links if link.link_type == link_type]
        return links

    def get_link_tree(self, entity_id: int) -> dict:
        """Get link tree."""
        entity = self.entities.get(entity_id)
        return {
            "entity": {
                "id": str(entity_id),
                "title": entity.title if entity else "",
                "state": entity.status if entity else "open",
            },
            "links": {
                "children": [],
                "blocking": [],
                "blocked_by": [],
                "parent": [],
            },
        }

    def find_cycles(self) -> list[list[int]]:
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
    entity = backend.create("Test Task", description="Test description")
    assert entity.id == 1
    assert entity.title == "Test Task"
    assert entity.description == "Test description"


def test_read_entity() -> None:
    """Test reading an entity."""
    backend = MockBackend()
    entity = backend.create("Test Task")
    read_entity = backend.read(entity.id)
    assert read_entity.id == entity.id
    assert read_entity.title == entity.title


def test_update_entity() -> None:
    """Test updating an entity."""
    backend = MockBackend()
    entity = backend.create("Old Title")
    updated = backend.update(entity.id, title="New Title")
    assert updated.title == "New Title"


def test_delete_entity() -> None:
    """Test deleting an entity."""
    backend = MockBackend()
    entity = backend.create("Test Task")
    backend.delete([entity.id])
    assert entity.id not in backend.entities


def test_list_entities() -> None:
    """Test listing entities."""
    backend = MockBackend()
    backend.create("Task 1")
    backend.create("Task 2")
    backend.create("Task 3")
    entities = backend.list_entities()
    assert len(entities) == 3


def test_add_link() -> None:
    """Test adding links."""
    backend = MockBackend()
    e1 = backend.create("Task 1")
    e2 = backend.create("Task 2")
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

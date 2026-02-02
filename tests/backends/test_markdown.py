"""Tests for markdown backend."""

import shutil
from pathlib import Path

import pytest

from entity_manager.backends.markdown import MarkdownBackend


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for markdown files."""
    return tmp_path / "markdown_test"


@pytest.fixture
def markdown_backend(temp_dir: Path) -> MarkdownBackend:
    """Create a markdown backend with a temporary directory."""
    # Clean up any existing test directory
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    return MarkdownBackend(directory_path=str(temp_dir))


def test_create_entity(markdown_backend: MarkdownBackend) -> None:
    """Test creating a new entity."""
    entity = markdown_backend.create(
        title="Test Entity",
        description="Test description",
        labels={"priority": "high", "type": "bug"},
        assignee="testuser",
    )

    assert entity.id.startswith("md-")
    assert entity.title == "Test Entity"
    assert entity.description == "Test description"
    assert entity.labels == {"priority": "high", "type": "bug"}
    assert entity.assignee == "testuser"
    assert entity.status == "open"

    # Verify file was created
    file_path = markdown_backend._get_entity_path(entity.id)
    assert file_path.exists()


def test_read_entity(markdown_backend: MarkdownBackend) -> None:
    """Test reading an entity."""
    created = markdown_backend.create(title="Test Entity", description="Test description")

    entity = markdown_backend.read(created.id)

    assert entity.id == created.id
    assert entity.title == "Test Entity"
    assert entity.description == "Test description"


def test_read_nonexistent_entity(markdown_backend: MarkdownBackend) -> None:
    """Test reading a non-existent entity raises an error."""
    with pytest.raises(ValueError, match="Entity not found"):
        markdown_backend.read("nonexistent-id")


def test_update_entity(markdown_backend: MarkdownBackend) -> None:
    """Test updating an entity."""
    entity = markdown_backend.create(title="Original Title", description="Original description")

    updated = markdown_backend.update(
        entity.id,
        title="Updated Title",
        description="Updated description",
        status="closed",
        assignee="newuser",
    )

    assert updated.id == entity.id
    assert updated.title == "Updated Title"
    assert updated.description == "Updated description"
    assert updated.status == "closed"
    assert updated.assignee == "newuser"


def test_update_partial_entity(markdown_backend: MarkdownBackend) -> None:
    """Test updating only some fields of an entity."""
    entity = markdown_backend.create(title="Title", description="Description", labels={"key": "value"}, assignee="user")

    updated = markdown_backend.update(entity.id, title="New Title")

    assert updated.title == "New Title"
    assert updated.description == "Description"  # Unchanged
    assert updated.labels == {"key": "value"}  # Unchanged
    assert updated.assignee == "user"  # Unchanged


def test_delete_entity(markdown_backend: MarkdownBackend) -> None:
    """Test deleting entities."""
    entity1 = markdown_backend.create(title="Entity 1")
    entity2 = markdown_backend.create(title="Entity 2")
    entity3 = markdown_backend.create(title="Entity 3")

    # Delete entity1 and entity2
    markdown_backend.delete([entity1.id, entity2.id])

    # Verify files are deleted
    assert not markdown_backend._get_entity_path(entity1.id).exists()
    assert not markdown_backend._get_entity_path(entity2.id).exists()
    assert markdown_backend._get_entity_path(entity3.id).exists()


def test_delete_nonexistent_entity(markdown_backend: MarkdownBackend) -> None:
    """Test deleting non-existent entities succeeds silently."""
    # Should not raise an error
    markdown_backend.delete(["nonexistent-id"])


def test_delete_empty_list(markdown_backend: MarkdownBackend) -> None:
    """Test deleting with an empty list succeeds silently."""
    # Should not raise an error
    markdown_backend.delete([])


def test_list_entities(markdown_backend: MarkdownBackend) -> None:
    """Test listing entities."""
    for i in range(1, 4):
        markdown_backend.create(title=f"Entity {i}")

    entities = markdown_backend.list_entities()

    assert len(entities) == 3
    titles = {e.title for e in entities}
    assert titles == {"Entity 1", "Entity 2", "Entity 3"}


def test_list_entities_with_filter_by_status(markdown_backend: MarkdownBackend) -> None:
    """Test listing entities filtered by status."""
    entity1 = markdown_backend.create(title="Open Entity")
    entity2 = markdown_backend.create(title="Closed Entity")

    markdown_backend.update(entity2.id, status="closed")

    open_entities = markdown_backend.list_entities(filters={"status": "open"})
    closed_entities = markdown_backend.list_entities(filters={"status": "closed"})

    assert len(open_entities) == 1
    assert open_entities[0].id == entity1.id
    assert len(closed_entities) == 1
    assert closed_entities[0].id == entity2.id


def test_list_entities_with_filter_by_assignee(markdown_backend: MarkdownBackend) -> None:
    """Test listing entities filtered by assignee."""
    markdown_backend.create(title="Entity 1", assignee="user1")
    markdown_backend.create(title="Entity 2", assignee="user2")

    user1_entities = markdown_backend.list_entities(filters={"assignee": "user1"})

    assert len(user1_entities) == 1
    assert user1_entities[0].title == "Entity 1"


def test_list_entities_with_sort_by_title(markdown_backend: MarkdownBackend) -> None:
    """Test listing entities sorted by title."""
    markdown_backend.create(title="Zebra")
    markdown_backend.create(title="Apple")
    markdown_backend.create(title="Middle")

    entities_asc = markdown_backend.list_entities(sort_by="title")
    entities_desc = markdown_backend.list_entities(sort_by="-title")

    assert [e.title for e in entities_asc] == ["Apple", "Middle", "Zebra"]
    assert [e.title for e in entities_desc] == ["Zebra", "Middle", "Apple"]


def test_list_entities_with_limit(markdown_backend: MarkdownBackend) -> None:
    """Test listing entities with a limit."""
    for i in range(10):
        markdown_backend.create(title=f"Entity {i}")

    entities = markdown_backend.list_entities(limit=5)

    assert len(entities) == 5


def test_add_link(markdown_backend: MarkdownBackend) -> None:
    """Test adding a link between entities."""
    entity1 = markdown_backend.create(title="Entity 1")
    entity2 = markdown_backend.create(title="Entity 2")

    markdown_backend.add_link(entity1.id, [entity2.id], "blocked by")

    links = markdown_backend.list_links(entity1.id)

    assert len(links) == 1
    assert links[0].source_id == entity1.id
    assert links[0].target_id == entity2.id
    assert links[0].link_type == "blocked by"


def test_add_multiple_links(markdown_backend: MarkdownBackend) -> None:
    """Test adding links to multiple targets."""
    entity1 = markdown_backend.create(title="Entity 1")
    entity2 = markdown_backend.create(title="Entity 2")
    entity3 = markdown_backend.create(title="Entity 3")

    markdown_backend.add_link(entity1.id, [entity2.id, entity3.id], "blocking")

    links = markdown_backend.list_links(entity1.id)

    assert len(links) == 2
    target_ids = {link.target_id for link in links}
    assert target_ids == {entity2.id, entity3.id}


def test_add_link_nonexistent_entity(markdown_backend: MarkdownBackend) -> None:
    """Test adding a link to a non-existent entity raises an error."""
    entity1 = markdown_backend.create(title="Entity 1")

    with pytest.raises(ValueError, match="Entity not found"):
        markdown_backend.add_link(entity1.id, ["nonexistent-id"], "blocked by")


def test_add_link_idempotent(markdown_backend: MarkdownBackend) -> None:
    """Test adding the same link twice is idempotent."""
    entity1 = markdown_backend.create(title="Entity 1")
    entity2 = markdown_backend.create(title="Entity 2")

    markdown_backend.add_link(entity1.id, [entity2.id], "blocked by")
    markdown_backend.add_link(entity1.id, [entity2.id], "blocked by")

    links = markdown_backend.list_links(entity1.id)

    # Should only have one link
    assert len(links) == 1


def test_remove_link(markdown_backend: MarkdownBackend) -> None:
    """Test removing a link."""
    entity1 = markdown_backend.create(title="Entity 1")
    entity2 = markdown_backend.create(title="Entity 2")

    markdown_backend.add_link(entity1.id, [entity2.id], "blocked by")
    markdown_backend.remove_link(entity1.id, [entity2.id], "blocked by")

    links = markdown_backend.list_links(entity1.id)

    assert len(links) == 0


def test_remove_link_recursive(markdown_backend: MarkdownBackend) -> None:
    """Test removing links recursively."""
    entity1 = markdown_backend.create(title="Entity 1")
    entity2 = markdown_backend.create(title="Entity 2")
    entity3 = markdown_backend.create(title="Entity 3")

    # Create chain: 1 -> 2 -> 3
    markdown_backend.add_link(entity1.id, [entity2.id], "children")
    markdown_backend.add_link(entity2.id, [entity3.id], "children")

    # Remove from entity1 with recursive=True
    markdown_backend.remove_link(entity1.id, [entity2.id], "children", recursive=True)

    # Both links should be removed
    links1 = markdown_backend.list_links(entity1.id)
    links2 = markdown_backend.list_links(entity2.id)

    assert len(links1) == 0
    assert len(links2) == 0


def test_list_links_filtered_by_type(markdown_backend: MarkdownBackend) -> None:
    """Test listing links filtered by type."""
    entity1 = markdown_backend.create(title="Entity 1")
    entity2 = markdown_backend.create(title="Entity 2")
    entity3 = markdown_backend.create(title="Entity 3")

    markdown_backend.add_link(entity1.id, [entity2.id], "blocked by")
    markdown_backend.add_link(entity1.id, [entity3.id], "parent")

    blocked_by_links = markdown_backend.list_links(entity1.id, "blocked by")
    parent_links = markdown_backend.list_links(entity1.id, "parent")

    assert len(blocked_by_links) == 1
    assert blocked_by_links[0].target_id == entity2.id
    assert len(parent_links) == 1
    assert parent_links[0].target_id == entity3.id


def test_get_link_tree(markdown_backend: MarkdownBackend) -> None:
    """Test getting the link tree for an entity."""
    entity1 = markdown_backend.create(title="Parent")
    entity2 = markdown_backend.create(title="Child")
    entity3 = markdown_backend.create(title="Blocking")

    markdown_backend.add_link(entity1.id, [entity2.id], "children")
    markdown_backend.add_link(entity3.id, [entity1.id], "blocking")

    tree = markdown_backend.get_link_tree(entity1.id)

    assert tree["entity"]["id"] == entity1.id
    assert tree["entity"]["title"] == "Parent"
    assert len(tree["links"]["children"]) == 1
    assert tree["links"]["children"][0]["id"] == entity2.id
    assert len(tree["links"]["blocked by"]) == 1
    assert tree["links"]["blocked by"][0]["id"] == entity3.id


def test_find_cycles_no_cycles(markdown_backend: MarkdownBackend) -> None:
    """Test finding cycles when there are none."""
    entity1 = markdown_backend.create(title="Entity 1")
    entity2 = markdown_backend.create(title="Entity 2")
    entity3 = markdown_backend.create(title="Entity 3")

    markdown_backend.add_link(entity1.id, [entity2.id], "blocked by")
    markdown_backend.add_link(entity2.id, [entity3.id], "blocked by")

    cycles = markdown_backend.find_cycles()

    assert len(cycles) == 0


def test_find_cycles_with_cycle(markdown_backend: MarkdownBackend) -> None:
    """Test finding cycles when they exist."""
    entity1 = markdown_backend.create(title="Entity 1")
    entity2 = markdown_backend.create(title="Entity 2")
    entity3 = markdown_backend.create(title="Entity 3")

    # Create cycle: 1 -> 2 -> 3 -> 1
    markdown_backend.add_link(entity1.id, [entity2.id], "blocked by")
    markdown_backend.add_link(entity2.id, [entity3.id], "blocked by")
    markdown_backend.add_link(entity3.id, [entity1.id], "blocked by")

    cycles = markdown_backend.find_cycles()

    assert len(cycles) == 1
    # Cycle should include all three entities
    cycle_set = set(cycles[0])
    assert {entity1.id, entity2.id, entity3.id}.issubset(cycle_set)


def test_find_cycles_self_reference(markdown_backend: MarkdownBackend) -> None:
    """Test finding cycles with self-referential links."""
    entity1 = markdown_backend.create(title="Entity 1")

    markdown_backend.add_link(entity1.id, [entity1.id], "blocked by")

    cycles = markdown_backend.find_cycles()

    assert len(cycles) == 1
    assert cycles[0][0] == entity1.id


def test_delete_entity_removes_links(markdown_backend: MarkdownBackend) -> None:
    """Test that deleting an entity removes its links."""
    entity1 = markdown_backend.create(title="Entity 1")
    entity2 = markdown_backend.create(title="Entity 2")
    entity3 = markdown_backend.create(title="Entity 3")

    markdown_backend.add_link(entity1.id, [entity2.id, entity3.id], "children")
    markdown_backend.add_link(entity2.id, [entity3.id], "blocking")

    # Delete entity2
    markdown_backend.delete([entity2.id])

    # Links involving entity2 should be removed
    links1 = markdown_backend.list_links(entity1.id)

    # entity1 should only have link to entity3 now
    assert len(links1) == 1
    assert links1[0].target_id == entity3.id


def test_yaml_frontmatter_parsing(markdown_backend: MarkdownBackend) -> None:
    """Test that YAML frontmatter is correctly parsed and written."""
    entity = markdown_backend.create(
        title="Test",
        description="Description with **markdown**",
        labels={"key": "value", "priority": "high"},
        assignee="user",
    )

    file_path = markdown_backend._get_entity_path(entity.id)
    content = file_path.read_text()

    # Verify YAML frontmatter format
    assert content.startswith("---")
    assert "id: " + entity.id in content
    assert "title: Test" in content
    assert "assignee: user" in content

    # Verify markdown content
    assert "Description with **markdown**" in content


def test_generate_unique_ids(markdown_backend: MarkdownBackend) -> None:
    """Test that generated entity IDs are unique."""
    ids = set()
    for _ in range(100):
        entity = markdown_backend.create(title=f"Entity {len(ids)}")
        ids.add(entity.id)

    # All IDs should be unique
    assert len(ids) == 100

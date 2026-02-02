"""Tests for SQLite backend."""

from pathlib import Path

import pytest

from entity_manager.backends.sqlite import SQLiteBackend


@pytest.fixture
def sqlite_backend(tmp_path: Path) -> SQLiteBackend:
    """Create a SQLite backend with a temporary database."""
    db_path = str(tmp_path / "test.db")
    return SQLiteBackend(db_path=db_path)


def test_sqlite_backend_init(sqlite_backend: SQLiteBackend) -> None:
    """Test SQLite backend initialization."""
    assert sqlite_backend.db_path.endswith("test.db")
    assert sqlite_backend._conn is not None


def test_create_entity(sqlite_backend: SQLiteBackend) -> None:
    """Test creating an entity."""
    entity = sqlite_backend.create("Test Task", description="Test description", assignee="alice")
    assert entity.id.startswith("sql-")
    assert entity.title == "Test Task"
    assert entity.description == "Test description"
    assert entity.assignee == "alice"
    assert entity.status == "open"


def test_create_entity_with_labels(sqlite_backend: SQLiteBackend) -> None:
    """Test creating an entity with labels."""
    labels = {"priority": "high", "type": "bug"}
    entity = sqlite_backend.create("Test Task", labels=labels)
    assert entity.labels == labels


def test_read_entity(sqlite_backend: SQLiteBackend) -> None:
    """Test reading an entity."""
    created = sqlite_backend.create("Test Task")
    read_entity = sqlite_backend.read(created.id)
    assert read_entity.id == created.id
    assert read_entity.title == created.title


def test_read_nonexistent_entity(sqlite_backend: SQLiteBackend) -> None:
    """Test reading a nonexistent entity raises error."""
    with pytest.raises(ValueError, match="not found"):
        sqlite_backend.read("sql-nonexistent")


def test_update_entity_title(sqlite_backend: SQLiteBackend) -> None:
    """Test updating entity title."""
    entity = sqlite_backend.create("Old Title")
    updated = sqlite_backend.update(entity.id, title="New Title")
    assert updated.title == "New Title"


def test_update_entity_status(sqlite_backend: SQLiteBackend) -> None:
    """Test updating entity status."""
    entity = sqlite_backend.create("Test Task")
    updated = sqlite_backend.update(entity.id, status="closed")
    assert updated.status == "closed"


def test_update_entity_labels(sqlite_backend: SQLiteBackend) -> None:
    """Test updating entity labels."""
    entity = sqlite_backend.create("Test Task", labels={"priority": "high"})
    updated = sqlite_backend.update(entity.id, labels={"priority": "low", "type": "feature"})
    assert updated.labels == {"priority": "low", "type": "feature"}


def test_update_nonexistent_entity(sqlite_backend: SQLiteBackend) -> None:
    """Test updating a nonexistent entity raises error."""
    with pytest.raises(ValueError, match="not found"):
        sqlite_backend.update("sql-nonexistent", title="New Title")


def test_delete_single_entity(sqlite_backend: SQLiteBackend) -> None:
    """Test deleting a single entity."""
    entity = sqlite_backend.create("Test Task")
    sqlite_backend.delete([entity.id])

    with pytest.raises(ValueError, match="not found"):
        sqlite_backend.read(entity.id)


def test_delete_multiple_entities(sqlite_backend: SQLiteBackend) -> None:
    """Test deleting multiple entities."""
    e1 = sqlite_backend.create("Task 1")
    e2 = sqlite_backend.create("Task 2")
    e3 = sqlite_backend.create("Task 3")

    sqlite_backend.delete([e1.id, e2.id])

    with pytest.raises(ValueError, match="not found"):
        sqlite_backend.read(e1.id)
    with pytest.raises(ValueError, match="not found"):
        sqlite_backend.read(e2.id)

    # Third entity should still exist
    assert sqlite_backend.read(e3.id).id == e3.id


def test_delete_empty_list(sqlite_backend: SQLiteBackend) -> None:
    """Test deleting with empty list succeeds silently."""
    sqlite_backend.create("Test Task")
    sqlite_backend.delete([])  # Should not raise


def test_list_all_entities(sqlite_backend: SQLiteBackend) -> None:
    """Test listing all entities."""
    sqlite_backend.create("Task 1")
    sqlite_backend.create("Task 2")
    sqlite_backend.create("Task 3")

    entities = sqlite_backend.list_entities()
    assert len(entities) == 3


def test_list_entities_with_status_filter(sqlite_backend: SQLiteBackend) -> None:
    """Test listing entities with status filter."""
    sqlite_backend.create("Task 1")
    e2 = sqlite_backend.create("Task 2")
    sqlite_backend.create("Task 3")
    sqlite_backend.update(e2.id, status="closed")

    open_entities = sqlite_backend.list_entities(filters={"status": "open"})
    assert len(open_entities) == 2

    closed_entities = sqlite_backend.list_entities(filters={"status": "closed"})
    assert len(closed_entities) == 1


def test_list_entities_with_assignee_filter(sqlite_backend: SQLiteBackend) -> None:
    """Test listing entities with assignee filter."""
    sqlite_backend.create("Task 1", assignee="alice")
    sqlite_backend.create("Task 2", assignee="bob")
    sqlite_backend.create("Task 3", assignee="alice")

    alice_entities = sqlite_backend.list_entities(filters={"assignee": "alice"})
    assert len(alice_entities) == 2


def test_list_entities_with_title_filter(sqlite_backend: SQLiteBackend) -> None:
    """Test listing entities with title filter."""
    sqlite_backend.create("Bug: Login fails")
    sqlite_backend.create("Feature: Add export")
    sqlite_backend.create("Task: Fix tests")

    bug_entities = sqlite_backend.list_entities(filters={"title": "Bug"})
    assert len(bug_entities) == 1
    assert bug_entities[0].title == "Bug: Login fails"


def test_list_entities_with_limit(sqlite_backend: SQLiteBackend) -> None:
    """Test listing entities with limit."""
    sqlite_backend.create("Task 1")
    sqlite_backend.create("Task 2")
    sqlite_backend.create("Task 3")

    entities = sqlite_backend.list_entities(limit=2)
    assert len(entities) == 2


def test_list_entities_with_sort(sqlite_backend: SQLiteBackend) -> None:
    """Test listing entities with sorting."""
    sqlite_backend.create("Task C")
    sqlite_backend.create("Task A")
    sqlite_backend.create("Task B")

    entities = sqlite_backend.list_entities(sort_by="title")
    assert entities[0].title == "Task A"
    assert entities[1].title == "Task B"
    assert entities[2].title == "Task C"


def test_add_link(sqlite_backend: SQLiteBackend) -> None:
    """Test adding a link between entities."""
    e1 = sqlite_backend.create("Task 1")
    e2 = sqlite_backend.create("Task 2")

    sqlite_backend.add_link(e1.id, [e2.id], "blocks")

    links = sqlite_backend.list_links(e1.id)
    assert len(links) == 1
    assert links[0].source_id == e1.id
    assert links[0].target_id == e2.id
    assert links[0].link_type == "blocks"


def test_add_multiple_links(sqlite_backend: SQLiteBackend) -> None:
    """Test adding multiple links from one source."""
    e1 = sqlite_backend.create("Task 1")
    e2 = sqlite_backend.create("Task 2")
    e3 = sqlite_backend.create("Task 3")

    sqlite_backend.add_link(e1.id, [e2.id, e3.id], "child")

    links = sqlite_backend.list_links(e1.id)
    assert len(links) == 2


def test_add_link_nonexistent_entity(sqlite_backend: SQLiteBackend) -> None:
    """Test adding link with nonexistent entity raises error."""
    e1 = sqlite_backend.create("Task 1")

    with pytest.raises(ValueError, match="not found"):
        sqlite_backend.add_link(e1.id, ["sql-nonexistent"], "blocks")


def test_remove_link(sqlite_backend: SQLiteBackend) -> None:
    """Test removing a link."""
    e1 = sqlite_backend.create("Task 1")
    e2 = sqlite_backend.create("Task 2")

    sqlite_backend.add_link(e1.id, [e2.id], "blocks")
    sqlite_backend.remove_link(e1.id, [e2.id], "blocks")

    links = sqlite_backend.list_links(e1.id)
    assert len(links) == 0


def test_list_links_with_type_filter(sqlite_backend: SQLiteBackend) -> None:
    """Test listing links filtered by type."""
    e1 = sqlite_backend.create("Task 1")
    e2 = sqlite_backend.create("Task 2")
    e3 = sqlite_backend.create("Task 3")

    sqlite_backend.add_link(e1.id, [e2.id], "blocks")
    sqlite_backend.add_link(e1.id, [e3.id], "child")

    blocking_links = sqlite_backend.list_links(e1.id, link_type="blocks")
    assert len(blocking_links) == 1
    assert blocking_links[0].target_id == e2.id


def test_get_link_tree(sqlite_backend: SQLiteBackend) -> None:
    """Test getting link tree for an entity."""
    e1 = sqlite_backend.create("Parent Task")
    e2 = sqlite_backend.create("Child Task")
    e3 = sqlite_backend.create("Blocking Task")

    sqlite_backend.add_link(e1.id, [e2.id], "child")
    sqlite_backend.add_link(e3.id, [e1.id], "blocking")

    tree = sqlite_backend.get_link_tree(e1.id)

    assert tree["entity"]["id"] == e1.id
    assert tree["entity"]["title"] == "Parent Task"
    assert len(tree["links"]["children"]) == 1
    assert tree["links"]["children"][0]["id"] == e2.id
    assert len(tree["links"]["blocked_by"]) == 1
    assert tree["links"]["blocked_by"][0]["id"] == e3.id


def test_find_cycles_no_cycles(sqlite_backend: SQLiteBackend) -> None:
    """Test finding cycles when none exist."""
    e1 = sqlite_backend.create("Task 1")
    e2 = sqlite_backend.create("Task 2")
    e3 = sqlite_backend.create("Task 3")

    sqlite_backend.add_link(e1.id, [e2.id], "blocks")
    sqlite_backend.add_link(e2.id, [e3.id], "blocks")

    cycles = sqlite_backend.find_cycles()
    assert len(cycles) == 0


def test_find_cycles_with_cycle(sqlite_backend: SQLiteBackend) -> None:
    """Test finding cycles when they exist."""
    e1 = sqlite_backend.create("Task 1")
    e2 = sqlite_backend.create("Task 2")
    e3 = sqlite_backend.create("Task 3")

    sqlite_backend.add_link(e1.id, [e2.id], "blocks")
    sqlite_backend.add_link(e2.id, [e3.id], "blocks")
    sqlite_backend.add_link(e3.id, [e1.id], "blocks")

    cycles = sqlite_backend.find_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {e1.id, e2.id, e3.id}


def test_find_cycles_self_reference(sqlite_backend: SQLiteBackend) -> None:
    """Test finding self-referential cycles."""
    e1 = sqlite_backend.create("Task 1")

    sqlite_backend.add_link(e1.id, [e1.id], "blocks")

    cycles = sqlite_backend.find_cycles()
    assert len(cycles) == 1
    assert cycles[0][0] == e1.id


def test_close_backend(sqlite_backend: SQLiteBackend) -> None:
    """Test closing the backend connection."""
    sqlite_backend.close()
    # After closing, the connection should be None or closed
    # We can't execute queries on a closed connection, so just verify it doesn't crash
    assert sqlite_backend._conn is None


def test_entity_persistence(sqlite_backend: SQLiteBackend) -> None:
    """Test that entities persist across connections."""
    e1 = sqlite_backend.create("Persistent Task")

    # Create new backend with same database
    import sqlite3

    conn = sqlite3.connect(sqlite_backend.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM entities WHERE id = ?", (e1.id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "Persistent Task"

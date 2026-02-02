"""Tests for Redis backend."""

from unittest.mock import MagicMock, patch

import pytest
from redis import Redis

from entity_manager.backends.redis import RedisBackend
from entity_manager.models import Entity


@pytest.fixture
def mock_pipeline():
    """Create a mock Redis pipeline."""
    pipeline = MagicMock()
    pipeline.delete.return_value = None
    pipeline.srem.return_value = None
    pipeline.set.return_value = None
    pipeline.execute.return_value = None
    return pipeline


@pytest.fixture
def mock_redis(mock_pipeline):
    """Create a mock Redis client."""
    with patch("entity_manager.backends.redis.Redis") as mock:
        client = MagicMock(spec=Redis)
        mock.return_value = client
        client.ping.return_value = True
        client.hgetall.return_value = {}
        client.hset.return_value = True
        client.exists.return_value = True
        client.smembers.return_value = set()
        client.scan_iter.return_value = []
        client.delete.return_value = 1
        client.srem.return_value = 1
        client.sadd.return_value = 1
        client.pipeline.return_value = mock_pipeline
        client.set.return_value = True
        yield client


@pytest.fixture
def redis_backend(mock_redis):
    """Create a Redis backend with mocked Redis client."""
    return RedisBackend()


def test_init(mock_redis):
    """Test Redis backend initialization."""
    backend = RedisBackend(host="localhost", port=6379, db=0)
    assert backend._redis is not None


def test_entity_key(redis_backend):
    """Test entity key generation."""
    key = redis_backend._entity_key("test-123")
    assert key == "entity:test-123"


def test_link_key(redis_backend):
    """Test link key generation."""
    key = redis_backend._link_key("src-1", "tgt-2", "blocks")
    assert key == "link:src-1:tgt-2:blocks"


def test_create_entity(redis_backend, mock_redis):
    """Test creating an entity."""

    # After creating, read() is called which uses hgetall
    # Set up hgetall to return a valid entity
    def hgetall_side_effect(key):
        if key.startswith("entity:r-"):
            return {
                "id": key.replace("entity:", ""),
                "title": "Test Task",
                "description": "Test description",
                "labels": "{}",
                "assignee": "user1",
                "status": "open",
                "metadata": '{"backend": "redis"}',
            }
        return {}

    mock_redis.hgetall.side_effect = hgetall_side_effect

    entity = redis_backend.create("Test Task", description="Test description", assignee="user1")

    assert isinstance(entity, Entity)
    assert entity.id.startswith("r-")
    assert entity.title == "Test Task"
    assert entity.description == "Test description"
    assert entity.assignee == "user1"
    mock_redis.hset.assert_called_once()
    mock_redis.sadd.assert_called_once()

    # Reset side effect
    mock_redis.hgetall.side_effect = None
    mock_redis.hgetall.return_value = {}


def test_read_entity(redis_backend, mock_redis):
    """Test reading an entity."""
    mock_redis.hgetall.return_value = {
        "id": "r-abc123",
        "title": "Existing Task",
        "description": "",
        "labels": "",
        "assignee": "",
        "status": "open",
        "metadata": "{}",
    }

    entity = redis_backend.read("r-abc123")

    assert entity.id == "r-abc123"
    assert entity.title == "Existing Task"
    assert entity.status == "open"


def test_read_entity_not_found(redis_backend, mock_redis):
    """Test reading a non-existent entity."""
    mock_redis.hgetall.return_value = {}

    with pytest.raises(ValueError, match="Entity r-missing not found"):
        redis_backend.read("r-missing")


def test_read_entity_invalid_labels(redis_backend, mock_redis):
    """Test reading an entity with invalid labels JSON."""
    mock_redis.hgetall.return_value = {
        "id": "r-badlabel",
        "title": "Task",
        "description": "",
        "labels": "invalid-json",
        "assignee": "",
        "status": "open",
        "metadata": "{}",
    }

    entity = redis_backend.read("r-badlabel")
    assert entity.labels == {}


def test_update_entity(redis_backend, mock_redis):
    """Test updating an entity."""
    mock_redis.hgetall.return_value = {
        "id": "r-update1",
        "title": "Updated Title",
        "description": "",
        "labels": "",
        "assignee": "",
        "status": "in_progress",
        "metadata": "{}",
    }

    entity = redis_backend.update("r-update1", title="Updated Title", status="in_progress")

    assert entity.title == "Updated Title"
    assert entity.status == "in_progress"
    mock_redis.hset.assert_called()


def test_update_entity_not_found(redis_backend, mock_redis):
    """Test updating a non-existent entity."""
    mock_redis.exists.return_value = False

    with pytest.raises(ValueError, match="Entity r-missing not found"):
        redis_backend.update("r-missing", title="New Title")


def test_delete_entities(redis_backend, mock_redis, mock_pipeline):
    """Test deleting entities."""
    redis_backend.delete(["r-del1", "r-del2"])

    mock_pipeline.delete.assert_called()
    mock_pipeline.srem.assert_called_with("em:entities", "r-del1", "r-del2")
    mock_pipeline.execute.assert_called()


def test_delete_empty_list(redis_backend, mock_redis):
    """Test deleting with an empty list."""
    redis_backend.delete([])
    mock_redis.delete.assert_not_called()


def test_list_entities_empty(redis_backend, mock_redis):
    """Test listing entities when none exist."""
    mock_redis.smembers.return_value = set()

    entities = redis_backend.list_entities()
    assert entities == []


def test_list_entities_with_filters(redis_backend, mock_redis):
    """Test listing entities with filters."""
    mock_redis.smembers.return_value = {"r-1", "r-2"}
    mock_redis.hgetall.side_effect = [
        {
            "id": "r-2",
            "title": "Task 2",
            "description": "",
            "labels": "",
            "assignee": "user2",
            "status": "closed",
            "metadata": "{}",
        },
        {
            "id": "r-1",
            "title": "Task 1",
            "description": "",
            "labels": '{"priority": "high"}',
            "assignee": "user1",
            "status": "open",
            "metadata": "{}",
        },
    ]

    entities = redis_backend.list_entities(filters={"status": "open"})
    assert len(entities) == 1
    assert entities[0].status == "open"


def test_list_entities_with_sort(redis_backend, mock_redis):
    """Test listing entities with sorting."""
    mock_redis.smembers.return_value = {"r-1", "r-2"}
    mock_redis.hgetall.side_effect = [
        {
            "id": "r-1",
            "title": "Zebra Task",
            "description": "",
            "labels": "",
            "assignee": "",
            "status": "open",
            "metadata": "{}",
        },
        {
            "id": "r-2",
            "title": "Apple Task",
            "description": "",
            "labels": "",
            "assignee": "",
            "status": "open",
            "metadata": "{}",
        },
    ]

    entities = redis_backend.list_entities(sort_by="title")
    assert len(entities) == 2
    assert entities[0].title == "Apple Task"
    assert entities[1].title == "Zebra Task"


def test_list_entities_with_limit(redis_backend, mock_redis):
    """Test listing entities with a limit."""
    mock_redis.smembers.return_value = {"r-1", "r-2", "r-3"}
    mock_redis.hgetall.side_effect = [
        {
            "id": f"r-{i}",
            "title": f"Task {i}",
            "description": "",
            "labels": "",
            "assignee": "",
            "status": "open",
            "metadata": "{}",
        }
        for i in range(1, 4)
    ]

    entities = redis_backend.list_entities(limit=2)
    assert len(entities) == 2


def test_add_link(redis_backend, mock_redis, mock_pipeline):
    """Test adding a link."""
    # Setup for source entity and target entity
    mock_redis.hgetall.return_value = {
        "id": "r-source",
        "title": "Source",
        "description": "",
        "labels": "",
        "assignee": "",
        "status": "open",
        "metadata": "{}",
    }

    redis_backend.add_link("r-source", ["r-target"], "blocks")
    mock_pipeline.set.assert_called_once()
    mock_pipeline.execute.assert_called_once()


def test_add_link_entity_not_found(redis_backend, mock_redis):
    """Test adding a link with non-existent entity."""
    mock_redis.hgetall.return_value = {}

    with pytest.raises(ValueError, match="Entity r-source not found"):
        redis_backend.add_link("r-source", ["r-missing"], "blocks")


def test_remove_link(redis_backend, mock_redis, mock_pipeline):
    """Test removing a link."""
    redis_backend.remove_link("r-source", ["r-target"], "blocks")
    mock_pipeline.delete.assert_called()
    mock_pipeline.execute.assert_called_once()


def test_remove_link_recursive(redis_backend, mock_redis, mock_pipeline):
    """Test removing links recursively."""
    mock_redis.scan_iter.return_value = ["link:r-target:r-other:blocks"]

    redis_backend.remove_link("r-source", ["r-target"], "blocks", recursive=True)
    # Should call delete at least once (for the direct link)
    assert mock_pipeline.delete.call_count >= 1
    mock_pipeline.execute.assert_called_once()


def test_list_links(redis_backend, mock_redis):
    """Test listing links for an entity."""
    mock_redis.scan_iter.return_value = ["link:r-1:r-2:blocks", "link:r-1:r-3:parent"]

    links = redis_backend.list_links("r-1")
    assert len(links) == 2
    assert links[0].source_id == "r-1"
    assert links[0].target_id == "r-2"
    assert links[0].link_type == "blocks"


def test_list_links_by_type(redis_backend, mock_redis):
    """Test listing links filtered by type."""
    mock_redis.scan_iter.return_value = ["link:r-1:r-2:blocks"]

    links = redis_backend.list_links("r-1", link_type="blocks")
    assert len(links) == 1
    assert links[0].link_type == "blocks"


def test_get_link_tree(redis_backend, mock_redis):
    """Test getting link tree for an entity."""
    mock_redis.hgetall.return_value = {
        "id": "r-1",
        "title": "Main Task",
        "description": "",
        "labels": "",
        "assignee": "",
        "status": "open",
        "metadata": "{}",
    }
    mock_redis.scan_iter.return_value = []

    tree = redis_backend.get_link_tree("r-1")

    assert "entity" in tree
    assert "links" in tree
    assert tree["entity"]["id"] == "r-1"
    assert tree["entity"]["title"] == "Main Task"
    assert "children" in tree["links"]
    assert "blocking" in tree["links"]
    assert "blocked_by" in tree["links"]
    assert "parent" in tree["links"]


def test_find_cycles_empty(redis_backend, mock_redis):
    """Test finding cycles when there are none."""
    mock_redis.scan_iter.return_value = []

    cycles = redis_backend.find_cycles()
    assert cycles == []


def test_find_cycles_with_cycle(redis_backend, mock_redis):
    """Test finding cycles in the link graph."""
    mock_redis.scan_iter.return_value = [
        "link:r-1:r-2:blocks",
        "link:r-2:r-3:blocks",
        "link:r-3:r-1:blocks",
    ]

    cycles = redis_backend.find_cycles()
    # Should find at least one cycle
    assert len(cycles) > 0


def test_close(redis_backend, mock_redis):
    """Test closing the Redis connection."""
    redis_backend.close()
    mock_redis.close.assert_called_once()

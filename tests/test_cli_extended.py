"""Extended tests for CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from entity_manager.cli import configure_logging, create, get_backend, list_entities, read
from entity_manager.config import Config
from entity_manager.models import Entity


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_backend():
    """Create a mock backend."""
    backend = MagicMock()
    backend.create.return_value = Entity(
        id="1",
        type="default",
        properties={"title": "Test Task", "description": "Test description", "status": "open"},
    )
    backend.read.return_value = Entity(
        id="1",
        type="default",
        properties={"title": "Test Task", "description": "Test description", "status": "open", "assignee": "user1"},
        metadata={"url": "http://example.com"},
    )
    backend.update.return_value = Entity(
        id="1",
        type="default",
        properties={"title": "Updated Task", "description": "Updated description", "status": "closed"},
    )
    backend.list_entities.return_value = [
        Entity(
            id="1",
            type="default",
            properties={"title": "Task 1", "description": "", "status": "open"},
        ),
        Entity(
            id="2",
            type="default",
            properties={"title": "Task 2", "description": "", "status": "closed"},
        ),
    ]
    return backend


def test_configure_logging():
    """Test configuring logging."""
    # Should not raise an error
    configure_logging("debug")
    configure_logging("info")
    configure_logging("warning")
    configure_logging("error")
    configure_logging("critical")


def test_get_backend_github(temp_config_dir):
    """Test getting GitHub backend."""
    config = Config(config_dir=temp_config_dir)
    config.set("backend", "github")
    config.set("github.owner", "test_owner")
    config.set("github.repository", "test_repo")
    config.set("github.token", "test_token")

    with patch("entity_manager.cli.get_config", return_value=config):
        with patch("entity_manager.cli.GitHubBackend") as mock_github:
            backend = get_backend()
            assert backend is not None
            mock_github.assert_called_once_with(owner="test_owner", repo="test_repo", token="test_token")


def test_get_backend_github_missing_config(temp_config_dir):
    """Test getting GitHub backend with missing config."""
    config = Config(config_dir=temp_config_dir)
    config.set("backend", "github")

    with patch("entity_manager.cli.get_config", return_value=config):
        with pytest.raises(ValueError, match="GitHub owner and repo not configured"):
            get_backend()


def test_get_backend_backlog(temp_config_dir):
    """Test getting Backlog backend."""
    config = Config(config_dir=temp_config_dir)
    config.set("backend", "backlog")
    config.set("backlog.path", "/path/to/backlog.md")

    with patch("entity_manager.cli.get_config", return_value=config):
        with patch("entity_manager.cli.BacklogBackend") as mock_backlog:
            backend = get_backend()
            assert backend is not None
            mock_backlog.assert_called_once_with(backlog_path="/path/to/backlog.md")


def test_get_backend_beads(temp_config_dir):
    """Test getting Beads backend."""
    config = Config(config_dir=temp_config_dir)
    config.set("backend", "beads")
    config.set("beads.project_path", "/path/to/project")

    with patch("entity_manager.cli.get_config", return_value=config):
        with patch("entity_manager.cli.BeadsBackend") as mock_beads:
            backend = get_backend()
            assert backend is not None
            mock_beads.assert_called_once_with(project_path="/path/to/project")


def test_get_backend_markdown(temp_config_dir):
    """Test getting Markdown backend."""
    config = Config(config_dir=temp_config_dir)
    config.set("backend", "markdown")
    config.set("markdown.directory_path", "/path/to/markdown")

    with patch("entity_manager.cli.get_config", return_value=config):
        with patch("entity_manager.cli.MarkdownBackend") as mock_markdown:
            backend = get_backend()
            assert backend is not None
            mock_markdown.assert_called_once_with(directory_path="/path/to/markdown")


def test_get_backend_markdown_default_path(temp_config_dir):
    """Test getting Markdown backend with default path."""
    config = Config(config_dir=temp_config_dir)
    config.set("backend", "markdown")

    with patch("entity_manager.cli.get_config", return_value=config):
        with patch("entity_manager.cli.MarkdownBackend") as mock_markdown:
            backend = get_backend()
            assert backend is not None
            mock_markdown.assert_called_once_with(directory_path=".entity-manager/content")


def test_get_backend_sqlite(temp_config_dir):
    """Test getting SQLite backend."""
    config = Config(config_dir=temp_config_dir)
    config.set("backend", "sqlite")
    config.set("sqlite.db_path", "/path/to/db.sqlite")

    with patch("entity_manager.cli.get_config", return_value=config):
        with patch("entity_manager.cli.SQLiteBackend") as mock_sqlite:
            backend = get_backend()
            assert backend is not None
            mock_sqlite.assert_called_once_with(db_path="/path/to/db.sqlite")


def test_get_backend_unknown(temp_config_dir):
    """Test getting unknown backend raises error."""
    config = Config(config_dir=temp_config_dir)
    config.set("backend", "unknown_backend")

    with patch("entity_manager.cli.get_config", return_value=config):
        with pytest.raises(ValueError, match="Unknown backend"):
            get_backend()


def test_create_entity_minimal(mock_backend, capsys):
    """Test creating entity with minimal fields."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        with patch("entity_manager.cli.TypeManager") as mock_tm:
            from entity_manager.models import EntityType, PropertyDefinition, PropertyType

            mock_tm.return_value.get_type.return_value = EntityType(
                name="default",
                properties=[
                    PropertyDefinition(name="title", type=PropertyType.STRING, required=True),
                    PropertyDefinition(name="description", type=PropertyType.STRING, default=""),
                    PropertyDefinition(name="status", type=PropertyType.STRING, default="open"),
                ],
            )
            create("title=Test Task")

    mock_backend.create.assert_called_once()
    call_kwargs = mock_backend.create.call_args[1]
    assert call_kwargs["properties"]["title"] == "Test Task"
    captured = capsys.readouterr()
    assert "Created entity 1: Test Task" in captured.out


def test_read_entity(mock_backend, capsys):
    """Test reading an entity."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        read("1")

    mock_backend.read.assert_called_once_with("1")
    captured = capsys.readouterr()
    assert "Entity: 1" in captured.out
    assert "Type: default" in captured.out
    assert "title: Test Task" in captured.out
    assert "description: Test description" in captured.out
    assert "status: open" in captured.out
    assert "assignee: user1" in captured.out
    assert "URL: http://example.com" in captured.out


def test_read_entity_no_labels(mock_backend, capsys):
    """Test reading entity without labels."""
    mock_backend.read.return_value = Entity(
        id="1",
        type="default",
        properties={"title": "Test Task", "description": "Test description", "status": "open"},
    )

    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        read("1")

    captured = capsys.readouterr()
    assert "Entity: 1" in captured.out
    assert "Type: default" in captured.out
    assert "title: Test Task" in captured.out


def test_list_entities(mock_backend, capsys):
    """Test listing entities."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        list_entities()

    mock_backend.list_entities.assert_called_once_with(filters=None, sort_by=None, limit=None)
    captured = capsys.readouterr()
    assert "Found 2 entity(ies):" in captured.out
    assert "1: Task 1" in captured.out
    assert "2: Task 2" in captured.out


def test_list_entities_with_filter(mock_backend):
    """Test listing entities with filter."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        list_entities(filter="status=open,assignee=user1")

    call_args = mock_backend.list_entities.call_args
    assert call_args[1]["filters"] == {"status": "open", "assignee": "user1"}


def test_list_entities_with_sort(mock_backend):
    """Test listing entities with sort."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        list_entities(sort="title")

    call_args = mock_backend.list_entities.call_args
    assert call_args[1]["sort_by"] == "title"


def test_list_entities_with_limit(mock_backend):
    """Test listing entities with limit."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        list_entities(limit=10)

    call_args = mock_backend.list_entities.call_args
    assert call_args[1]["limit"] == 10


def test_list_entities_no_labels(mock_backend, capsys):
    """Test listing entities without labels."""
    mock_backend.list_entities.return_value = [
        Entity(id="1", type="default", properties={"title": "Task 1", "status": "open"})
    ]

    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        list_entities()

    captured = capsys.readouterr()
    assert "1: Task 1" in captured.out

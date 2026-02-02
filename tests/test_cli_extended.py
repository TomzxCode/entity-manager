"""Extended tests for CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from entity_manager.cli import configure_logging, create, get_backend, list_entities, read, update
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
        title="Test Task",
        description="Test description",
        status="open",
        labels={},
        assignee=None,
    )
    backend.read.return_value = Entity(
        id="1",
        title="Test Task",
        description="Test description",
        status="open",
        labels={"type": "bug"},
        assignee="user1",
        metadata={"url": "http://example.com"},
    )
    backend.update.return_value = Entity(
        id="1",
        title="Updated Task",
        description="Updated description",
        status="closed",
        labels={},
        assignee=None,
    )
    backend.list_entities.return_value = [
        Entity(
            id="1",
            title="Task 1",
            description="",
            status="open",
            labels={"priority": "high"},
            assignee=None,
        ),
        Entity(
            id="2",
            title="Task 2",
            description="",
            status="closed",
            labels={},
            assignee=None,
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
        create("Test Task")

    mock_backend.create.assert_called_once_with(
        title="Test Task",
        description="",
        labels={},
        assignee=None,
    )
    captured = capsys.readouterr()
    assert "Created entity 1: Test Task" in captured.out


def test_create_entity_with_all_fields(mock_backend, capsys):
    """Test creating entity with all fields."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        create("Test Task", description="Test desc", labels="type:bug,priority:high", assignee="user1")

    mock_backend.create.assert_called_once_with(
        title="Test Task",
        description="Test desc",
        labels={"type": "bug", "priority": "high"},
        assignee="user1",
    )


def test_create_entity_with_labels_no_value(mock_backend):
    """Test creating entity with labels without values."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        create("Test Task", labels="bug,feature")

    mock_backend.create.assert_called_once()
    call_args = mock_backend.create.call_args
    assert call_args[1]["labels"] == {"bug": "", "feature": ""}


def test_read_entity(mock_backend, capsys):
    """Test reading an entity."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        read("1")

    mock_backend.read.assert_called_once_with("1")
    captured = capsys.readouterr()
    assert "Entity: 1" in captured.out
    assert "Title: Test Task" in captured.out
    assert "Description: Test description" in captured.out
    assert "Status: open" in captured.out
    assert "Labels: type:bug" in captured.out
    assert "Assignee: user1" in captured.out
    assert "URL: http://example.com" in captured.out


def test_read_entity_no_labels(mock_backend, capsys):
    """Test reading entity without labels."""
    mock_backend.read.return_value = Entity(
        id="1",
        title="Test Task",
        description="Test description",
        status="open",
        labels=None,
        assignee=None,
    )

    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        read("1")

    captured = capsys.readouterr()
    assert "Labels:" not in captured.out
    assert "Assignee:" not in captured.out


def test_update_entity_title(mock_backend, capsys):
    """Test updating entity title."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        update("1", title="New Title")

    mock_backend.update.assert_called_once_with(
        entity_id="1",
        title="New Title",
        description=None,
        labels=None,
        status=None,
        assignee=None,
    )
    captured = capsys.readouterr()
    assert "Updated entity 1: Updated Task" in captured.out


def test_update_entity_with_labels(mock_backend):
    """Test updating entity with labels."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        update("1", labels="type:bug,priority:high")

    call_args = mock_backend.update.call_args
    assert call_args[1]["labels"] == {"type": "bug", "priority": "high"}


def test_update_entity_all_fields(mock_backend):
    """Test updating entity with all fields."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        update("1", title="New Title", description="New desc", labels="type:bug", status="closed", assignee="user2")

    mock_backend.update.assert_called_once_with(
        entity_id="1",
        title="New Title",
        description="New desc",
        labels={"type": "bug"},
        status="closed",
        assignee="user2",
    )


def test_list_entities(mock_backend, capsys):
    """Test listing entities."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        list_entities()

    mock_backend.list_entities.assert_called_once_with(filters=None, sort_by=None, limit=None)
    captured = capsys.readouterr()
    assert "Found 2 entity(ies):" in captured.out
    assert "● 1: Task 1 [priority:high]" in captured.out
    assert "○ 2: Task 2" in captured.out


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
        Entity(id="1", title="Task 1", description="", status="open", labels=None, assignee=None)
    ]

    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        list_entities()

    captured = capsys.readouterr()
    assert "● 1: Task 1\n" in captured.out

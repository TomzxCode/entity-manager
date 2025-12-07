"""Tests for beads backend."""

import json
from unittest.mock import MagicMock, patch

from entity_manager.backends.beads import BeadsBackend


@patch("entity_manager.backends.beads.subprocess.run")
def test_beads_backend_init(mock_run: MagicMock) -> None:
    """Test beads backend initialization."""
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")

    backend = BeadsBackend(project_path="/test/path")
    assert backend.project_path == "/test/path"
    mock_run.assert_called_once()


@patch("entity_manager.backends.beads.subprocess.run")
def test_create_issue(mock_run: MagicMock) -> None:
    """Test creating a beads issue."""
    # Mock init call
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock create call
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "id": "bd-a1b2",
                "title": "Test Issue",
                "description": "Test description",
                "status": "open",
                "labels": [],
                "assignee": None,
            }
        ),
        stderr="",
    )

    entity = backend.create("Test Issue", description="Test description")
    assert entity.id == "bd-a1b2"
    assert entity.title == "Test Issue"
    assert entity.description == "Test description"


@patch("entity_manager.backends.beads.subprocess.run")
def test_read_issue(mock_run: MagicMock) -> None:
    """Test reading a beads issue."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock read call
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "id": "bd-a1b2",
                "title": "Test Issue",
                "description": "Test description",
                "status": "open",
                "labels": ["bug", "priority:high"],
                "assignee": "alice",
            }
        ),
        stderr="",
    )

    entity = backend.read("bd-a1b2")
    assert entity.id == "bd-a1b2"
    assert entity.title == "Test Issue"
    assert entity.assignee == "alice"
    assert entity.labels == {"bug": "", "priority": "high"}


@patch("entity_manager.backends.beads.subprocess.run")
def test_list_issues(mock_run: MagicMock) -> None:
    """Test listing beads issues."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock list call
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            [
                {
                    "id": "bd-a1b2",
                    "title": "Issue 1",
                    "description": "",
                    "status": "open",
                    "labels": [],
                },
                {
                    "id": "bd-c3d4",
                    "title": "Issue 2",
                    "description": "",
                    "status": "open",
                    "labels": [],
                },
            ]
        ),
        stderr="",
    )

    entities = backend.list_entities()
    assert len(entities) == 2
    assert entities[0].id == "bd-a1b2"
    assert entities[1].id == "bd-c3d4"


@patch("entity_manager.backends.beads.subprocess.run")
def test_add_link(mock_run: MagicMock) -> None:
    """Test adding dependencies."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock add link call
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    backend.add_link("bd-a1b2", ["bd-c3d4"], "blocks")

    # Verify the command was called with correct arguments
    assert any("dep" in str(call) for call in mock_run.call_args_list)


@patch("entity_manager.backends.beads.subprocess.run")
def test_entity_id_conversion(mock_run: MagicMock) -> None:
    """Test entity ID conversion."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Test conversion
    assert backend._entity_id_to_bead_id("bd-a1b2") == "bd-a1b2"
    assert backend._entity_id_to_bead_id("123") == "bd-123"
    assert backend._entity_id_to_bead_id("a1b2") == "bd-a1b2"

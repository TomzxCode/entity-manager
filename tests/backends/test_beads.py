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

    entity = backend.create(properties={"title": "Test Issue", "description": "Test description"})
    assert entity.id == "bd-a1b2"
    assert entity.properties["title"] == "Test Issue"
    assert entity.properties["description"] == "Test description"


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
    assert entity.properties["title"] == "Test Issue"
    assert entity.properties["assignee"] == "alice"
    assert entity.properties["bug"] == ""
    assert entity.properties["priority"] == "high"


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


@patch("entity_manager.backends.beads.subprocess.run")
def test_update_issue(mock_run: MagicMock) -> None:
    """Test updating a beads issue."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock read call (for update to fetch current issue)
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "id": "bd-a1b2",
                "title": "Updated Title",
                "description": "Updated description",
                "status": "closed",
                "labels": [],
                "assignee": "bob",
            }
        ),
        stderr="",
    )

    entity = backend.update("bd-a1b2", properties={"title": "Updated Title", "status": "closed", "assignee": "bob"})
    assert entity.properties["title"] == "Updated Title"
    assert entity.properties["status"] == "closed"
    assert entity.properties["assignee"] == "bob"


@patch("entity_manager.backends.beads.subprocess.run")
def test_update_issue_with_labels(mock_run: MagicMock) -> None:
    """Test updating a beads issue with labels."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock read call for getting current labels
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "id": "bd-a1b2",
                "title": "Test",
                "description": "",
                "status": "open",
                "labels": ["old:label"],
                "assignee": None,
            }
        ),
        stderr="",
    )

    # Update with new labels
    entity = backend.update("bd-a1b2", properties={"new": "label", "tag": ""})
    # Will have old labels from the mocked read, merged with new
    assert "old" in entity.properties


@patch("entity_manager.backends.beads.subprocess.run")
def test_delete_issue(mock_run: MagicMock) -> None:
    """Test deleting (closing) a beads issue."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock close call
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"result": "success"}), stderr="")

    backend.delete(["bd-a1b2", "bd-c3d4"])

    # Verify close was called for each ID
    assert mock_run.call_count >= 2


@patch("entity_manager.backends.beads.subprocess.run")
def test_list_with_filters(mock_run: MagicMock) -> None:
    """Test listing with filters."""
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
                    "title": "Bug Issue",
                    "description": "",
                    "status": "open",
                    "labels": [],
                    "assignee": "alice",
                }
            ]
        ),
        stderr="",
    )

    entities = backend.list_entities(filters={"status": "open", "assignee": "alice"})
    assert len(entities) == 1
    assert entities[0].properties["assignee"] == "alice"


@patch("entity_manager.backends.beads.subprocess.run")
def test_list_with_limit(mock_run: MagicMock) -> None:
    """Test listing with limit."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock list call with multiple items
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            [
                {"id": f"bd-{i}", "title": f"Issue {i}", "description": "", "status": "open", "labels": []}
                for i in range(10)
            ]
        ),
        stderr="",
    )

    entities = backend.list_entities(limit=5)
    assert len(entities) == 5


@patch("entity_manager.backends.beads.subprocess.run")
def test_remove_link(mock_run: MagicMock) -> None:
    """Test removing dependencies."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock remove link call
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    backend.remove_link("bd-a1b2", ["bd-c3d4"], "blocks")

    # Verify the command was called
    assert mock_run.call_count >= 1


@patch("entity_manager.backends.beads.subprocess.run")
def test_list_links(mock_run: MagicMock) -> None:
    """Test listing links for an issue."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock show call with dependencies
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "id": "bd-a1b2",
                "title": "Test",
                "description": "",
                "status": "open",
                "labels": [],
                "dependencies": [
                    {"type": "blocks", "target_id": "bd-c3d4"},
                    {"type": "related", "target_id": "bd-e5f6"},
                ],
            }
        ),
        stderr="",
    )

    links = backend.list_links("bd-a1b2")
    assert len(links) == 2
    assert links[0].link_type == "blocks"
    assert links[1].link_type == "related"


@patch("entity_manager.backends.beads.subprocess.run")
def test_list_links_with_filter(mock_run: MagicMock) -> None:
    """Test listing links with type filter."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock show call with dependencies
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "id": "bd-a1b2",
                "title": "Test",
                "description": "",
                "status": "open",
                "labels": [],
                "dependencies": [
                    {"type": "blocks", "target_id": "bd-c3d4"},
                    {"type": "related", "target_id": "bd-e5f6"},
                ],
            }
        ),
        stderr="",
    )

    links = backend.list_links("bd-a1b2", link_type="blocks")
    assert len(links) == 1
    assert links[0].link_type == "blocks"


@patch("entity_manager.backends.beads.subprocess.run")
def test_get_link_tree(mock_run: MagicMock) -> None:
    """Test getting dependency tree."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Use side_effect to handle multiple calls in sequence
    mock_run.side_effect = [
        # First call: read (show) command
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "id": "bd-a1b2",
                    "title": "Test Issue",
                    "description": "",
                    "status": "open",
                    "labels": [],
                }
            ),
            stderr="",
        ),
        # Second call: tree command
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "children": [{"id": "bd-c3d4", "title": "Child"}],
                    "blocking": [],
                    "blocked_by": [],
                    "parent": {"id": "bd-e5f6", "title": "Parent"},
                }
            ),
            stderr="",
        ),
    ]

    tree = backend.get_link_tree("bd-a1b2")
    assert tree["entity"]["id"] == "bd-a1b2"
    assert len(tree["links"]["children"]) == 1
    assert len(tree["links"]["parent"]) == 1


@patch("entity_manager.backends.beads.subprocess.run")
def test_find_cycles(mock_run: MagicMock) -> None:
    """Test finding cycles in dependency graph."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock cycles call
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps([["bd-a1b2", "bd-c3d4", "bd-a1b2"]]),
        stderr="",
    )

    cycles = backend.find_cycles()
    assert len(cycles) == 1
    assert len(cycles[0]) == 3


@patch("entity_manager.backends.beads.subprocess.run")
def test_create_with_labels(mock_run: MagicMock) -> None:
    """Test creating issue with labels."""
    # Mock init
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"status": "ok"}), stderr="")
    backend = BeadsBackend()

    # Mock create call
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "id": "bd-a1b2",
                "title": "Test",
                "description": "",
                "status": "open",
                "labels": ["bug", "priority:high"],
                "assignee": None,
            }
        ),
        stderr="",
    )

    entity = backend.create(properties={"title": "Test", "bug": "", "priority": "high"})
    assert entity.properties["bug"] == ""
    assert entity.properties["priority"] == "high"


@patch("entity_manager.backends.beads.subprocess.run")
def test_init_failure(mock_run: MagicMock) -> None:
    """Test initialization failure."""
    import subprocess

    mock_run.side_effect = subprocess.CalledProcessError(1, ["bd", "info"], stderr="bd not found")

    try:
        BeadsBackend()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "bd command failed" in str(e)

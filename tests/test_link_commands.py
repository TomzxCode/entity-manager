"""Tests for link management commands."""

from unittest.mock import MagicMock, patch

import pytest

import entity_manager.link_commands as link_commands
from entity_manager.models import Link


@pytest.fixture
def mock_backend():
    """Create a mock backend."""
    backend = MagicMock()
    backend.list_links.return_value = []
    backend.get_link_tree.return_value = {
        "entity": {"id": "1", "title": "Test Entity", "state": "open"},
        "links": {"children": [], "blocking": [], "blocked_by": [], "parent": []},
    }
    backend.find_cycles.return_value = []
    return backend


def test_add_link(mock_backend, capsys):
    """Test adding links."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        link_commands.add("source-1", "target-1", "target-2", type="blocks")

    mock_backend.add_link.assert_called_once_with("source-1", ["target-1", "target-2"], "blocks")
    captured = capsys.readouterr()
    assert "Added 2 link(s) from source-1" in captured.out


def test_add_link_default_type(mock_backend):
    """Test adding links with default type."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        link_commands.add("source-1", "target-1")

    mock_backend.add_link.assert_called_once_with("source-1", ["target-1"], "relates-to")


def test_remove_link(mock_backend, capsys):
    """Test removing links."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        link_commands.remove("source-1", "target-1", "target-2", type="blocks", recursive=False)

    mock_backend.remove_link.assert_called_once_with("source-1", ["target-1", "target-2"], "blocks", False)
    captured = capsys.readouterr()
    assert "Removed 2 link(s) from source-1" in captured.out


def test_remove_link_recursive(mock_backend):
    """Test removing links recursively."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        link_commands.remove("source-1", "target-1", type="blocks", recursive=True)

    mock_backend.remove_link.assert_called_once_with("source-1", ["target-1"], "blocks", True)


def test_remove_link_default_type(mock_backend):
    """Test removing links with default type."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        link_commands.remove("source-1", "target-1")

    mock_backend.remove_link.assert_called_once_with("source-1", ["target-1"], "relates-to", False)


def test_list_links_empty(mock_backend, capsys):
    """Test listing links when no links exist."""
    mock_backend.list_links.return_value = []

    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        link_commands.list_links("entity-1")

    mock_backend.list_links.assert_called_once_with("entity-1", None)
    captured = capsys.readouterr()
    assert "No links found for entity entity-1" in captured.out


def test_list_links_with_results(mock_backend, capsys):
    """Test listing links with results."""
    links = [
        Link(source_id="1", target_id="2", link_type="blocks"),
        Link(source_id="1", target_id="3", link_type="relates-to"),
    ]
    mock_backend.list_links.return_value = links

    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        link_commands.list_links("1")

    mock_backend.list_links.assert_called_once_with("1", None)
    captured = capsys.readouterr()
    assert "Links for entity 1:" in captured.out
    assert "1 --[blocks]--> 2" in captured.out
    assert "1 --[relates-to]--> 3" in captured.out


def test_list_links_with_type_filter(mock_backend):
    """Test listing links with type filter."""
    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        link_commands.list_links("entity-1", type="blocks")

    mock_backend.list_links.assert_called_once_with("entity-1", "blocks")


def test_tree(mock_backend, capsys):
    """Test displaying link tree."""
    tree_data = {
        "entity": {"id": "1", "title": "Main Task", "state": "open"},
        "links": {
            "children": [
                {"id": "2", "title": "Child 1"},
                {"id": "3", "title": "Child 2"},
            ],
            "blocking": [
                {"id": "4", "title": "Blocked Task"},
            ],
            "blocked_by": [],
            "parent": [],
        },
    }
    mock_backend.get_link_tree.return_value = tree_data

    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        link_commands.tree("1")

    mock_backend.get_link_tree.assert_called_once_with("1")
    captured = capsys.readouterr()
    assert "Entity: 1 Main Task (open)" in captured.out
    assert "Children:" in captured.out
    assert "2 Child 1" in captured.out
    assert "3 Child 2" in captured.out
    assert "Blocking:" in captured.out
    assert "4 Blocked Task" in captured.out


def test_tree_empty_links(mock_backend, capsys):
    """Test displaying tree with no links."""
    tree_data = {
        "entity": {"id": "1", "title": "Solo Task", "state": "open"},
        "links": {
            "children": [],
            "blocking": [],
            "blocked_by": [],
            "parent": [],
        },
    }
    mock_backend.get_link_tree.return_value = tree_data

    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        link_commands.tree("1")

    captured = capsys.readouterr()
    assert "Entity: 1 Solo Task (open)" in captured.out
    # Empty link types should not be displayed
    assert "Children:" not in captured.out
    assert "Blocking:" not in captured.out


def test_cycle_no_cycles(mock_backend, capsys):
    """Test finding cycles when none exist."""
    mock_backend.find_cycles.return_value = []

    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        link_commands.cycle()

    mock_backend.find_cycles.assert_called_once()
    captured = capsys.readouterr()
    assert "No cycles found" in captured.out


def test_cycle_with_cycles(mock_backend, capsys):
    """Test finding and displaying cycles."""
    cycles = [
        ["1", "2", "3"],
        ["4", "5"],
    ]
    mock_backend.find_cycles.return_value = cycles

    with patch("entity_manager.cli.get_backend", return_value=mock_backend):
        link_commands.cycle()

    mock_backend.find_cycles.assert_called_once()
    captured = capsys.readouterr()
    assert "Found 2 cycle(s):" in captured.out
    assert "1. 1 -> 2 -> 3 -> 1" in captured.out
    assert "2. 4 -> 5 -> 4" in captured.out

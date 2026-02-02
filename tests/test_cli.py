"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import patch

import pytest

from entity_manager.backends.sqlite import SQLiteBackend
from entity_manager.cli import delete


@pytest.fixture
def sqlite_backend(tmp_path: Path) -> SQLiteBackend:
    """Create a SQLite backend with a temporary database."""
    db_path = str(tmp_path / "test.db")
    return SQLiteBackend(db_path=db_path)


def test_delete_backend_accepts_tuple(sqlite_backend: SQLiteBackend) -> None:
    """Test that delete command properly handles tuple arguments.

    This test ensures the fix for the bug where the CLI's delete function
    was incorrectly passing arguments. The fix uses (*entity_ids,) tuple syntax
    instead of list(entity_ids) which was shadowed by the list command function.
    """
    # Create entities
    e1 = sqlite_backend.create("Task 1")
    e2 = sqlite_backend.create("Task 2")

    # The backend.delete method expects a sequence of entity IDs
    # The CLI's delete function now passes (*entity_ids,) which is a tuple
    # This test verifies the backend accepts a tuple
    sqlite_backend.delete((e1.id, e2.id))

    # Verify entities were deleted
    with pytest.raises(ValueError, match="not found"):
        sqlite_backend.read(e1.id)

    with pytest.raises(ValueError, match="not found"):
        sqlite_backend.read(e2.id)


def test_delete_cli_function_handles_varargs(tmp_path: Path) -> None:
    """Test that the CLI delete function properly handles *args.

    This test verifies that the delete command correctly converts variadic
    arguments to a tuple using (*entity_ids,) syntax, which avoids the
    bug where list(entity_ids) was calling the list command function instead
    of Python's built-in list type.
    """
    db_path = str(tmp_path / "test.db")
    backend = SQLiteBackend(db_path=db_path)

    # Create entities
    e1 = backend.create("Task 1")
    e2 = backend.create("Task 2")
    e3 = backend.create("Task 3")

    # Mock get_backend to return our test backend
    with patch("entity_manager.cli.get_backend", return_value=backend):
        # Call delete with multiple arguments as *args
        delete(e1.id, e2.id, e3.id)

    # Verify all entities were deleted
    with pytest.raises(ValueError, match="not found"):
        backend.read(e1.id)

    with pytest.raises(ValueError, match="not found"):
        backend.read(e2.id)

    with pytest.raises(ValueError, match="not found"):
        backend.read(e3.id)

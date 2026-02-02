"""Tests for backlog.md backend."""

from pathlib import Path

import pytest
import yaml

from entity_manager.backends.backlog import (
    STATUS_MAP_TO_BACKLOG,
    STATUS_MAP_TO_ENTITY,
    BacklogBackend,
)
from entity_manager.models import Entity


@pytest.fixture
def temp_backlog_dir(tmp_path: Path) -> Path:
    """Create temporary backlog directory."""
    tasks_dir = tmp_path / "backlog" / "tasks"
    tasks_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def backlog_backend(temp_backlog_dir: Path) -> BacklogBackend:
    """Create BacklogBackend instance with temp directory."""
    return BacklogBackend(backlog_path=str(temp_backlog_dir / "backlog"))


@pytest.fixture
def sample_task_file(temp_backlog_dir: Path) -> Path:
    """Create sample task file for testing."""
    tasks_dir = temp_backlog_dir / "backlog" / "tasks"
    task_file = tasks_dir / "task-1 - Sample Task.md"
    task_file.write_text(
        """---
id: task-1
title: "Sample Task"
description: "This is a sample task"
status: "To Do"
labels:
  - "feature"
  - "priority:high"
assignee: "@alice"
priority: "high"
dependencies:
  - "task-0"
---
"""
    )
    return task_file


class TestBacklogBackendInit:
    """Tests for BacklogBackend initialization."""

    def test_init_with_path(self, temp_backlog_dir: Path) -> None:
        """Test backend initialization with custom path."""
        backend = BacklogBackend(backlog_path=str(temp_backlog_dir / "backlog"))
        assert backend.backlog_path == temp_backlog_dir / "backlog"
        assert backend.tasks_dir == temp_backlog_dir / "backlog" / "tasks"
        assert backend.tasks_dir.exists()

    def test_init_with_default_path(self, tmp_path: Path) -> None:
        """Test backend initialization with default path."""
        import os

        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            backend = BacklogBackend()
            assert backend.backlog_path == Path.cwd() / "backlog"
            assert backend.tasks_dir == Path.cwd() / "backlog" / "tasks"
        finally:
            os.chdir(original_cwd)


class TestStatusMapping:
    """Tests for status mapping functions."""

    def test_map_status_to_entity(self) -> None:
        """Test mapping Backlog.md status to Entity Manager status."""
        assert BacklogBackend._map_status_to_entity(None, "To Do") == "open"
        assert BacklogBackend._map_status_to_entity(None, "todo") == "open"
        assert BacklogBackend._map_status_to_entity(None, "In Progress") == "in_progress"
        assert BacklogBackend._map_status_to_entity(None, "inprogress") == "in_progress"
        assert BacklogBackend._map_status_to_entity(None, "Done") == "closed"
        # Invalid status defaults to open
        assert BacklogBackend._map_status_to_entity(None, "invalid") == "open"

    def test_map_status_to_backlog(self) -> None:
        """Test mapping Entity Manager status to Backlog.md status."""
        assert BacklogBackend._map_status_to_backlog(None, "open") == "To Do"
        assert BacklogBackend._map_status_to_backlog(None, "in_progress") == "In Progress"
        assert BacklogBackend._map_status_to_backlog(None, "closed") == "Done"
        # Invalid status defaults to To Do
        assert BacklogBackend._map_status_to_backlog(None, "invalid") == "To Do"

    def test_status_map_constants(self) -> None:
        """Test status mapping constants."""
        assert "to do" in STATUS_MAP_TO_ENTITY
        assert STATUS_MAP_TO_ENTITY["to do"] == "open"
        assert "open" in STATUS_MAP_TO_BACKLOG
        assert STATUS_MAP_TO_BACKLOG["open"] == "To Do"


class TestCreate:
    """Tests for creating tasks."""

    def test_create_minimal_task(self, backlog_backend: BacklogBackend) -> None:
        """Test creating a task with minimal fields."""
        entity = backlog_backend.create(properties={"title": "Test Task"})

        assert entity.id == "task-1"
        assert entity.properties["title"] == "Test Task"
        assert entity.properties.get("description", "") == ""
        assert entity.properties.get("status", "open") == "open"
        assert entity.type == "backlog_task"

        # Check file was created
        file_path = backlog_backend.tasks_dir / "task-1 - Test Task.md"
        assert file_path.exists()

    def test_create_task_with_all_fields(self, backlog_backend: BacklogBackend) -> None:
        """Test creating a task with all fields."""
        entity = backlog_backend.create(
            properties={
                "title": "Full Task",
                "description": "Detailed description",
                "feature": "",
                "priority": "high",
                "assignee": "@bob",
            }
        )

        assert entity.id == "task-1"
        assert entity.properties["title"] == "Full Task"
        assert entity.properties["description"] == "Detailed description"
        assert entity.properties["feature"] == ""
        assert entity.properties["priority"] == "high"
        assert entity.properties["assignee"] == "@bob"

    def test_create_generates_sequential_ids(self, backlog_backend: BacklogBackend) -> None:
        """Test that create generates sequential IDs."""
        entity1 = backlog_backend.create(properties={"title": "Task 1"})
        entity2 = backlog_backend.create(properties={"title": "Task 2"})
        entity3 = backlog_backend.create(properties={"title": "Task 3"})

        assert entity1.id == "task-1"
        assert entity2.id == "task-2"
        assert entity3.id == "task-3"

    def test_create_sanitizes_filename(self, backlog_backend: BacklogBackend) -> None:
        """Test that create sanitizes special characters in title."""
        _ = backlog_backend.create(properties={"title": "Task: With / Special \\ <Characters>"})

        # File should be created with sanitized name
        files = list(backlog_backend.tasks_dir.glob("task-1*.md"))
        assert len(files) == 1
        assert ":" not in files[0].name
        assert "/" not in files[0].name

    def test_write_task_file(self, backlog_backend: BacklogBackend) -> None:
        """Test writing task file with valid frontmatter."""
        entity = Entity(
            id="task-1",
            type="default",
            properties={
                "title": "Test Task",
                "description": "Test description",
                "status": "open",
                "feature": "",
                "assignee": "@alice",
            },
            metadata={"priority": "high"},
        )

        file_path = backlog_backend.tasks_dir / "task-1 - Test Task.md"
        backlog_backend._write_task_file(entity, file_path)

        # Verify file content
        content = file_path.read_text()
        assert content.startswith("---")
        assert "---" in content[4:]  # Second yaml delimiter

        # Parse and verify frontmatter
        frontmatter = yaml.safe_load(content.split("---")[1])
        assert frontmatter["id"] == "task-1"
        assert frontmatter["title"] == "Test Task"
        assert frontmatter["description"] == "Test description"
        assert frontmatter["status"] == "To Do"
        assert "feature" in frontmatter["labels"]
        assert frontmatter["assignee"] == "@alice"
        assert frontmatter["priority"] == "high"


class TestRead:
    """Tests for reading tasks."""

    def test_read_existing_task(self, backlog_backend: BacklogBackend, sample_task_file: Path) -> None:
        """Test reading an existing task."""
        entity = backlog_backend.read("task-1")

        assert entity.id == "task-1"
        assert entity.properties["title"] == "Sample Task"
        assert entity.properties["description"] == "This is a sample task"
        assert entity.properties["status"] == "open"
        assert entity.properties["feature"] == ""
        assert entity.properties["priority"] == "high"
        assert entity.properties["assignee"] == "@alice"

    def test_read_parses_labels_correctly(self, backlog_backend: BacklogBackend) -> None:
        """Test that read parses labels with key:value format."""
        task_file = backlog_backend.tasks_dir / "task-1 - Labels Test.md"
        task_file.write_text(
            """---
id: task-1
title: "Labels Test"
labels:
  - "simple"
  - "key:value"
  - "another:complex:value"
---
"""
        )

        entity = backlog_backend.read("task-1")
        assert entity.properties["simple"] == ""
        assert entity.properties["key"] == "value"
        assert entity.properties["another"] == "complex:value"

    def test_read_maps_statuses(self, backlog_backend: BacklogBackend) -> None:
        """Test that read maps Backlog.md statuses to Entity Manager statuses."""
        test_cases = [
            ("To Do", "open"),
            ("In Progress", "in_progress"),
            ("Done", "closed"),
        ]

        for idx, (backlog_status, expected_status) in enumerate(test_cases):
            # Use unique IDs for each test case
            task_id = f"task-status-{idx}"
            task_file = backlog_backend.tasks_dir / f"{task_id} - Status Test.md"
            task_file.write_text(
                f"""---
id: {task_id}
title: "Status Test"
status: "{backlog_status}"
---
"""
            )

            entity = backlog_backend.read(task_id)
            assert entity.properties["status"] == expected_status

    def test_read_nonexistent_task_raises_error(self, backlog_backend: BacklogBackend) -> None:
        """Test reading a non-existent task raises ValueError."""
        with pytest.raises(ValueError, match="Task file not found"):
            backlog_backend.read("task-999")

    def test_read_with_numeric_id(self, backlog_backend: BacklogBackend, sample_task_file: Path) -> None:
        """Test reading task with numeric ID only."""
        entity = backlog_backend.read("1")  # Without "task-" prefix
        assert entity.id == "task-1"


class TestUpdate:
    """Tests for updating tasks."""

    def test_update_title(self, backlog_backend: BacklogBackend, sample_task_file: Path) -> None:
        """Test updating task title."""
        entity = backlog_backend.update("task-1", properties={"title": "Updated Title"})

        assert entity.properties["title"] == "Updated Title"

        # Verify file was updated
        updated_file = backlog_backend.tasks_dir / "task-1 - Updated Title.md"
        assert updated_file.exists()
        # Old file should be removed
        assert not sample_task_file.exists()

    def test_update_description(self, backlog_backend: BacklogBackend, sample_task_file: Path) -> None:
        """Test updating task description."""
        entity = backlog_backend.update("task-1", properties={"description": "New description"})

        assert entity.properties["description"] == "New description"

    def test_update_status(self, backlog_backend: BacklogBackend, sample_task_file: Path) -> None:
        """Test updating task status."""
        entity = backlog_backend.update("task-1", properties={"status": "in_progress"})

        assert entity.properties["status"] == "in_progress"

        # Verify file was updated with correct status
        file_path = backlog_backend._get_task_file_path("task-1")
        frontmatter = backlog_backend._parse_frontmatter(file_path)
        assert frontmatter["status"] == "In Progress"

    def test_update_labels(self, backlog_backend: BacklogBackend, sample_task_file: Path) -> None:
        """Test updating task labels (stored as properties)."""
        new_labels = {"bug": "", "priority": "urgent"}
        entity = backlog_backend.update("task-1", properties=new_labels)

        assert entity.properties["bug"] == ""
        assert entity.properties["priority"] == "urgent"

    def test_update_assignee(self, backlog_backend: BacklogBackend, sample_task_file: Path) -> None:
        """Test updating task assignee."""
        entity = backlog_backend.update("task-1", properties={"assignee": "@charlie"})

        assert entity.properties["assignee"] == "@charlie"

    def test_update_preserves_other_fields(self, backlog_backend: BacklogBackend, sample_task_file: Path) -> None:
        """Test that update preserves fields not being updated."""
        original = backlog_backend.read("task-1")

        updated = backlog_backend.update("task-1", properties={"status": "in_progress"})

        assert updated.properties["title"] == original.properties["title"]
        assert updated.properties["description"] == original.properties["description"]
        assert updated.properties["assignee"] == original.properties["assignee"]


class TestDelete:
    """Tests for deleting tasks."""

    def test_delete_single_task(self, backlog_backend: BacklogBackend, sample_task_file: Path) -> None:
        """Test deleting a single task."""
        backlog_backend.delete(["task-1"])

        assert not sample_task_file.exists()

    def test_delete_multiple_tasks(self, backlog_backend: BacklogBackend) -> None:
        """Test deleting multiple tasks."""
        backlog_backend.create(properties={"title": "Task 1"})
        backlog_backend.create(properties={"title": "Task 2"})
        backlog_backend.create(properties={"title": "Task 3"})

        backlog_backend.delete(["task-1", "task-2"])

        # Verify task-1 and task-2 files are deleted
        assert not list(backlog_backend.tasks_dir.glob("task-1*.md"))
        assert not list(backlog_backend.tasks_dir.glob("task-2*.md"))
        # Verify task-3 still exists
        assert list(backlog_backend.tasks_dir.glob("task-3*.md"))

    def test_delete_nonexistent_task_no_error(self, backlog_backend: BacklogBackend) -> None:
        """Test that deleting non-existent task doesn't raise error."""
        # Should not raise
        backlog_backend.delete(["task-999"])


class TestList:
    """Tests for listing tasks."""

    def test_list_all_tasks(self, backlog_backend: BacklogBackend) -> None:
        """Test listing all tasks."""
        backlog_backend.create(properties={"title": "Task 1"})
        backlog_backend.create(properties={"title": "Task 2"})
        backlog_backend.create(properties={"title": "Task 3"})

        entities = backlog_backend.list_entities()

        assert len(entities) == 3
        titles = {e.properties["title"] for e in entities}
        assert titles == {"Task 1", "Task 2", "Task 3"}

    def test_list_with_status_filter(self, backlog_backend: BacklogBackend) -> None:
        """Test listing tasks with status filter."""
        backlog_backend.create(properties={"title": "Task 1"})
        task2 = backlog_backend.create(properties={"title": "Task 2"})
        task3 = backlog_backend.create(properties={"title": "Task 3"})

        # Update statuses
        backlog_backend.update(task2.id, properties={"status": "in_progress"})
        backlog_backend.update(task3.id, properties={"status": "closed"})

        # List open tasks (using backlog status format)
        open_tasks = backlog_backend.list_entities(filters={"status": "To Do"})
        assert len(open_tasks) == 1
        assert open_tasks[0].properties["title"] == "Task 1"

        # List in_progress tasks
        progress_tasks = backlog_backend.list_entities(filters={"status": "In Progress"})
        assert len(progress_tasks) == 1
        assert progress_tasks[0].properties["title"] == "Task 2"

    def test_list_with_limit(self, backlog_backend: BacklogBackend) -> None:
        """Test listing tasks with limit."""
        backlog_backend.create(properties={"title": "Task 1"})
        backlog_backend.create(properties={"title": "Task 2"})
        backlog_backend.create(properties={"title": "Task 3"})

        entities = backlog_backend.list_entities(limit=2)

        assert len(entities) == 2

    def test_list_sorts_by_id_descending(self, backlog_backend: BacklogBackend) -> None:
        """Test that list returns tasks sorted by ID (descending)."""
        backlog_backend.create(properties={"title": "Task 1"})
        backlog_backend.create(properties={"title": "Task 2"})
        backlog_backend.create(properties={"title": "Task 3"})

        entities = backlog_backend.list_entities()

        # Should be sorted by ID descending (task-3, task-2, task-1)
        assert entities[0].id == "task-3"
        assert entities[1].id == "task-2"
        assert entities[2].id == "task-1"


class TestLinks:
    """Tests for dependency/link operations."""

    def test_add_dependency(self, backlog_backend: BacklogBackend) -> None:
        """Test adding a dependency between tasks."""
        task1 = backlog_backend.create(properties={"title": "Task 1"})
        task2 = backlog_backend.create(properties={"title": "Task 2"})

        backlog_backend.add_link(task2.id, [task1.id], "blocked_by")

        # Verify dependency was added
        links = backlog_backend.list_links(task2.id)
        assert len(links) == 1
        assert links[0].target_id == task1.id
        assert links[0].link_type == "blocked_by"

    def test_add_multiple_dependencies(self, backlog_backend: BacklogBackend) -> None:
        """Test adding multiple dependencies."""
        task1 = backlog_backend.create(properties={"title": "Task 1"})
        task2 = backlog_backend.create(properties={"title": "Task 2"})
        task3 = backlog_backend.create(properties={"title": "Task 3"})

        backlog_backend.add_link(task3.id, [task1.id, task2.id], "blocked_by")

        links = backlog_backend.list_links(task3.id)
        assert len(links) == 2

    def test_remove_dependency(self, backlog_backend: BacklogBackend) -> None:
        """Test removing a dependency."""
        task1 = backlog_backend.create(properties={"title": "Task 1"})
        task2 = backlog_backend.create(properties={"title": "Task 2"})

        backlog_backend.add_link(task2.id, [task1.id], "blocked_by")
        backlog_backend.remove_link(task2.id, [task1.id], "blocked_by")

        links = backlog_backend.list_links(task2.id)
        assert len(links) == 0

    def test_list_links_filters_by_type(self, backlog_backend: BacklogBackend) -> None:
        """Test listing links with type filter."""
        task1 = backlog_backend.create(properties={"title": "Task 1"})
        task2 = backlog_backend.create(properties={"title": "Task 2"})

        backlog_backend.add_link(task2.id, [task1.id], "blocked_by")

        # List with filter
        links = backlog_backend.list_links(task2.id, link_type="blocked_by")
        assert len(links) == 1

        # List with different filter (should return none)
        links = backlog_backend.list_links(task2.id, link_type="parent")
        assert len(links) == 0

    def test_unsupported_link_type_raises_error(self, backlog_backend: BacklogBackend) -> None:
        """Test that unsupported link types raise ValueError."""
        task1 = backlog_backend.create(properties={"title": "Task 1"})
        task2 = backlog_backend.create(properties={"title": "Task 2"})

        with pytest.raises(ValueError, match="Unsupported link type"):
            backlog_backend.add_link(task2.id, [task1.id], "parent")


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_parse_invalid_yaml(self, backlog_backend: BacklogBackend) -> None:
        """Test parsing file with invalid YAML."""
        task_file = backlog_backend.tasks_dir / "task-1 - Invalid.md"
        task_file.write_text(
            """---
id: task-1
title: "Invalid"
labels: [unclosed bracket
---
"""
        )

        with pytest.raises(ValueError, match="Failed to parse frontmatter"):
            backlog_backend._parse_frontmatter(task_file)

    def test_parse_missing_frontmatter(self, backlog_backend: BacklogBackend) -> None:
        """Test parsing file without frontmatter."""
        task_file = backlog_backend.tasks_dir / "task-1 - No Frontmatter.md"
        task_file.write_text("Just some content without frontmatter")

        # Should return empty dict, not raise
        frontmatter = backlog_backend._parse_frontmatter(task_file)
        assert frontmatter == {}

    def test_parse_empty_labels_list(self, backlog_backend: BacklogBackend) -> None:
        """Test parsing empty labels list."""
        assert backlog_backend._parse_labels(None) == {}
        assert backlog_backend._parse_labels([]) == {}

    def test_format_labels_dict(self, backlog_backend: BacklogBackend) -> None:
        """Test formatting labels dict to list."""
        labels = {"key": "value", "simple": ""}
        formatted = backlog_backend._format_labels(labels)

        assert "key:value" in formatted
        assert "simple" in formatted

    def test_get_task_file_path_not_found(self, backlog_backend: BacklogBackend) -> None:
        """Test getting file path for non-existent task."""
        with pytest.raises(ValueError, match="Task file not found"):
            backlog_backend._get_task_file_path("task-999")

    def test_generate_filename_sanitizes(self, backlog_backend: BacklogBackend) -> None:
        """Test filename generation sanitizes special chars."""
        filename = backlog_backend._generate_filename("task-1", "Bad:Chars/Here\\<>|?*")
        assert ":" not in filename
        assert "/" not in filename
        assert filename == "task-1 - BadCharsHere.md"

    def test_generate_filename_limits_length(self, backlog_backend: BacklogBackend) -> None:
        """Test filename generation limits length."""
        long_title = "x" * 200
        filename = backlog_backend._generate_filename("task-1", long_title)
        assert len(filename) < 150  # Should be truncated


class TestGetLinkTree:
    """Tests for get_link_tree method."""

    def test_get_link_tree(self, backlog_backend: BacklogBackend) -> None:
        """Test getting link tree for a task."""
        task1 = backlog_backend.create(properties={"title": "Task 1"})
        task2 = backlog_backend.create(properties={"title": "Task 2"})
        task3 = backlog_backend.create(properties={"title": "Task 3"})

        # Create dependencies: task3 depends on task1 and task2
        backlog_backend.add_link(task3.id, [task1.id, task2.id], "blocked_by")

        tree = backlog_backend.get_link_tree(task3.id)

        assert tree["entity"]["id"] == task3.id
        assert tree["entity"]["title"] == "Task 3"
        assert len(tree["links"]["blocked_by"]) == 2

    def test_get_link_tree_with_missing_target(self, backlog_backend: BacklogBackend) -> None:
        """Test get_link_tree when target doesn't exist."""
        task1 = backlog_backend.create(properties={"title": "Task 1"})

        # Manually add a dependency to non-existent task
        file_path = backlog_backend._get_task_file_path(task1.id)
        frontmatter = backlog_backend._parse_frontmatter(file_path)
        frontmatter["dependencies"] = ["task-999"]
        content = file_path.read_text()
        parts = content.split("---", 2)
        new_content = f"---\n{yaml.dump(frontmatter)}---{parts[2] if len(parts) > 2 else ''}"
        file_path.write_text(new_content)

        # Should not raise, just skip missing target
        tree = backlog_backend.get_link_tree(task1.id)
        assert len(tree["links"]["blocked_by"]) == 0


class TestFindCycles:
    """Tests for find_cycles method."""

    def test_find_no_cycles(self, backlog_backend: BacklogBackend) -> None:
        """Test cycle detection with acyclic graph."""
        task1 = backlog_backend.create(properties={"title": "Task 1"})
        task2 = backlog_backend.create(properties={"title": "Task 2"})
        task3 = backlog_backend.create(properties={"title": "Task 3"})

        # Create chain: task3 -> task2 -> task1
        backlog_backend.add_link(task2.id, [task1.id], "blocked_by")
        backlog_backend.add_link(task3.id, [task2.id], "blocked_by")

        cycles = backlog_backend.find_cycles()
        assert len(cycles) == 0

    def test_find_cycle(self, backlog_backend: BacklogBackend) -> None:
        """Test cycle detection with circular dependency."""
        task1 = backlog_backend.create(properties={"title": "Task 1"})
        task2 = backlog_backend.create(properties={"title": "Task 2"})

        # Create cycle: task1 -> task2 -> task1
        backlog_backend.add_link(task1.id, [task2.id], "blocked_by")
        backlog_backend.add_link(task2.id, [task1.id], "blocked_by")

        cycles = backlog_backend.find_cycles()
        assert len(cycles) > 0
        # Cycle should contain both tasks
        assert any("task-1" in cycle and "task-2" in cycle for cycle in cycles)


class TestGetNextId:
    """Tests for _get_next_id method."""

    def test_get_next_id_empty_directory(self, backlog_backend: BacklogBackend) -> None:
        """Test getting next ID from empty directory."""
        next_id = backlog_backend._get_next_id()
        assert next_id == "task-1"

    def test_get_next_id_existing_tasks(self, backlog_backend: BacklogBackend) -> None:
        """Test getting next ID with existing tasks."""
        backlog_backend.create(properties={"title": "Task 1"})
        backlog_backend.create(properties={"title": "Task 2"})

        next_id = backlog_backend._get_next_id()
        assert next_id == "task-3"


class TestNormalizeIds:
    """Tests for ID normalization in various methods."""

    def test_read_normalizes_id(self, backlog_backend: BacklogBackend) -> None:
        """Test that read normalizes ID without task- prefix."""
        _ = backlog_backend.create(properties={"title": "Test Task"})

        # Read with just the number
        entity = backlog_backend.read("1")
        assert entity.id == "task-1"

    def test_delete_normalizes_ids(self, backlog_backend: BacklogBackend) -> None:
        """Test that delete normalizes IDs."""
        backlog_backend.create(properties={"title": "Task 1"})

        # Delete with just the number
        backlog_backend.delete(["1"])

        # Verify file was deleted
        assert not list(backlog_backend.tasks_dir.glob("task-1*.md"))

    def test_add_link_normalizes_ids(self, backlog_backend: BacklogBackend) -> None:
        """Test that add_link normalizes IDs."""
        _ = backlog_backend.create(properties={"title": "Task 1"})
        _ = backlog_backend.create(properties={"title": "Task 2"})

        # Add link with numeric IDs
        backlog_backend.add_link("2", ["1"], "blocked_by")

        links = backlog_backend.list_links("task-2")
        assert len(links) == 1
        assert links[0].target_id == "task-1"

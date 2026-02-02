"""Integration tests for backlog.md backend."""

from pathlib import Path

import pytest

from entity_manager.backends.backlog import BacklogBackend


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


class TestFullWorkflow:
    """Integration tests for complete CRUD workflows."""

    def test_create_read_update_delete_workflow(self, backlog_backend: BacklogBackend) -> None:
        """Test complete workflow: create, read, update, delete."""
        # Create
        entity = backlog_backend.create(
            properties={
                "title": "Integration Test Task",
                "description": "Testing full workflow",
                "test": "",
                "priority": "high",
                "assignee": "@tester",
            }
        )

        assert entity.id == "task-1"
        assert entity.properties["title"] == "Integration Test Task"

        # Read
        read_entity = backlog_backend.read("task-1")
        assert read_entity.id == "task-1"
        assert read_entity.properties["title"] == "Integration Test Task"
        assert read_entity.properties["description"] == "Testing full workflow"
        assert read_entity.properties["test"] == ""
        assert read_entity.properties["priority"] == "high"
        assert read_entity.properties["assignee"] == "@tester"
        assert read_entity.properties["status"] == "open"

        # Update
        updated = backlog_backend.update(
            "task-1",
            properties={"title": "Updated Task Title", "status": "in_progress"},
        )
        assert updated.properties["title"] == "Updated Task Title"
        assert updated.properties["status"] == "in_progress"
        # Other properties are preserved
        assert updated.properties["description"] == "Testing full workflow"
        assert updated.properties["assignee"] == "@tester"

        # Verify update persisted
        re_read = backlog_backend.read("task-1")
        assert re_read.properties["title"] == "Updated Task Title"
        assert re_read.properties["status"] == "in_progress"

        # Delete
        backlog_backend.delete(["task-1"])

        # Verify deletion
        with pytest.raises(ValueError, match="Task file not found"):
            backlog_backend.read("task-1")

    def test_list_after_multiple_creates(self, backlog_backend: BacklogBackend) -> None:
        """Test listing tasks after creating multiple."""
        # Create multiple tasks
        backlog_backend.create(properties={"title": "First Task"})
        backlog_backend.create(properties={"title": "Second Task"})
        backlog_backend.create(properties={"title": "Third Task"})

        # List all
        entities = backlog_backend.list_entities()
        assert len(entities) == 3

        # Verify titles
        titles = {e.properties["title"] for e in entities}
        assert titles == {"First Task", "Second Task", "Third Task"}

    def test_create_updates_metadata(self, backlog_backend: BacklogBackend) -> None:
        """Test that create adds proper metadata."""
        entity = backlog_backend.create(properties={"title": "Metadata Test"})

        assert "file_path" in entity.metadata
        assert "created" in entity.metadata

    def test_update_adds_timestamp(self, backlog_backend: BacklogBackend) -> None:
        """Test that update adds updated timestamp."""
        entity = backlog_backend.create(properties={"title": "Timestamp Test"})

        # First create should have created timestamp
        assert "created" in entity.metadata

        # Update should add updated timestamp
        updated = backlog_backend.update("task-1", properties={"status": "in_progress"})
        assert "updated" in updated.metadata


class TestDependencyWorkflow:
    """Integration tests for dependency management workflows."""

    def test_create_and_list_dependencies(self, backlog_backend: BacklogBackend) -> None:
        """Test creating tasks with dependencies and listing them."""
        # Create a dependency chain
        task1 = backlog_backend.create(properties={"title": "Foundation Task"})
        task2 = backlog_backend.create(properties={"title": "Dependent Task"})
        task3 = backlog_backend.create(properties={"title": "Top Level Task"})

        # Add dependencies: task3 depends on task2 and task1
        # task2 depends on task1
        backlog_backend.add_link(task2.id, [task1.id], "blocked_by")
        backlog_backend.add_link(task3.id, [task1.id, task2.id], "blocked_by")

        # List dependencies for task3
        links = backlog_backend.list_links(task3.id)
        assert len(links) == 2

        target_ids = {link.target_id for link in links}
        assert task1.id in target_ids
        assert task2.id in target_ids

        # All links should be blocked_by type
        assert all(link.link_type == "blocked_by" for link in links)

    def test_dependency_tree_workflow(self, backlog_backend: BacklogBackend) -> None:
        """Test getting dependency tree for complex relationships."""
        # Create tasks
        task1 = backlog_backend.create(properties={"title": "Database Setup"})
        task2 = backlog_backend.create(properties={"title": "API Layer"})
        task3 = backlog_backend.create(properties={"title": "User Interface"})

        # Create dependencies
        backlog_backend.add_link(task2.id, [task1.id], "blocked_by")
        backlog_backend.add_link(task3.id, [task2.id], "blocked_by")

        # Get link tree for task3
        tree = backlog_backend.get_link_tree(task3.id)

        assert tree["entity"]["id"] == task3.id
        assert tree["entity"]["title"] == "User Interface"
        assert len(tree["links"]["blocked_by"]) == 1
        assert tree["links"]["blocked_by"][0]["id"] == task2.id

    def test_remove_dependencies(self, backlog_backend: BacklogBackend) -> None:
        """Test removing dependencies from a task."""
        task1 = backlog_backend.create(properties={"title": "Task 1"})
        task2 = backlog_backend.create(properties={"title": "Task 2"})
        task3 = backlog_backend.create(properties={"title": "Task 3"})

        # Add multiple dependencies
        backlog_backend.add_link(task3.id, [task1.id, task2.id], "blocked_by")

        # Verify added
        links = backlog_backend.list_links(task3.id)
        assert len(links) == 2

        # Remove one dependency
        backlog_backend.remove_link(task3.id, [task1.id], "blocked_by")

        # Verify removed
        links = backlog_backend.list_links(task3.id)
        assert len(links) == 1
        assert links[0].target_id == task2.id

    def test_circular_dependency_detection(self, backlog_backend: BacklogBackend) -> None:
        """Test detecting circular dependencies."""
        task1 = backlog_backend.create(properties={"title": "Task 1"})
        task2 = backlog_backend.create(properties={"title": "Task 2"})
        task3 = backlog_backend.create(properties={"title": "Task 3"})

        # Create a cycle: task1 -> task2 -> task3 -> task1
        backlog_backend.add_link(task1.id, [task2.id], "blocked_by")
        backlog_backend.add_link(task2.id, [task3.id], "blocked_by")
        backlog_backend.add_link(task3.id, [task1.id], "blocked_by")

        # Detect cycles
        cycles = backlog_backend.find_cycles()
        assert len(cycles) > 0

        # Verify cycle contains our tasks
        cycle = cycles[0]
        assert "task-1" in cycle
        assert "task-2" in cycle
        assert "task-3" in cycle


class TestFilteringAndSorting:
    """Integration tests for filtering and sorting operations."""

    def test_filter_by_status_workflow(self, backlog_backend: BacklogBackend) -> None:
        """Test filtering tasks by different statuses."""
        # Create tasks with different statuses
        task1 = backlog_backend.create(properties={"title": "Todo Task"})
        task2 = backlog_backend.create(properties={"title": "In Progress Task"})
        task3 = backlog_backend.create(properties={"title": "Done Task"})

        backlog_backend.update(task2.id, properties={"status": "in_progress"})
        backlog_backend.update(task3.id, properties={"status": "closed"})

        # Filter by each status (using backlog status format)
        todo_tasks = backlog_backend.list_entities(filters={"status": "To Do"})
        assert len(todo_tasks) == 1
        assert todo_tasks[0].id == task1.id

        progress_tasks = backlog_backend.list_entities(filters={"status": "In Progress"})
        assert len(progress_tasks) == 1
        assert progress_tasks[0].id == task2.id

        done_tasks = backlog_backend.list_entities(filters={"status": "Done"})
        assert len(done_tasks) == 1
        assert done_tasks[0].id == task3.id

    def test_limit_results_workflow(self, backlog_backend: BacklogBackend) -> None:
        """Test limiting number of results."""
        # Create many tasks
        for i in range(10):
            backlog_backend.create(properties={"title": f"Task {i}"})

        # List with limit
        entities = backlog_backend.list_entities(limit=5)
        assert len(entities) == 5

    def test_default_sort_order(self, backlog_backend: BacklogBackend) -> None:
        """Test that list returns tasks in default sort order (newest first)."""
        backlog_backend.create(properties={"title": "First Task"})
        backlog_backend.create(properties={"title": "Second Task"})
        backlog_backend.create(properties={"title": "Third Task"})

        entities = backlog_backend.list_entities()

        # Should be sorted by ID descending (task-3, task-2, task-1)
        assert entities[0].id == "task-3"
        assert entities[1].id == "task-2"
        assert entities[2].id == "task-1"


class TestFilePersistence:
    """Integration tests for file persistence and format."""

    def test_task_file_format(self, backlog_backend: BacklogBackend) -> None:
        """Test that task files are created in correct format."""
        entity = backlog_backend.create(
            properties={
                "title": "Format Test",
                "description": "Testing file format",
                "type": "test",
                "assignee": "@formatter",
            }
        )

        file_path = backlog_backend._get_task_file_path(entity.id)
        content = file_path.read_text()

        # Verify YAML frontmatter structure
        assert content.startswith("---")
        assert "---" in content[4:]

        # Parse and verify frontmatter
        import yaml

        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])

        assert frontmatter["id"] == entity.id
        assert frontmatter["title"] == "Format Test"
        assert frontmatter["description"] == "Testing file format"
        assert frontmatter["status"] == "To Do"
        assert "type:test" in frontmatter["labels"]
        assert frontmatter["assignee"] == "@formatter"

    def test_file_rename_on_title_change(self, backlog_backend: BacklogBackend) -> None:
        """Test that file is renamed when title changes."""
        entity = backlog_backend.create(properties={"title": "Original Title"})

        original_path = backlog_backend._get_task_file_path(entity.id)

        # Update title
        backlog_backend.update(entity.id, properties={"title": "New Title"})

        # Old file should be gone
        assert not original_path.exists()

        # New file should exist
        new_path = backlog_backend._get_task_file_path(entity.id)
        assert new_path.exists()
        assert "New Title" in new_path.name

    def test_metadata_preservation_in_file(self, backlog_backend: BacklogBackend) -> None:
        """Test that created timestamp is preserved in file format."""
        # Create a task normally
        entity = backlog_backend.create(
            properties={
                "title": "Metadata Test",
            }
        )

        # Verify created timestamp is in file
        file_path = backlog_backend._get_task_file_path(entity.id)
        frontmatter = backlog_backend._parse_frontmatter(file_path)

        assert "created" in frontmatter
        assert "updated" in frontmatter


class TestErrorRecovery:
    """Integration tests for error handling and recovery."""

    def test_handle_corrupted_file_gracefully(self, backlog_backend: BacklogBackend) -> None:
        """Test that corrupted files don't crash list operations."""
        # Create valid task
        backlog_backend.create(properties={"title": "Valid Task"})

        # Create corrupted file (use name that won't parse as task-NNN)
        corrupted = backlog_backend.tasks_dir / "corrupted-file.md"
        corrupted.write_text("invalid yaml content: [unclosed")

        # List should skip corrupted file and not crash
        entities = backlog_backend.list_entities()
        assert len(entities) == 1
        assert entities[0].properties["title"] == "Valid Task"

    def test_read_nonexistent_raises_error(self, backlog_backend: BacklogBackend) -> None:
        """Test reading non-existent task raises clear error."""
        with pytest.raises(ValueError, match="Task file not found"):
            backlog_backend.read("task-99999")

    def test_update_nonexistent_raises_error(self, backlog_backend: BacklogBackend) -> None:
        """Test updating non-existent task raises clear error."""
        with pytest.raises(ValueError, match="Task file not found"):
            backlog_backend.update("task-99999", properties={"title": "New Title"})


class TestMultiTaskOperations:
    """Integration tests for operations across multiple tasks."""

    def test_batch_delete_workflow(self, backlog_backend: BacklogBackend) -> None:
        """Test deleting multiple tasks at once."""
        # Create tasks
        for i in range(5):
            backlog_backend.create(properties={"title": f"Task {i}"})

        # Delete multiple
        backlog_backend.delete(["task-1", "task-2", "task-3"])

        # Verify deletions
        entities = backlog_backend.list_entities()
        assert len(entities) == 2

        remaining_ids = {e.id for e in entities}
        assert "task-1" not in remaining_ids
        assert "task-2" not in remaining_ids
        assert "task-3" not in remaining_ids

    def test_complex_dependency_graph(self, backlog_backend: BacklogBackend) -> None:
        """Test working with a complex dependency graph."""
        # Create a diamond dependency graph:
        #     task1
        #     /    \
        # task2  task3
        #     \    /
        #    task4

        task1 = backlog_backend.create(properties={"title": "Foundation"})
        task2 = backlog_backend.create(properties={"title": "Branch 1"})
        task3 = backlog_backend.create(properties={"title": "Branch 2"})
        task4 = backlog_backend.create(properties={"title": "Convergence"})

        # Create dependencies
        backlog_backend.add_link(task2.id, [task1.id], "blocked_by")
        backlog_backend.add_link(task3.id, [task1.id], "blocked_by")
        backlog_backend.add_link(task4.id, [task2.id, task3.id], "blocked_by")

        # Verify each task's dependencies
        task1_links = backlog_backend.list_links(task1.id)
        assert len(task1_links) == 0  # No dependencies

        task2_links = backlog_backend.list_links(task2.id)
        assert len(task2_links) == 1
        assert task2_links[0].target_id == task1.id

        task3_links = backlog_backend.list_links(task3.id)
        assert len(task3_links) == 1
        assert task3_links[0].target_id == task1.id

        task4_links = backlog_backend.list_links(task4.id)
        assert len(task4_links) == 2
        task4_targets = {link.target_id for link in task4_links}
        assert task4_targets == {task2.id, task3.id}


class TestIdFormats:
    """Integration tests for different ID format handling."""

    def test_operations_with_numeric_ids(self, backlog_backend: BacklogBackend) -> None:
        """Test operations using numeric IDs without task- prefix."""
        _ = backlog_backend.create(properties={"title": "Numeric ID Test"})

        # All operations should work with numeric ID
        read = backlog_backend.read("1")
        assert read.id == "task-1"

        updated = backlog_backend.update("1", properties={"status": "in_progress"})
        assert updated.properties["status"] == "in_progress"

        links = backlog_backend.list_links("1")
        assert len(links) == 0

        backlog_backend.delete(["1"])
        with pytest.raises(ValueError):
            backlog_backend.read("1")

    def test_mixed_id_format_operations(self, backlog_backend: BacklogBackend) -> None:
        """Test operations with mixed ID formats."""
        _ = backlog_backend.create(properties={"title": "Task 1"})
        _ = backlog_backend.create(properties={"title": "Task 2"})

        # Add link using different formats
        backlog_backend.add_link("task-1", ["2"], "blocked_by")

        # Should be able to list with either format
        links_full = backlog_backend.list_links("task-1")
        links_numeric = backlog_backend.list_links("1")

        assert len(links_full) == 1
        assert len(links_numeric) == 1
        assert links_full[0].target_id == "task-2"
        assert links_numeric[0].target_id == "task-2"

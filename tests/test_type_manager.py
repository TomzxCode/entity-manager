"""Tests for type management."""

import tempfile

import pytest

from entity_manager.models import PropertyDefinition, PropertyType
from entity_manager.type_manager import TypeManager


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for type configs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path

        yield Path(tmpdir)


def test_type_manager_init(temp_config_dir):
    """Test TypeManager initialization."""
    manager = TypeManager(config_dir=temp_config_dir)
    assert manager.config_file == temp_config_dir / "types.yaml"


def test_get_default_type(temp_config_dir):
    """Test getting the default type."""
    manager = TypeManager(config_dir=temp_config_dir)
    default_type = manager.get_type("default")

    assert default_type.name == "default"
    assert default_type.properties == []
    assert default_type.description == "Default entity type"


def test_create_type(temp_config_dir):
    """Test creating a new entity type."""
    manager = TypeManager(config_dir=temp_config_dir)

    properties = [
        PropertyDefinition(
            name="severity",
            type=PropertyType.STRING,
            default="medium",
            required=True,
            options=["low", "medium", "high"],
        ),
    ]

    entity_type = manager.create_type(
        name="bug",
        properties=properties,
        description="A bug report",
    )

    assert entity_type.name == "bug"
    assert len(entity_type.properties) == 1
    assert entity_type.properties[0].name == "severity"
    assert entity_type.description == "A bug report"


def test_list_types(temp_config_dir):
    """Test listing all types."""
    manager = TypeManager(config_dir=temp_config_dir)

    types = manager.list_types()
    assert len(types) >= 1  # At least default type

    type_names = [t.name for t in types]
    assert "default" in type_names


def test_delete_type(temp_config_dir):
    """Test deleting a type."""
    manager = TypeManager(config_dir=temp_config_dir)

    # Create a type
    properties = [
        PropertyDefinition(name="test", type=PropertyType.STRING),
    ]
    manager.create_type("test_type", properties)

    # Delete it
    manager.delete_type("test_type")

    # Verify it's gone
    types = manager.list_types()
    type_names = [t.name for t in types]
    assert "test_type" not in type_names


def test_cannot_delete_default_type(temp_config_dir):
    """Test that the default type cannot be deleted."""
    manager = TypeManager(config_dir=temp_config_dir)

    with pytest.raises(ValueError, match="Cannot delete default type"):
        manager.delete_type("default")


def test_type_persistence(temp_config_dir):
    """Test that types persist across manager instances."""
    # Create type with first manager
    manager1 = TypeManager(config_dir=temp_config_dir)
    properties = [
        PropertyDefinition(name="title", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="priority", type=PropertyType.INTEGER, default=0),
    ]
    manager1.create_type("task", properties)

    # Load with second manager
    manager2 = TypeManager(config_dir=temp_config_dir)
    entity_type = manager2.get_type("task")

    assert entity_type.name == "task"
    assert len(entity_type.properties) == 2
    assert entity_type.properties[0].name == "title"
    assert entity_type.properties[1].name == "priority"


def test_update_type(temp_config_dir):
    """Test updating an existing type."""
    manager = TypeManager(config_dir=temp_config_dir)

    # Create a type
    properties = [
        PropertyDefinition(name="title", type=PropertyType.STRING, required=True),
    ]
    manager.create_type("feature", properties)

    # Update description
    updated = manager.update_type("feature", description="A new feature")
    assert updated.description == "A new feature"

    # Update properties
    new_properties = [
        PropertyDefinition(name="title", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="priority", type=PropertyType.INTEGER, default=1),
    ]
    updated = manager.update_type("feature", properties=new_properties)
    assert len(updated.properties) == 2
    assert updated.properties[1].name == "priority"


def test_get_nonexistent_type_falls_back_to_default(temp_config_dir):
    """Test that getting a non-existent type falls back to default."""
    manager = TypeManager(config_dir=temp_config_dir)

    entity_type = manager.get_type("nonexistent")
    assert entity_type.name == "default"

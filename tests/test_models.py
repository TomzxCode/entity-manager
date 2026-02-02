"""Tests for data models."""

from entity_manager.models import Entity, EntityType, Link, PropertyDefinition, PropertyType


def test_entity_creation() -> None:
    """Test entity creation with defaults."""
    entity = Entity(id="test-1")
    assert entity.id == "test-1"
    assert entity.type == "default"
    assert entity.properties == {}
    assert entity.metadata == {}


def test_entity_with_type_and_properties() -> None:
    """Test entity creation with type and properties."""
    entity = Entity(
        id="test-2",
        type="bug",
        properties={"title": "Fix bug", "severity": "high"},
    )
    assert entity.id == "test-2"
    assert entity.type == "bug"
    assert entity.properties == {"title": "Fix bug", "severity": "high"}


def test_property_type_enum() -> None:
    """Test PropertyType enum values."""
    assert PropertyType.STRING.value == "string"
    assert PropertyType.INTEGER.value == "integer"
    assert PropertyType.BOOLEAN.value == "boolean"
    assert PropertyType.ARRAY.value == "array"


def test_property_definition() -> None:
    """Test PropertyDefinition dataclass."""
    prop = PropertyDefinition(
        name="severity",
        type=PropertyType.STRING,
        default="medium",
        required=True,
        options=["low", "medium", "high"],
    )
    assert prop.name == "severity"
    assert prop.type == PropertyType.STRING
    assert prop.default == "medium"
    assert prop.required is True
    assert prop.options == ["low", "medium", "high"]


def test_entity_type() -> None:
    """Test EntityType dataclass."""
    props = [
        PropertyDefinition(name="title", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="severity", type=PropertyType.STRING, default="low"),
    ]
    entity_type = EntityType(name="bug", properties=props, description="A bug report")

    assert entity_type.name == "bug"
    assert len(entity_type.properties) == 2
    assert entity_type.description == "A bug report"


def test_entity_type_get_property_defaults() -> None:
    """Test getting default values from EntityType."""
    props = [
        PropertyDefinition(name="title", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="severity", type=PropertyType.STRING, default="low"),
        PropertyDefinition(name="status", type=PropertyType.STRING, default="open"),
    ]
    entity_type = EntityType(name="bug", properties=props)

    defaults = entity_type.get_property_defaults()
    assert defaults == {"severity": "low", "status": "open"}


def test_entity_type_get_property() -> None:
    """Test getting a property by name from EntityType."""
    props = [
        PropertyDefinition(name="title", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="severity", type=PropertyType.STRING, default="low"),
    ]
    entity_type = EntityType(name="bug", properties=props)

    prop = entity_type.get_property("severity")
    assert prop is not None
    assert prop.name == "severity"
    assert prop.default == "low"

    missing = entity_type.get_property("nonexistent")
    assert missing is None


def test_entity_type_validate_property() -> None:
    """Test property validation in EntityType."""
    props = [
        PropertyDefinition(name="title", type=PropertyType.STRING, required=True),
        PropertyDefinition(name="severity", type=PropertyType.STRING, default="low", options=["low", "medium", "high"]),
    ]
    entity_type = EntityType(name="bug", properties=props)

    # Valid value
    valid, error = entity_type.validate_property("severity", "medium")
    assert valid is True
    assert error == ""

    # Invalid option
    valid, error = entity_type.validate_property("severity", "critical")
    assert valid is False
    assert "must be one of" in error

    # Missing required
    valid, error = entity_type.validate_property("title", None)
    assert valid is False
    assert "required" in error.lower()


def test_link_creation() -> None:
    """Test link creation."""
    link = Link(source_id=1, target_id=2, link_type="relates_to")
    assert link.source_id == 1
    assert link.target_id == 2
    assert link.link_type == "relates_to"

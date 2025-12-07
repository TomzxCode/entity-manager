"""Tests for data models."""

from entity_manager.models import Entity, Link


def test_entity_creation() -> None:
    """Test entity creation with defaults."""
    entity = Entity(id=1, title="Test Entity")
    assert entity.id == 1
    assert entity.title == "Test Entity"
    assert entity.description == ""
    assert entity.labels == {}
    assert entity.assignee is None
    assert entity.status == "open"


def test_entity_with_labels() -> None:
    """Test entity creation with labels."""
    entity = Entity(
        id=2,
        title="Bug Fix",
        labels={"type": "bug", "priority": "high"},
    )
    assert entity.labels == {"type": "bug", "priority": "high"}


def test_link_creation() -> None:
    """Test link creation."""
    link = Link(source_id=1, target_id=2, link_type="relates_to")
    assert link.source_id == 1
    assert link.target_id == 2
    assert link.link_type == "relates_to"

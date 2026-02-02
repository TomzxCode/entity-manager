"""Data models for entity manager."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PropertyType(Enum):
    """Supported property types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    ARRAY = "array"
    DICT = "dict"


@dataclass
class PropertyDefinition:
    """Definition of a property for an entity type."""

    name: str
    type: PropertyType
    default: Any = None
    required: bool = False
    description: str = ""
    options: list[Any] | None = None


@dataclass
class EntityType:
    """Definition of an entity type with its properties."""

    name: str
    properties: list[PropertyDefinition]
    description: str = ""

    def get_property_defaults(self) -> dict[str, Any]:
        """Get default values for all properties."""
        return {p.name: p.default for p in self.properties if p.default is not None}

    def get_property(self, name: str) -> PropertyDefinition | None:
        """Get a property definition by name."""
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None

    def validate_property(self, name: str, value: Any) -> tuple[bool, str]:
        """Validate a property value."""
        from entity_manager.validation import validate_type

        prop = self.get_property(name)
        if not prop:
            return False, f"Unknown property: {name}"

        if prop.required and value is None:
            return False, f"Required property '{name}' is missing"

        if value is None:
            return True, ""

        if not validate_type(value, prop.type):
            return False, f"Invalid type for {name}: expected {prop.type.value}"

        if prop.options and value not in prop.options:
            return False, f"Invalid value for {name}: must be one of {prop.options}"

        return True, ""


@dataclass
class Entity:
    """Represents an entity with configurable properties."""

    id: str
    type: str = "default"
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Link:
    """Represents a link between entities."""

    source_id: str
    target_id: str
    link_type: str = "relates_to"

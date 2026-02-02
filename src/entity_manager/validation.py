"""Property validation utilities."""

from datetime import datetime
from typing import Any

from entity_manager.models import PropertyType


class ValidationError(Exception):
    """Raised when property validation fails."""

    def __init__(self, property_name: str, message: str) -> None:
        self.property_name = property_name
        self.message = message
        super().__init__(f"Validation failed for '{property_name}': {message}")


def validate_type(value: Any, property_type: PropertyType) -> bool:
    """Check if value matches the expected type."""
    if property_type == PropertyType.STRING:
        return isinstance(value, str)
    elif property_type == PropertyType.INTEGER:
        return isinstance(value, int) and not isinstance(value, bool)
    elif property_type == PropertyType.FLOAT:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    elif property_type == PropertyType.BOOLEAN:
        return isinstance(value, bool)
    elif property_type == PropertyType.ARRAY:
        return isinstance(value, list)
    elif property_type == PropertyType.DICT:
        return isinstance(value, dict)
    elif property_type == PropertyType.DATETIME:
        if isinstance(value, datetime):
            return True
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return True
            except ValueError:
                return False
        return False
    return False


def validate_property_value(
    property_name: str,
    value: Any,
    property_type: PropertyType,
    required: bool = False,
    options: list[Any] | None = None,
) -> None:
    """Validate a property value.

    Args:
        property_name: Name of the property
        value: Value to validate
        property_type: Expected type
        required: Whether the property is required
        options: Optional list of valid values

    Raises:
        ValidationError: If validation fails
    """
    if required and value is None:
        raise ValidationError(property_name, "This property is required")

    if value is None:
        return

    if not validate_type(value, property_type):
        expected_type = property_type.value
        actual_type = type(value).__name__
        raise ValidationError(property_name, f"Expected type '{expected_type}', got '{actual_type}'")

    if options and value not in options:
        options_str = ", ".join([str(o) for o in options])
        raise ValidationError(property_name, f"Value must be one of: {options_str}")


def coerce_property_value(value: Any, property_type: PropertyType) -> Any:
    """Coerce a string value to the target property type.

    Useful for CLI inputs which are always strings.

    Args:
        value: Value to coerce
        property_type: Target type

    Returns:
        Coerced value

    Raises:
        ValidationError: If coercion fails
    """
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

    try:
        if property_type == PropertyType.STRING:
            return str(value)
        elif property_type == PropertyType.INTEGER:
            return int(value)
        elif property_type == PropertyType.FLOAT:
            return float(value)
        elif property_type == PropertyType.BOOLEAN:
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)
        elif property_type == PropertyType.ARRAY:
            if isinstance(value, str):
                return [item.strip() for item in value.split(",")]
            return list(value)
        elif property_type == PropertyType.DICT:
            if isinstance(value, str):
                import json

                return json.loads(value)
            return dict(value)
        elif property_type == PropertyType.DATETIME:
            if isinstance(value, str):
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            return value
    except (ValueError, json.JSONDecodeError) as e:
        raise ValidationError("coercion", f"Failed to coerce value '{value}' to type {property_type.value}: {e}")

    return value

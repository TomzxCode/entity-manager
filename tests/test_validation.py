"""Tests for validation utilities."""

import pytest

from entity_manager.models import PropertyType
from entity_manager.validation import ValidationError, coerce_property_value, validate_property_value, validate_type


def test_validate_type_string():
    """Test string type validation."""
    assert validate_type("hello", PropertyType.STRING) is True
    assert validate_type(123, PropertyType.STRING) is False
    assert validate_type(None, PropertyType.STRING) is False


def test_validate_type_integer():
    """Test integer type validation."""
    assert validate_type(42, PropertyType.INTEGER) is True
    assert validate_type(0, PropertyType.INTEGER) is True
    assert validate_type(3.14, PropertyType.INTEGER) is False
    assert validate_type(True, PropertyType.INTEGER) is False  # bool is subclass of int
    assert validate_type("42", PropertyType.INTEGER) is False


def test_validate_type_float():
    """Test float type validation."""
    assert validate_type(3.14, PropertyType.FLOAT) is True
    assert validate_type(42, PropertyType.FLOAT) is True
    assert validate_type(True, PropertyType.FLOAT) is False
    assert validate_type("3.14", PropertyType.FLOAT) is False


def test_validate_type_boolean():
    """Test boolean type validation."""
    assert validate_type(True, PropertyType.BOOLEAN) is True
    assert validate_type(False, PropertyType.BOOLEAN) is True
    assert validate_type(1, PropertyType.BOOLEAN) is False
    assert validate_type("true", PropertyType.BOOLEAN) is False


def test_validate_type_array():
    """Test array type validation."""
    assert validate_type([1, 2, 3], PropertyType.ARRAY) is True
    assert validate_type([], PropertyType.ARRAY) is True
    assert validate_type("not an array", PropertyType.ARRAY) is False
    assert validate_type({"key": "value"}, PropertyType.ARRAY) is False


def test_validate_type_dict():
    """Test dict type validation."""
    assert validate_type({"key": "value"}, PropertyType.DICT) is True
    assert validate_type({}, PropertyType.DICT) is True
    assert validate_type("not a dict", PropertyType.DICT) is False
    assert validate_type([1, 2, 3], PropertyType.DICT) is False


def test_validate_type_datetime():
    """Test datetime type validation."""
    from datetime import datetime

    assert validate_type(datetime.now(), PropertyType.DATETIME) is True
    assert validate_type("2024-01-01T00:00:00", PropertyType.DATETIME) is True
    assert validate_type("2024-01-01T00:00:00Z", PropertyType.DATETIME) is True
    assert validate_type("not a datetime", PropertyType.DATETIME) is False


def test_validate_property_value_success():
    """Test successful property validation."""
    validate_property_value("title", "Hello", PropertyType.STRING, required=True)
    validate_property_value("count", 42, PropertyType.INTEGER, required=False)


def test_validate_property_value_required_missing():
    """Test that required property validation fails when value is None."""
    with pytest.raises(ValidationError, match="required"):
        validate_property_value("title", None, PropertyType.STRING, required=True)


def test_validate_property_value_type_mismatch():
    """Test that type mismatch raises ValidationError."""
    with pytest.raises(ValidationError, match="Expected type"):
        validate_property_value("count", "not a number", PropertyType.INTEGER)


def test_validate_property_value_invalid_option():
    """Test that invalid option raises ValidationError."""
    with pytest.raises(ValidationError, match="must be one of"):
        validate_property_value("severity", "critical", PropertyType.STRING, options=["low", "medium", "high"])


def test_coerce_string():
    """Test coercing to string."""
    assert coerce_property_value(42, PropertyType.STRING) == "42"
    assert coerce_property_value(None, PropertyType.STRING) is None
    assert coerce_property_value("  hello  ", PropertyType.STRING) == "hello"


def test_coerce_integer():
    """Test coercing to integer."""
    assert coerce_property_value("42", PropertyType.INTEGER) == 42
    assert coerce_property_value("  42  ", PropertyType.INTEGER) == 42
    assert coerce_property_value(None, PropertyType.INTEGER) is None


def test_coerce_float():
    """Test coercing to float."""
    assert coerce_property_value("3.14", PropertyType.FLOAT) == 3.14
    assert coerce_property_value("42", PropertyType.FLOAT) == 42.0


def test_coerce_boolean():
    """Test coercing to boolean."""
    assert coerce_property_value("true", PropertyType.BOOLEAN) is True
    assert coerce_property_value("TRUE", PropertyType.BOOLEAN) is True
    assert coerce_property_value("1", PropertyType.BOOLEAN) is True
    assert coerce_property_value("yes", PropertyType.BOOLEAN) is True
    assert coerce_property_value("on", PropertyType.BOOLEAN) is True
    assert coerce_property_value("false", PropertyType.BOOLEAN) is False
    assert coerce_property_value("0", PropertyType.BOOLEAN) is False
    assert coerce_property_value("no", PropertyType.BOOLEAN) is False


def test_coerce_array():
    """Test coercing to array."""
    assert coerce_property_value("a,b,c", PropertyType.ARRAY) == ["a", "b", "c"]
    assert coerce_property_value(" a , b , c ", PropertyType.ARRAY) == ["a", "b", "c"]


def test_coerce_dict():
    """Test coercing to dict."""
    result = coerce_property_value('{"key": "value"}', PropertyType.DICT)
    assert result == {"key": "value"}


def test_coerce_datetime():
    """Test coercing to datetime."""
    from datetime import datetime

    result = coerce_property_value("2024-01-01T12:00:00", PropertyType.DATETIME)
    assert isinstance(result, datetime)

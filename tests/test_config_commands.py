"""Tests for config commands."""

from entity_manager.config_commands import _redact_value


def test_redact_value_short_token() -> None:
    """Test redaction of short token (8 chars or less)."""
    assert _redact_value("github.token", "abc123") == "-redacted-"
    assert _redact_value("github.token", "abcdefgh") == "-redacted-"


def test_redact_value_long_token() -> None:
    """Test redaction of long token (more than 8 chars)."""
    assert _redact_value("github.token", "abcdefghijk") == "abcd...hijk"
    assert _redact_value("notion.token", "ghp_1234567890abcdef") == "ghp_...cdef"


def test_redact_value_non_sensitive_key() -> None:
    """Test that non-sensitive keys are not redacted."""
    assert _redact_value("user.name", "tom") == "tom"
    assert _redact_value("backend.type", "markdown") == "markdown"


def test_redact_value_password_key() -> None:
    """Test redaction of password keys."""
    assert _redact_value("database.password", "pass1234") == "-redacted-"
    assert _redact_value("database.password", "mylongpassword123") == "mylo...d123"


def test_redact_value_secret_key() -> None:
    """Test redaction of secret keys."""
    assert _redact_value("api.secret", "abc") == "-redacted-"
    assert _redact_value("api.secret", "supersecretkey123") == "supe...y123"


def test_redact_value_api_key() -> None:
    """Test redaction of api_key keys."""
    assert _redact_value("service.api_key", "key1234") == "-redacted-"
    assert _redact_value("service.api_key", "my_api_key_12345") == "my_a...2345"


def test_redact_value_auth_key() -> None:
    """Test redaction of auth keys."""
    assert _redact_value("bearer.auth", "token") == "-redacted-"
    assert _redact_value("bearer.auth", "bearer_token_abc123") == "bear...c123"


def test_redact_value_empty_string() -> None:
    """Test redaction of empty string."""
    assert _redact_value("github.token", "") == ""


def test_redact_value_case_insensitive() -> None:
    """Test that key matching is case-insensitive."""
    assert _redact_value("GitHub.Token", "abcdefghijk") == "abcd...hijk"
    assert _redact_value("GITHUB.TOKEN", "abcdefghijk") == "abcd...hijk"

"""Extended tests for configuration commands."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from entity_manager.config import Config
from entity_manager.config_commands import get, init, list_config, set, unset


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config(temp_config_dir):
    """Create a mock config."""
    return Config(config_dir=temp_config_dir)


def test_set_local(mock_config, capsys):
    """Test setting a local config value."""
    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        set("test_key", "test_value", global_=False)

    assert mock_config.get("test_key") == "test_value"
    captured = capsys.readouterr()
    assert "Set test_key = test_value (local)" in captured.out


def test_set_global(mock_config, capsys):
    """Test setting a global config value."""
    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        set("test_key", "test_value", global_=True)

    assert mock_config.get("test_key") == "test_value"
    captured = capsys.readouterr()
    assert "Set test_key = test_value (global)" in captured.out


def test_unset_local(mock_config, capsys):
    """Test unsetting a local config value."""
    mock_config.set("test_key", "test_value")

    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        unset("test_key", global_=False)

    assert mock_config.get("test_key") is None
    captured = capsys.readouterr()
    assert "Unset test_key (local)" in captured.out


def test_unset_global(mock_config, capsys):
    """Test unsetting a global config value."""
    mock_config.set("test_key", "test_value")

    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        unset("test_key", global_=True)

    captured = capsys.readouterr()
    assert "Unset test_key (global)" in captured.out


def test_get_existing_value(mock_config, capsys):
    """Test getting an existing config value."""
    mock_config.set("test_key", "test_value")

    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        get("test_key", global_=False)

    captured = capsys.readouterr()
    assert "test_key = test_value" in captured.out


def test_get_nonexistent_value(mock_config, capsys):
    """Test getting a nonexistent config value."""
    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        get("nonexistent_key", global_=False)

    captured = capsys.readouterr()
    assert "nonexistent_key is not set" in captured.out


def test_get_sensitive_value_redacted(mock_config, capsys):
    """Test that sensitive values are redacted."""
    mock_config.set("github.token", "secret_token_12345")

    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        get("github.token", global_=False)

    captured = capsys.readouterr()
    assert "secr...2345" in captured.out
    assert "secret_token_12345" not in captured.out


def test_list_empty_config(mock_config, capsys):
    """Test listing empty config."""
    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        list_config(global_=False)

    captured = capsys.readouterr()
    assert "No local configuration settings" in captured.out


def test_list_config_with_values(mock_config, capsys):
    """Test listing config with values."""
    mock_config.set("key1", "value1")
    mock_config.set("key2", "value2")

    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        list_config(global_=False)

    captured = capsys.readouterr()
    assert "Configuration settings:" in captured.out
    assert "key1 = value1" in captured.out
    assert "key2 = value2" in captured.out


def test_list_config_global(mock_config, capsys):
    """Test listing global config."""
    mock_config.set("key1", "value1")

    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        list_config(global_=True)

    captured = capsys.readouterr()
    assert "Global settings:" in captured.out


def test_list_config_redacts_sensitive(mock_config, capsys):
    """Test that listing config redacts sensitive values."""
    mock_config.set("github.token", "secret_token_12345")
    mock_config.set("normal_key", "normal_value")

    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        list_config(global_=False)

    captured = capsys.readouterr()
    assert "secr...2345" in captured.out
    assert "secret_token_12345" not in captured.out
    assert "normal_key = normal_value" in captured.out


def test_init_github_backend(mock_config):
    """Test initializing GitHub backend."""
    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        with patch("entity_manager.config_commands.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["github", "owner_name", "repo_name", "token_value"]
            init(global_=False)

    assert mock_config.get("backend") == "github"
    assert mock_config.get("github.owner") == "owner_name"
    assert mock_config.get("github.repository") == "repo_name"
    assert mock_config.get("github.token") == "token_value"


def test_init_beads_backend(mock_config):
    """Test initializing Beads backend."""
    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        with patch("entity_manager.config_commands.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["beads", "/path/to/project"]
            init(global_=False)

    assert mock_config.get("backend") == "beads"
    assert mock_config.get("beads.project_path") == "/path/to/project"


def test_init_notion_backend(mock_config):
    """Test initializing Notion backend."""
    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        with patch("entity_manager.config_commands.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["notion", "notion_token_value", "database_id_value"]
            init(global_=False)

    assert mock_config.get("backend") == "notion"
    assert mock_config.get("notion.token") == "notion_token_value"
    assert mock_config.get("notion.database_id") == "database_id_value"


def test_init_backlog_backend(mock_config):
    """Test initializing Backlog backend."""
    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        with patch("entity_manager.config_commands.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["backlog", "/path/to/backlog.md"]
            init(global_=False)

    assert mock_config.get("backend") == "backlog"
    assert mock_config.get("backlog.path") == "/path/to/backlog.md"


def test_init_sqlite_backend(mock_config):
    """Test initializing SQLite backend."""
    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        with patch("entity_manager.config_commands.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["sqlite", "/path/to/db.sqlite"]
            init(global_=False)

    assert mock_config.get("backend") == "sqlite"
    assert mock_config.get("sqlite.db_path") == "/path/to/db.sqlite"


def test_init_markdown_backend(mock_config):
    """Test initializing Markdown backend."""
    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        with patch("entity_manager.config_commands.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["markdown", "/path/to/markdown"]
            init(global_=False)

    assert mock_config.get("backend") == "markdown"
    assert mock_config.get("markdown.directory_path") == "/path/to/markdown"


def test_init_with_existing_backend(mock_config):
    """Test initializing with existing backend."""
    mock_config.set("backend", "github")
    mock_config.set("github.owner", "old_owner")

    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        with patch("entity_manager.config_commands.Prompt.ask") as mock_prompt:
            # User accepts existing backend and updates owner
            mock_prompt.side_effect = ["github", "new_owner", "repo_name", "token_value"]
            init(global_=False)

    assert mock_config.get("backend") == "github"
    assert mock_config.get("github.owner") == "new_owner"


def test_init_invalid_backend_retry(mock_config):
    """Test initializing with invalid backend, then retry."""
    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        with patch("entity_manager.config_commands.Prompt.ask") as mock_prompt:
            # First invalid, then valid
            mock_prompt.side_effect = ["invalid_backend", "sqlite", "/path/to/db.sqlite"]
            init(global_=False)

    assert mock_config.get("backend") == "sqlite"


def test_init_with_empty_optional_values(mock_config):
    """Test initializing with empty optional values."""
    with patch("entity_manager.config_commands.get_config", return_value=mock_config):
        with patch("entity_manager.config_commands.Prompt.ask") as mock_prompt:
            # Empty values for optional fields
            mock_prompt.side_effect = ["github", "", "", ""]
            init(global_=False)

    assert mock_config.get("backend") == "github"
    # Empty values should not be set
    assert mock_config.get("github.owner") is None
    assert mock_config.get("github.repository") is None
    assert mock_config.get("github.token") is None

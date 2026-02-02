"""Tests for configuration management."""

import tempfile
from pathlib import Path

import pytest

from entity_manager.config import Config, get_config


@pytest.fixture
def temp_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config_with_custom_dir(temp_dir):
    """Create a Config instance with a custom directory."""
    return Config(config_dir=temp_dir)


def test_config_init_with_custom_dir(temp_dir):
    """Test Config initialization with custom directory."""
    config = Config(config_dir=temp_dir)
    assert config.config_dir == temp_dir
    assert config.config_file == temp_dir / "config.yaml"
    assert config.config_dir.exists()


def test_config_init_global():
    """Test Config initialization with global flag."""
    config = Config(use_global=True)
    assert config.is_global is True
    assert config.config_dir == Path.home() / ".entity-manager"


def test_config_init_local():
    """Test Config initialization with local flag."""
    config = Config(use_global=False)
    assert config.is_global is False
    assert config.config_dir == Path.cwd() / ".entity-manager"


def test_set_and_get(config_with_custom_dir):
    """Test setting and getting config values."""
    config = config_with_custom_dir
    config.set("test_key", "test_value")
    assert config.get("test_key") == "test_value"


def test_get_with_default(config_with_custom_dir):
    """Test getting config value with default."""
    config = config_with_custom_dir
    assert config.get("nonexistent_key", "default_value") == "default_value"


def test_get_nonexistent_returns_none(config_with_custom_dir):
    """Test getting nonexistent key returns None."""
    config = config_with_custom_dir
    assert config.get("nonexistent_key") is None


def test_unset(config_with_custom_dir):
    """Test unsetting config values."""
    config = config_with_custom_dir
    config.set("test_key", "test_value")
    assert config.get("test_key") == "test_value"
    config.unset("test_key")
    assert config.get("test_key") is None


def test_unset_nonexistent_key(config_with_custom_dir):
    """Test unsetting a key that doesn't exist."""
    config = config_with_custom_dir
    # Should not raise an error
    config.unset("nonexistent_key")


def test_list_empty(config_with_custom_dir):
    """Test listing empty config."""
    config = config_with_custom_dir
    assert config.list() == {}


def test_list_with_values(config_with_custom_dir):
    """Test listing config with values."""
    config = config_with_custom_dir
    config.set("key1", "value1")
    config.set("key2", "value2")
    result = config.list()
    assert result == {"key1": "value1", "key2": "value2"}


def test_persistence(temp_dir):
    """Test that config persists across instances."""
    config1 = Config(config_dir=temp_dir)
    config1.set("test_key", "test_value")

    config2 = Config(config_dir=temp_dir)
    assert config2.get("test_key") == "test_value"


def test_global_fallback(temp_dir):
    """Test that local config falls back to global config."""
    # Create global config
    global_dir = temp_dir / "global"
    global_dir.mkdir()
    global_config = Config(config_dir=global_dir, use_global=True)
    global_config.set("global_key", "global_value")

    # Create local config with global fallback
    local_dir = temp_dir / "local"
    local_dir.mkdir()

    # Mock the global config file location by creating a config with custom dir
    local_config = Config(config_dir=local_dir, use_global=False)
    # Manually set the global config for testing
    local_config._global_config = {"global_key": "global_value"}

    # Local config should fall back to global
    assert local_config.get("global_key") == "global_value"


def test_local_overrides_global(temp_dir):
    """Test that local config overrides global config."""
    local_config = Config(config_dir=temp_dir, use_global=False)
    local_config._global_config = {"key": "global_value"}
    local_config.set("key", "local_value")

    # Local value should override global
    assert local_config.get("key") == "local_value"


def test_list_merges_global_and_local(temp_dir):
    """Test that list() merges global and local config."""
    local_config = Config(config_dir=temp_dir, use_global=False)
    local_config._global_config = {"global_key": "global_value", "shared_key": "global_shared"}
    local_config.set("local_key", "local_value")
    local_config.set("shared_key", "local_shared")

    result = local_config.list()
    assert result == {
        "global_key": "global_value",
        "local_key": "local_value",
        "shared_key": "local_shared",  # Local overrides global
    }


def test_list_global_only(temp_dir):
    """Test list() for global config only."""
    config = Config(config_dir=temp_dir, use_global=True)
    config.set("key1", "value1")
    config.set("key2", "value2")

    result = config.list()
    assert result == {"key1": "value1", "key2": "value2"}


def test_load_invalid_yaml(temp_dir):
    """Test loading invalid YAML raises error."""
    config_file = temp_dir / "config.yaml"
    config_file.write_text("invalid: yaml: content: [")

    with pytest.raises(ValueError, match="Failed to load config"):
        Config(config_dir=temp_dir)


def test_save_failure(temp_dir, monkeypatch):
    """Test save failure handling."""
    config = Config(config_dir=temp_dir)

    # Make the directory read-only to cause save failure
    def mock_open(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)

    with pytest.raises(ValueError, match="Failed to save config"):
        config.set("key", "value")


def test_load_global_config_failure(temp_dir, monkeypatch):
    """Test graceful handling of global config load failure."""
    # Create a local config that will try to load global config
    global_config_file = Path.home() / ".entity-manager" / "config.yaml"

    # Mock the global config file to raise an exception
    original_open = open

    def mock_open(file, *args, **kwargs):
        if str(file) == str(global_config_file):
            raise Exception("Mock error")
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    # Should not raise, just log a warning
    config = Config(config_dir=temp_dir, use_global=False)
    assert config._global_config == {}


def test_get_config_function():
    """Test the get_config helper function."""
    config = get_config(use_global=False)
    assert isinstance(config, Config)
    assert config.is_global is False

    config_global = get_config(use_global=True)
    assert isinstance(config_global, Config)
    assert config_global.is_global is True

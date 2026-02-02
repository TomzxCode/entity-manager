"""Configuration commands for entity manager CLI."""

from cyclopts import App

from entity_manager.config import get_config

config_app = App(name="config", help="Manage configuration")

SENSITIVE_KEY_PATTERNS = ("token", "password", "secret", "api_key", "auth")


def _redact_value(key: str, value: str) -> str:
    """Redact a sensitive configuration value.

    Shows first 4 and last 4 characters, or "-redacted-" if 8 chars or less.

    Args:
        key: Configuration key
        value: Configuration value to potentially redact

    Returns:
        Original value or redacted version
    """
    key_lower = key.lower()
    if not any(pattern in key_lower for pattern in SENSITIVE_KEY_PATTERNS):
        return value
    if not value:
        return value
    if len(value) <= 8:
        return "-redacted-"
    return f"{value[:4]}...{value[-4:]}"


@config_app.command
def set(key: str, value: str, global_: bool = False) -> None:
    """Set a configuration setting.

    Args:
        key: Configuration key
        value: Configuration value
        global_: If True, set in global config. If False, set in local config.
    """
    config = get_config(use_global=global_)
    config.set(key, value)
    scope = "global" if global_ else "local"
    print(f"Set {key} = {value} ({scope})")


@config_app.command
def unset(key: str, global_: bool = False) -> None:
    """Unset a configuration setting.

    Args:
        key: Configuration key
        global_: If True, unset from global config. If False, unset from local config.
    """
    config = get_config(use_global=global_)
    config.unset(key)
    scope = "global" if global_ else "local"
    print(f"Unset {key} ({scope})")


@config_app.command
def get(key: str, global_: bool = False) -> None:
    """Get the value of a configuration setting.

    Args:
        key: Configuration key
        global_: If True, get from global config only. If False, get with global fallback.
    """
    config = get_config(use_global=global_)
    value = config.get(key)
    if value is None:
        print(f"{key} is not set")
    else:
        redacted_value = _redact_value(key, value)
        print(f"{key} = {redacted_value}")


@config_app.command(name="list")
def list_config(global_: bool = False) -> None:
    """List all configuration settings.

    Args:
        global_: If True, list global config only. If False, list merged config.
    """
    config = get_config(use_global=global_)
    settings = config.list()

    if not settings:
        scope = "global" if global_ else "local"
        print(f"No {scope} configuration settings")
        return

    scope = "Global" if global_ else "Configuration"
    print(f"{scope} settings:\n")
    for key, value in settings.items():
        redacted_value = _redact_value(key, value)
        print(f"{key} = {redacted_value}")

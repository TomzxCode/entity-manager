"""Configuration management for entity-manager using YAML files."""

from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()


class Config:
    """Configuration manager using YAML file storage.

    Supports both local (repository-level) and global (user-level) configuration.
    Local config is stored in .entity-manager/config.yaml in the current directory.
    Global config is stored in ~/.entity-manager/config.yaml.

    When reading, values are looked up in local config first, then global config.
    """

    def __init__(self, use_global: bool = False, config_dir: Path | None = None) -> None:
        """Initialize configuration manager.

        Args:
            use_global: If True, use global config only. If False, use local config with global fallback.
            config_dir: Custom directory to store config file (overrides use_global)
        """
        if config_dir is not None:
            # Custom config directory
            self.config_dir = Path(config_dir)
            self.is_global = use_global
        elif use_global:
            # Global config in home directory
            self.config_dir = Path.home() / ".entity-manager"
            self.is_global = True
        else:
            # Local config in current directory
            self.config_dir = Path.cwd() / ".entity-manager"
            self.is_global = False

        self.config_file = self.config_dir / "config.yaml"

        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load existing config or initialize empty
        self._config: dict[str, Any] = self._load()

        # For local config, also load global config as fallback
        self._global_config: dict[str, Any] = {}
        if not self.is_global:
            global_config_file = Path.home() / ".entity-manager" / "config.yaml"
            if global_config_file.exists():
                try:
                    with open(global_config_file, "r") as f:
                        self._global_config = yaml.safe_load(f) or {}
                except Exception as e:
                    logger.warning("Failed to load global config", error=str(e))

        logger.debug("Config initialized", config_file=str(self.config_file), is_global=self.is_global)

    def _load(self) -> dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Configuration dictionary
        """
        if not self.config_file.exists():
            logger.debug("Config file does not exist, initializing empty config")
            return {}

        try:
            with open(self.config_file, "r") as f:
                config = yaml.safe_load(f) or {}
                logger.debug("Config loaded successfully", keys=list(config.keys()))
                return config
        except Exception as e:
            logger.error("Failed to load config", error=str(e))
            raise ValueError(f"Failed to load config from {self.config_file}: {e}") from e

    def _save(self) -> None:
        """Save configuration to YAML file."""
        try:
            with open(self.config_file, "w") as f:
                yaml.safe_dump(self._config, f, default_flow_style=False, sort_keys=False)
            logger.debug("Config saved successfully")
        except Exception as e:
            logger.error("Failed to save config", error=str(e))
            raise ValueError(f"Failed to save config to {self.config_file}: {e}") from e

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a configuration value.

        For local config, checks local config first, then falls back to global config.

        Args:
            key: Configuration key
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        # Check local config first
        if key in self._config:
            value = self._config[key]
            logger.debug("Getting config value from local", key=key)
            return value

        # Fall back to global config if not in local
        if not self.is_global and key in self._global_config:
            value = self._global_config[key]
            logger.debug("Getting config value from global", key=key)
            return value

        logger.debug("Config value not found", key=key)
        return default

    def set(self, key: str, value: str) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        logger.debug("Setting config value", key=key)
        self._config[key] = value
        self._save()

    def unset(self, key: str) -> None:
        """Remove a configuration value.

        Args:
            key: Configuration key
        """
        logger.debug("Unsetting config value", key=key)
        if key in self._config:
            del self._config[key]
            self._save()

    def list(self) -> dict[str, str]:
        """List all configuration settings.

        For local config, merges global config with local config (local takes precedence).

        Returns:
            Dictionary of all config settings
        """
        if self.is_global:
            logger.debug("Listing global config values", count=len(self._config))
            return self._config.copy()
        else:
            # Merge global and local, with local taking precedence
            merged = self._global_config.copy()
            merged.update(self._config)
            logger.debug("Listing merged config values", count=len(merged))
            return merged


def get_config(use_global: bool = False) -> Config:
    """Get a configuration instance.

    Args:
        use_global: If True, return global config. If False, return local config with global fallback.

    Returns:
        Config instance
    """
    return Config(use_global=use_global)

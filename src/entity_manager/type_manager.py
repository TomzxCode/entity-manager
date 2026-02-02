"""Type management for entity types."""

from pathlib import Path
from typing import Any

import structlog
import yaml

from entity_manager.models import EntityType, PropertyDefinition, PropertyType

logger = structlog.get_logger()


class TypeManager:
    """Manages entity type definitions."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize type manager.

        Args:
            config_dir: Custom config directory (uses local .entity-manager by default)
        """
        if config_dir:
            self.config_dir = config_dir
        else:
            self.config_dir = Path.cwd() / ".entity-manager"

        self.config_file = self.config_dir / "types.yaml"
        self._type_config: dict[str, EntityType] | None = None

    def _load(self) -> dict[str, EntityType]:
        """Load type configuration from YAML file."""
        if not self.config_file.exists():
            logger.debug("Types file does not exist, creating default types")
            default_types = self._get_default_types()
            self._save_types_dict(default_types)
            return default_types

        try:
            with open(self.config_file, "r") as f:
                data = yaml.safe_load(f) or {}
                return self._dict_to_types(data.get("types", {}))
        except Exception as e:
            logger.error("Failed to load types", error=str(e))
            raise ValueError(f"Failed to load types from {self.config_file}: {e}") from e

    def _save_types_dict(self, types: dict[str, EntityType]) -> None:
        """Save type configuration to YAML file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.config_file, "w") as f:
                yaml.safe_dump({"types": self._types_to_dict(types)}, f, default_flow_style=False, sort_keys=False)
            logger.debug("Types saved successfully")
        except Exception as e:
            logger.error("Failed to save types", error=str(e))
            raise ValueError(f"Failed to save types to {self.config_file}: {e}") from e

    def _get_default_types(self) -> dict[str, EntityType]:
        """Get default type configuration."""
        default_type = EntityType(name="default", properties=[], description="Default entity type")
        return {"default": default_type}

    def _dict_to_types(self, data: dict[str, Any]) -> dict[str, EntityType]:
        """Convert dictionary from YAML to EntityType objects."""
        types = {}
        for name, type_data in data.items():
            props = []
            for prop_name, prop_data in type_data.get("properties", {}).items():
                props.append(
                    PropertyDefinition(
                        name=prop_name,
                        type=PropertyType(prop_data.get("type", "string")),
                        default=prop_data.get("default"),
                        required=prop_data.get("required", False),
                        description=prop_data.get("description", ""),
                        options=prop_data.get("options"),
                    )
                )
            types[name] = EntityType(
                name=name,
                properties=props,
                description=type_data.get("description", ""),
            )
        return types

    def _types_to_dict(self, types: dict[str, EntityType]) -> dict[str, Any]:
        """Convert EntityType objects to dictionary for YAML storage."""
        result = {}
        for name, entity_type in types.items():
            props = {}
            for prop in entity_type.properties:
                props[prop.name] = {
                    "type": prop.type.value,
                    "default": prop.default,
                    "required": prop.required,
                    "description": prop.description,
                }
                if prop.options:
                    props[prop.name]["options"] = prop.options
            result[name] = {
                "description": entity_type.description,
                "properties": props,
            }
        return result

    def get_type(self, type_name: str) -> EntityType:
        """Get an entity type by name.

        Args:
            type_name: Name of the type to retrieve

        Returns:
            EntityType object

        Raises:
            ValueError: If type doesn't exist
        """
        if self._type_config is None:
            self._type_config = self._load()

        entity_type = self._type_config.get(type_name)
        if not entity_type:
            # Fall back to default type
            entity_type = self._type_config.get("default")
            if not entity_type:
                logger.warning("No types configured, using default")
                return self._get_default_types()["default"]

        return entity_type

    def list_types(self) -> list[EntityType]:
        """List all available entity types.

        Returns:
            List of EntityType objects
        """
        if self._type_config is None:
            self._type_config = self._load()

        return list(self._type_config.values())

    def create_type(
        self,
        name: str,
        properties: list[PropertyDefinition],
        description: str = "",
    ) -> EntityType:
        """Create a new entity type.

        Args:
            name: Type name
            properties: List of property definitions
            description: Type description

        Returns:
            Created EntityType
        """
        if self._type_config is None:
            self._type_config = self._load()

        entity_type = EntityType(name=name, properties=properties, description=description)

        self._type_config[name] = entity_type
        self._save_types_dict(self._type_config)

        logger.info("Entity type created", type_name=name)
        return entity_type

    def update_type(
        self,
        name: str,
        properties: list[PropertyDefinition] | None = None,
        description: str | None = None,
    ) -> EntityType:
        """Update an existing entity type.

        Args:
            name: Type name
            properties: New property definitions (None = keep existing)
            description: New description (None = keep existing)

        Returns:
            Updated EntityType

        Raises:
            ValueError: If type doesn't exist
        """
        if self._type_config is None:
            self._type_config = self._load()

        entity_type = self._type_config.get(name)
        if not entity_type:
            raise ValueError(f"Type '{name}' not found")

        if properties is not None:
            entity_type.properties = properties
        if description is not None:
            entity_type.description = description

        self._save_types_dict(self._type_config)

        logger.info("Entity type updated", type_name=name)
        return entity_type

    def delete_type(self, name: str) -> None:
        """Delete an entity type.

        Args:
            name: Type name to delete

        Raises:
            ValueError: If trying to delete default type or type doesn't exist
        """
        if name == "default":
            raise ValueError("Cannot delete default type")

        if self._type_config is None:
            self._type_config = self._load()

        if name not in self._type_config:
            raise ValueError(f"Type '{name}' not found")

        del self._type_config[name]
        self._save_types_dict(self._type_config)

        logger.info("Entity type deleted", type_name=name)

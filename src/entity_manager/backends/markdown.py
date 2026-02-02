"""Markdown file-based backend implementation."""

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import structlog
import yaml

from entity_manager.backend import Backend
from entity_manager.models import Entity, Link

logger = structlog.get_logger()


# Link storage file
LINKS_FILE = "_links.yaml"


class MarkdownBackend(Backend):
    """Markdown file-based backend using markdown files for entity storage."""

    def __init__(self, directory_path: str = ".") -> None:
        """Initialize markdown backend.

        Args:
            directory_path: Path to directory containing markdown entity files
        """
        self.directory_path = Path(directory_path).resolve()
        logger.debug("Initializing markdown backend", directory_path=str(self.directory_path))

        # Create directory if it doesn't exist
        self.directory_path.mkdir(parents=True, exist_ok=True)

        logger.info("Markdown backend initialized", directory_path=str(self.directory_path))

    def _get_entity_path(self, entity_id: str) -> Path:
        """Get the file path for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Path to the markdown file for this entity
        """
        return self.directory_path / f"{entity_id}.md"

    def _get_links_path(self) -> Path:
        """Get the path to the links storage file.

        Returns:
            Path to the links YAML file
        """
        return self.directory_path / LINKS_FILE

    def _generate_entity_id(self) -> str:
        """Generate a unique entity ID.

        Returns:
            Unique entity ID based on timestamp and counter
        """
        import time

        # Use timestamp and a counter for uniqueness
        timestamp = int(time.time() * 1000)
        counter = 0
        while True:
            entity_id = f"md-{timestamp}-{counter:04d}"
            if not self._get_entity_path(entity_id).exists():
                return entity_id
            counter += 1

    def _parse_entity_file(self, file_path: Path) -> Entity | None:
        """Parse a markdown entity file into an Entity object.

        File format:
        ---
        id: md-123-0001
        type: default
        title: Entity Title
        status: open
        assignee: username
        labels:
            key1: value1
            key2: value2
        ---
        Optional description content here.
        Additional markdown content.

        Args:
            file_path: Path to the markdown file

        Returns:
            Entity object or None if parsing fails
        """
        logger.debug("Parsing entity file", file_path=str(file_path))

        try:
            content = file_path.read_text()

            # Extract YAML frontmatter
            frontmatter_match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
            if not frontmatter_match:
                logger.warning("Invalid entity file format", file_path=str(file_path))
                return None

            frontmatter_text = frontmatter_match.group(1)
            description = frontmatter_match.group(2).strip()

            # Parse YAML frontmatter
            frontmatter = yaml.safe_load(frontmatter_text)
            if not isinstance(frontmatter, dict):
                logger.warning("Invalid frontmatter format", file_path=str(file_path))
                return None

            entity_id = frontmatter.get("id")
            entity_type = frontmatter.get("type", "default")
            title = frontmatter.get("title")

            if not entity_id or not title:
                logger.warning("Missing required fields in entity file", file_path=str(file_path))
                return None

            # Build properties dict from frontmatter
            properties: dict[str, Any] = {
                "title": str(title),
                "description": description,
                "status": frontmatter.get("status", "open"),
            }

            # Add assignee if present
            assignee = frontmatter.get("assignee")
            if assignee:
                properties["assignee"] = assignee

            # Merge labels into properties
            labels = frontmatter.get("labels", {})
            if isinstance(labels, dict):
                properties.update(labels)

            entity = Entity(
                id=str(entity_id),
                type=entity_type,
                properties=properties,
                metadata={"file_path": str(file_path)},
            )
            logger.debug("Parsed entity successfully", entity_id=entity.id)
            return entity

        except Exception as e:
            logger.error("Error parsing entity file", file_path=str(file_path), error=str(e))
            return None

    def _write_entity_file(self, entity: Entity) -> None:
        """Write an entity to a markdown file.

        Args:
            entity: Entity object to write
        """
        file_path = self._get_entity_path(entity.id)

        # Build YAML frontmatter
        frontmatter = {
            "id": entity.id,
            "type": entity.type,
        }

        # Extract standard fields from properties
        title = entity.properties.get("title", "")
        description = entity.properties.get("description", "")
        status = entity.properties.get("status", "open")
        assignee = entity.properties.get("assignee")

        if title:
            frontmatter["title"] = title
        if description:
            frontmatter["description"] = description
        if status:
            frontmatter["status"] = status
        if assignee:
            frontmatter["assignee"] = assignee

        # Extract labels (properties that aren't standard fields)
        standard_fields = {"title", "description", "status", "assignee"}
        labels = {k: v for k, v in entity.properties.items() if k not in standard_fields}
        if labels:
            frontmatter["labels"] = labels

        # Write file with YAML frontmatter
        frontmatter_text = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        content = f"---\n{frontmatter_text}---\n{description}\n"

        file_path.write_text(content)
        logger.debug("Wrote entity file", entity_id=entity.id, file_path=str(file_path))

    def _load_links(self) -> dict[str, dict[str, list[str]]]:
        """Load links from the links storage file.

        Returns:
            Dictionary mapping source_id -> link_type -> list of target_ids
        """
        links_path = self._get_links_path()
        if not links_path.exists():
            return {}

        try:
            content = links_path.read_text()
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.error("Error loading links file", links_path=str(links_path), error=str(e))

        return {}

    def _save_links(self, links: dict[str, dict[str, list[str]]]) -> None:
        """Save links to the links storage file.

        Args:
            links: Dictionary mapping source_id -> link_type -> list of target_ids
        """
        links_path = self._get_links_path()
        links_path.write_text(yaml.dump(links, default_flow_style=False, sort_keys=True))
        logger.debug("Saved links file", links_path=str(links_path))

    def create(
        self,
        type: str = "default",
        properties: dict[str, Any] | None = None,
    ) -> Entity:
        """Create a new entity as a markdown file."""
        properties = properties or {}
        title = properties.get("title", "")
        assignee = properties.get("assignee")

        logger.info("Creating markdown entity", title=title, assignee=assignee)

        entity_id = self._generate_entity_id()

        # Build properties with defaults
        entity_properties: dict[str, Any] = {
            "title": title,
            "description": properties.get("description", ""),
            "status": "open",
        }

        # Add assignee if provided
        if assignee:
            entity_properties["assignee"] = assignee

        # Merge other properties
        for key, value in properties.items():
            if key not in ("title", "description", "assignee"):
                entity_properties[key] = value

        entity = Entity(
            id=entity_id,
            type=type,
            properties=entity_properties,
            metadata={"file_path": str(self._get_entity_path(entity_id))},
        )

        self._write_entity_file(entity)
        logger.info("Markdown entity created", entity_id=entity_id)
        return entity

    def read(self, entity_id: str) -> Entity:
        """Read an entity by ID from markdown file."""
        logger.info("Reading markdown entity", entity_id=entity_id)

        file_path = self._get_entity_path(entity_id)
        if not file_path.exists():
            raise ValueError(f"Entity not found: {entity_id}")

        entity = self._parse_entity_file(file_path)
        if entity is None:
            raise ValueError(f"Failed to parse entity: {entity_id}")

        logger.debug("Markdown entity read successfully", entity_id=entity_id)
        return entity

    def update(
        self,
        entity_id: str,
        type: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> Entity:
        """Update an entity in the markdown file."""
        properties = properties or {}
        title = properties.get("title")
        status = properties.get("status")

        logger.info("Updating markdown entity", entity_id=entity_id, title=title, status=status)

        entity = self.read(entity_id)

        # Update type if provided
        if type is not None:
            entity.type = type

        # Update properties
        for key, value in properties.items():
            if value is not None:
                entity.properties[key] = value

        self._write_entity_file(entity)
        logger.info("Markdown entity updated successfully", entity_id=entity_id)
        return entity

    def delete(self, entity_ids: list[str]) -> None:
        """Delete entity markdown files."""
        if not entity_ids:
            logger.info("No entity IDs provided for deletion")
            return
        logger.info("Deleting markdown entities", entity_ids=entity_ids, count=len(entity_ids))

        for entity_id in entity_ids:
            file_path = self._get_entity_path(entity_id)
            if file_path.exists():
                file_path.unlink()
                logger.debug("Deleted entity file", entity_id=entity_id)

        # Also remove any links involving deleted entities
        self._remove_links_for_entities(entity_ids)

        logger.info("Markdown entities deleted successfully", count=len(entity_ids))

    def _remove_links_for_entities(self, entity_ids: list[str]) -> None:
        """Remove all links involving the specified entities.

        Args:
            entity_ids: List of entity IDs to remove links for
        """
        links = self._load_links()
        entity_ids_set = set(entity_ids)

        # Remove links where source or target is a deleted entity
        for source_id in list(links.keys()):
            if source_id in entity_ids_set:
                del links[source_id]
            else:
                for link_type in list(links[source_id].keys()):
                    links[source_id][link_type] = [
                        target_id for target_id in links[source_id][link_type] if target_id not in entity_ids_set
                    ]
                    if not links[source_id][link_type]:
                        del links[source_id][link_type]

                if not links[source_id]:
                    del links[source_id]

        self._save_links(links)

    def list_entities(
        self,
        filters: dict[str, str] | None = None,
        sort_by: str | None = None,
        limit: int | None = None,
    ) -> list[Entity]:
        """List all entities from markdown files."""
        logger.info("Listing markdown entities", filters=filters, sort_by=sort_by, limit=limit)

        entities = []
        for file_path in self.directory_path.glob("*.md"):
            # Skip the links file
            if file_path.name == LINKS_FILE:
                continue

            entity = self._parse_entity_file(file_path)
            if entity:
                entities.append(entity)

        # Apply filters
        if filters:
            for key, value in filters.items():
                if key == "type":
                    entities = [e for e in entities if e.type == value]
                else:
                    entities = [e for e in entities if e.properties.get(key) == value]

        # Apply sorting
        if sort_by:
            reverse = sort_by.startswith("-")
            sort_key = sort_by.lstrip("-")

            if sort_key == "title":
                entities.sort(key=lambda e: str(e.properties.get("title", "")).lower(), reverse=reverse)
            elif sort_key == "status":
                entities.sort(key=lambda e: e.properties.get("status", ""), reverse=reverse)
            elif sort_key == "assignee":
                entities.sort(key=lambda e: e.properties.get("assignee") or "", reverse=reverse)

        # Apply limit
        if limit:
            entities = entities[:limit]

        logger.info("Listed markdown entities", count=len(entities))
        return entities

    def add_link(self, source_id: str, target_ids: list[str], link_type: str) -> None:
        """Add links between entities."""
        logger.info("Adding link to markdown entity", source_id=source_id, target_ids=target_ids, link_type=link_type)

        # Verify entities exist
        try:
            self.read(source_id)
            for target_id in target_ids:
                self.read(target_id)
        except ValueError as e:
            logger.error("Entity not found for link", error=str(e))
            raise

        # Load existing links
        links = self._load_links()

        # Add new links
        if source_id not in links:
            links[source_id] = {}

        if link_type not in links[source_id]:
            links[source_id][link_type] = []

        for target_id in target_ids:
            if target_id not in links[source_id][link_type]:
                links[source_id][link_type].append(target_id)

        self._save_links(links)
        logger.info("Link added successfully", source_id=source_id, target_ids=target_ids, link_type=link_type)

    def remove_link(self, source_id: str, target_ids: list[str], link_type: str, recursive: bool = False) -> None:
        """Remove links between entities."""
        logger.info(
            "Removing link from markdown entity", source_id=source_id, target_ids=target_ids, link_type=link_type
        )

        links = self._load_links()

        # Remove direct links
        if source_id in links and link_type in links[source_id]:
            for target_id in target_ids:
                if target_id in links[source_id][link_type]:
                    links[source_id][link_type].remove(target_id)

            # Clean up empty link type lists
            if not links[source_id][link_type]:
                del links[source_id][link_type]

            # Clean up empty source entries
            if not links[source_id]:
                del links[source_id]

        # Save changes before recursive calls
        self._save_links(links)

        # Handle recursive removal
        if recursive:
            for target_id in target_ids:
                # Reload links to get the latest state
                current_links = self._load_links()
                if target_id in current_links:
                    # Find all links from this target and remove them recursively
                    for inner_link_type in list(current_links[target_id].keys()):
                        inner_targets = current_links[target_id][inner_link_type][:]
                        if inner_targets:
                            self.remove_link(target_id, inner_targets, inner_link_type, recursive=True)

        logger.info("Link removed successfully", source_id=source_id, target_ids=target_ids, link_type=link_type)

    def list_links(self, entity_id: str, link_type: str | None = None) -> list[Link]:
        """List all links for an entity."""
        logger.debug("Listing links for markdown entity", entity_id=entity_id, link_type=link_type)

        links = self._load_links()
        result = []

        # Get outgoing links
        if entity_id in links:
            for lt, target_ids in links[entity_id].items():
                if link_type is None or lt == link_type:
                    for target_id in target_ids:
                        result.append(Link(source_id=entity_id, target_id=target_id, link_type=lt))

        # Get incoming links (inverse lookup)
        for source_id, link_types in links.items():
            for lt, target_ids in link_types.items():
                if entity_id in target_ids and (link_type is None or lt == link_type):
                    # For incoming links, we need to handle inverse types
                    inverse_type = self._get_inverse_link_type(lt)
                    result.append(Link(source_id=source_id, target_id=entity_id, link_type=inverse_type))

        logger.debug("Listed links", entity_id=entity_id, count=len(result))
        return result

    def _get_inverse_link_type(self, link_type: str) -> str:
        """Get the inverse link type.

        Args:
            link_type: Original link type

        Returns:
            Inverse link type
        """
        inverse_map = {
            "blocked by": "blocking",
            "blocking": "blocked by",
            "parent": "children",
            "children": "parent",
            "depends-on": "depended-on-by",
        }
        # If no explicit inverse mapping exists, create a generic inverse name
        if link_type not in inverse_map:
            # Convert "some-link" to "some-link-by" or similar
            if link_type.endswith("-on"):
                return link_type[:-3] + "-on-by"
            else:
                return f"{link_type}-inverse"
        return inverse_map.get(link_type, link_type)

    def get_link_tree(self, entity_id: str) -> dict[str, Any]:
        """Get the link tree for an entity.

        Returns:
            Dictionary with structure:
            {
                "entity": {
                    "id": str,
                    "title": str,
                    "state": str
                },
                "links": {
                    "<link_type>": list[dict],  # Dynamically populated
                    ...
                }
            }
        """
        logger.info("Getting link tree for markdown entity", entity_id=entity_id)

        # Get the main entity
        entity = self.read(entity_id)

        # Load all links
        links = self._load_links()

        # Initialize tree structure with dynamic links
        tree: dict[str, Any] = {
            "entity": {
                "id": entity.id,
                "title": entity.properties.get("title", ""),
                "state": entity.properties.get("status", ""),
            },
            "links": defaultdict(list),
        }

        # Helper to get entity info
        def get_entity_info(eid: str) -> dict[str, str] | None:
            try:
                e = self.read(eid)
                return {
                    "id": e.id,
                    "title": e.properties.get("title", ""),
                    "state": e.properties.get("status", ""),
                }
            except ValueError:
                return None

        # Get outgoing links (all types)
        if entity_id in links:
            for link_type, target_ids in links[entity_id].items():
                for target_id in target_ids:
                    info = get_entity_info(target_id)
                    if info:
                        tree["links"][link_type].append(info)

        # Get incoming links (all types, with inverse relationship)
        for source_id, link_types in links.items():
            for link_type, target_ids in link_types.items():
                if entity_id in target_ids:
                    info = get_entity_info(source_id)
                    if info:
                        # Add as inverse relationship
                        inverse_type = self._get_inverse_link_type(link_type)
                        tree["links"][inverse_type].append(info)

        # Convert defaultdict to regular dict for cleaner output
        tree["links"] = dict(tree["links"])

        # Log link counts
        link_counts = {k: len(v) for k, v in tree["links"].items()}
        logger.info("Link tree retrieved", entity_id=entity_id, link_counts=link_counts)

        return tree

    def find_cycles(self) -> list[list[str]]:
        """Find cycles in the link graph using DFS."""
        logger.debug("Finding cycles in markdown link graph")

        links = self._load_links()

        # Build adjacency list for graph traversal
        graph: dict[str, set[str]] = defaultdict(set)
        all_entities = set()

        for source_id, link_types in links.items():
            all_entities.add(source_id)
            for link_type, target_ids in link_types.items():
                for target_id in target_ids:
                    all_entities.add(target_id)
                    graph[source_id].add(target_id)

        # Also add entities with no links
        for entity in self.list_entities():
            all_entities.add(entity.id)
            if entity.id not in graph:
                graph[entity.id] = set()

        # Find cycles using DFS with coloring
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {node: WHITE for node in all_entities}
        cycles: list[list[str]] = []
        path: list[str] = []

        def dfs(node: str) -> None:
            nonlocal path
            color[node] = GRAY
            path.append(node)

            for neighbor in graph[node]:
                if color[neighbor] == GRAY:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif color[neighbor] == WHITE:
                    dfs(neighbor)

            path.pop()
            color[node] = BLACK

        for node in all_entities:
            if color[node] == WHITE:
                dfs(node)

        logger.info("Found cycles", count=len(cycles))
        return cycles

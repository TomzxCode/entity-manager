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
            title = frontmatter.get("title")
            status = frontmatter.get("status", "open")
            assignee = frontmatter.get("assignee")
            labels = frontmatter.get("labels", {})

            if not entity_id or not title:
                logger.warning("Missing required fields in entity file", file_path=str(file_path))
                return None

            entity = Entity(
                id=str(entity_id),
                title=str(title),
                description=description,
                labels=labels if isinstance(labels, dict) else {},
                assignee=assignee if assignee else None,
                status=str(status),
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
            "title": entity.title,
            "status": entity.status,
        }

        if entity.description:
            frontmatter["description"] = entity.description

        if entity.labels:
            frontmatter["labels"] = entity.labels

        if entity.assignee:
            frontmatter["assignee"] = entity.assignee

        # Write file with YAML frontmatter
        frontmatter_text = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        content = f"---\n{frontmatter_text}---\n{entity.description}\n"

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
        title: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Create a new entity as a markdown file."""
        logger.info("Creating markdown entity", title=title, assignee=assignee)

        entity_id = self._generate_entity_id()

        entity = Entity(
            id=entity_id,
            title=title,
            description=description,
            labels=labels or {},
            assignee=assignee,
            status="open",
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
        title: str | None = None,
        description: str | None = None,
        labels: dict[str, str] | None = None,
        status: str | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Update an entity in the markdown file."""
        logger.info("Updating markdown entity", entity_id=entity_id, title=title, status=status)

        entity = self.read(entity_id)

        if title is not None:
            entity.title = title
        if description is not None:
            entity.description = description
        if labels is not None:
            entity.labels = labels
        if status is not None:
            entity.status = status
        if assignee is not None:
            entity.assignee = assignee

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
            if "status" in filters:
                entities = [e for e in entities if e.status == filters["status"]]
            if "assignee" in filters:
                entities = [e for e in entities if e.assignee == filters["assignee"]]

        # Apply sorting
        if sort_by:
            reverse = sort_by.startswith("-")
            sort_key = sort_by.lstrip("-")

            if sort_key == "title":
                entities.sort(key=lambda e: e.title.lower(), reverse=reverse)
            elif sort_key == "status":
                entities.sort(key=lambda e: e.status, reverse=reverse)
            elif sort_key == "assignee":
                entities.sort(key=lambda e: e.assignee or "", reverse=reverse)

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
        }
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
                    "children": list[dict],
                    "blocking": list[dict],
                    "blocked_by": list[dict],
                    "parent": list[dict]
                }
            }
        """
        logger.info("Getting link tree for markdown entity", entity_id=entity_id)

        # Get the main entity
        entity = self.read(entity_id)

        # Load all links
        links = self._load_links()

        # Initialize tree structure
        tree: dict[str, Any] = {
            "entity": {
                "id": entity.id,
                "title": entity.title,
                "state": entity.status,
            },
            "links": {
                "children": [],
                "blocking": [],
                "blocked_by": [],
                "parent": [],
            },
        }

        # Helper to get entity info
        def get_entity_info(eid: str) -> dict[str, str] | None:
            try:
                e = self.read(eid)
                return {"id": e.id, "title": e.title, "state": e.status}
            except ValueError:
                return None

        # Get outgoing links (children, blocking)
        if entity_id in links:
            for link_type, target_ids in links[entity_id].items():
                for target_id in target_ids:
                    info = get_entity_info(target_id)
                    if info:
                        if link_type == "children":
                            tree["links"]["children"].append(info)
                        elif link_type == "blocking":
                            tree["links"]["blocking"].append(info)

        # Get incoming links (blocked_by, parent)
        for source_id, link_types in links.items():
            for link_type, target_ids in link_types.items():
                if entity_id in target_ids:
                    info = get_entity_info(source_id)
                    if info:
                        # If someone links to us with "blocked by", they block us
                        if link_type == "blocked by":
                            tree["links"]["blocked_by"].append(info)
                        # If we link to someone with "blocking", they block us (inverse)
                        elif link_type == "blocking":
                            tree["links"]["blocked_by"].append(info)
                        # If someone links to us with "parent", they are our parent
                        elif link_type == "parent":
                            tree["links"]["parent"].append(info)
                        # If we link to someone with "children", they are our parent (inverse)
                        elif link_type == "children":
                            tree["links"]["parent"].append(info)

        logger.info(
            "Link tree retrieved",
            entity_id=entity_id,
            children_count=len(tree["links"]["children"]),
            blocking_count=len(tree["links"]["blocking"]),
            blocked_by_count=len(tree["links"]["blocked_by"]),
            parent_count=len(tree["links"]["parent"]),
        )
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

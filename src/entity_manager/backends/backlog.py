"""Backlog.md backend implementation using markdown files."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

from entity_manager.backend import Backend
from entity_manager.models import Entity, Link

logger = structlog.get_logger()

# Status mapping between Backlog.md and Entity Manager
STATUS_MAP_TO_ENTITY = {
    "to do": "open",
    "todo": "open",
    "in progress": "in_progress",
    "inprogress": "in_progress",
    "done": "closed",
}

STATUS_MAP_TO_BACKLOG = {
    "open": "To Do",
    "in_progress": "In Progress",
    "closed": "Done",
}


class BacklogBackend(Backend):
    """Backlog.md-based backend using markdown files in backlog/ folder."""

    def __init__(self, backlog_path: str | None = None) -> None:
        """Initialize Backlog backend.

        Args:
            backlog_path: Path to the backlog folder (defaults to ./backlog)
        """
        if backlog_path:
            self.backlog_path = Path(backlog_path)
        else:
            self.backlog_path = Path.cwd() / "backlog"

        self.tasks_dir = self.backlog_path / "tasks"

        logger.debug("Initializing Backlog backend", backlog_path=str(self.backlog_path))

        # Create directories if they don't exist
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Backlog backend initialized", backlog_path=str(self.backlog_path))

    def _map_status_to_entity(self, status: str) -> str:
        """Map Backlog.md status to Entity Manager status."""
        return STATUS_MAP_TO_ENTITY.get(status.lower().replace(" ", ""), "open")

    def _map_status_to_backlog(self, status: str) -> str:
        """Map Entity Manager status to Backlog.md status."""
        return STATUS_MAP_TO_BACKLOG.get(status.lower(), "To Do")

    def _parse_frontmatter(self, file_path: Path) -> dict[str, Any]:
        """Parse YAML frontmatter from markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            Dictionary with parsed frontmatter fields

        Raises:
            ValueError: If file doesn't exist or frontmatter is invalid
        """
        if not file_path.exists():
            raise ValueError(f"Task file not found: {file_path}")

        try:
            content = file_path.read_text()
        except OSError as e:
            raise ValueError(f"Failed to read file {file_path}: {e}") from e

        # Extract frontmatter between --- markers
        if not content.startswith("---"):
            logger.warning("No frontmatter found in file", file_path=str(file_path))
            return {}

        parts = content.split("---", 2)
        if len(parts) < 3:
            logger.warning("Invalid frontmatter format in file", file_path=str(file_path))
            return {}

        frontmatter_text = parts[1].strip()

        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            return frontmatter or {}
        except yaml.YAMLError as e:
            logger.error("Failed to parse frontmatter", file_path=str(file_path), error=str(e))
            raise ValueError(f"Failed to parse frontmatter in {file_path}: {e}") from e

    def _format_labels(self, labels: dict[str, str]) -> list[str]:
        """Format labels dict into Backlog.md label list format."""
        return [f"{k}:{v}" if v else k for k, v in labels.items()]

    def _parse_labels(self, labels_list: list[str] | None) -> dict[str, str]:
        """Parse Backlog.md label list into dict."""
        labels = {}
        if labels_list:
            for label in labels_list:
                if isinstance(label, str):
                    if ":" in label:
                        key, value = label.split(":", 1)
                        labels[key.strip()] = value.strip()
                    else:
                        labels[label.strip()] = ""
        return labels

    def _file_to_entity(self, file_path: Path) -> Entity:
        """Convert a Backlog.md task file to an Entity.

        Args:
            file_path: Path to the task markdown file

        Returns:
            Entity object
        """
        frontmatter = self._parse_frontmatter(file_path)

        # Extract ID from filename if not in frontmatter
        entity_id = frontmatter.get("id", "")
        if not entity_id:
            # Try to extract from filename
            match = re.match(r"(task-\d+)", file_path.stem)
            if match:
                entity_id = match.group(1)
            else:
                entity_id = file_path.stem

        # Extract fields with defaults
        title = frontmatter.get("title", "(No title)")
        description = frontmatter.get("description", "")
        backlog_status = frontmatter.get("status", "To Do")
        labels_list = frontmatter.get("labels", [])
        assignee = frontmatter.get("assignee")

        # Map status
        status = self._map_status_to_entity(backlog_status)

        # Parse labels
        labels = self._parse_labels(labels_list)

        # Build metadata
        metadata = {
            "file_path": str(file_path),
            "priority": frontmatter.get("priority"),
            "created": frontmatter.get("created"),
            "updated": frontmatter.get("updated"),
        }

        # Remove None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}

        entity = Entity(
            id=entity_id,
            title=title,
            description=description,
            labels=labels,
            assignee=assignee,
            status=status,
            metadata=metadata,
        )

        logger.debug("Converted file to entity", entity_id=entity_id, title=title)
        return entity

    def _get_next_id(self) -> str:
        """Get the next available task ID.

        Scans existing task files to find the highest ID number,
        then returns the next sequential ID.

        Returns:
            New task ID in format "task-<number>"
        """
        if not self.tasks_dir.exists():
            return "task-1"

        max_id = 0
        for file_path in self.tasks_dir.glob("task-*.md"):
            match = re.match(r"task-(\d+)", file_path.name)
            if match:
                task_id = int(match.group(1))
                max_id = max(max_id, task_id)

        return f"task-{max_id + 1}"

    def _generate_filename(self, entity_id: str, title: str) -> str:
        """Generate filename for task.

        Args:
            entity_id: Task ID (e.g., "task-10")
            title: Task title

        Returns:
            Filename in format "task-<id> - <title>.md"
        """
        # Sanitize title for filename
        safe_title = re.sub(r'[<>:"/\\|?*]', "", title)
        safe_title = safe_title.strip()

        # Limit length
        if len(safe_title) > 100:
            safe_title = safe_title[:97] + "..."

        return f"{entity_id} - {safe_title}.md"

    def _get_task_file_path(self, entity_id: str) -> Path:
        """Get the file path for a task by ID.

        Args:
            entity_id: Task ID

        Returns:
            Path to the task file

        Raises:
            ValueError: If task file not found
        """
        # Search for the file
        for file_path in self.tasks_dir.glob(f"{entity_id}*.md"):
            # Check if it starts with the entity ID
            if file_path.name.startswith(entity_id):
                return file_path

        raise ValueError(f"Task file not found for ID: {entity_id}")

    def _write_task_file(self, entity: Entity, file_path: Path) -> None:
        """Write entity data to Backlog.md markdown file.

        Args:
            entity: Entity to write
            file_path: Path to write the file
        """
        # Build frontmatter
        frontmatter: dict[str, Any] = {
            "id": entity.id,
            "title": entity.title,
            "description": entity.description,
            "status": self._map_status_to_backlog(entity.status),
        }

        # Add optional fields
        if entity.labels:
            frontmatter["labels"] = self._format_labels(entity.labels)
        if entity.assignee:
            frontmatter["assignee"] = entity.assignee

        # Add metadata fields
        if entity.metadata.get("priority"):
            frontmatter["priority"] = entity.metadata["priority"]

        # Preserve created timestamp if exists
        if entity.metadata.get("created"):
            frontmatter["created"] = entity.metadata["created"]

        # Add/update updated timestamp
        frontmatter["updated"] = datetime.now(tz=None).strftime("%Y-%m-%d %H:%M")

        # Get dependencies from links if we have them stored
        # Note: In a full implementation, we'd need to track dependencies separately
        # or read them from existing frontmatter

        # Write file
        frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        content = f"---\n{frontmatter_yaml}---\n"

        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically
        temp_path = file_path.with_suffix(".tmp")
        try:
            temp_path.write_text(content)
            temp_path.replace(file_path)
        except OSError as e:
            raise ValueError(f"Failed to write file {file_path}: {e}") from e

    def create(
        self,
        title: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Create a new Backlog.md task."""
        logger.info("Creating Backlog.md task", title=title, assignee=assignee)

        # Generate new ID
        entity_id = self._get_next_id()
        logger.debug("Generated new task ID", entity_id=entity_id)

        # Create entity
        entity = Entity(
            id=entity_id,
            title=title,
            description=description,
            labels=labels or {},
            assignee=assignee,
            status="open",
            metadata={"created": datetime.now(tz=None).strftime("%Y-%m-%d %H:%M")},
        )

        # Generate filename and write file
        filename = self._generate_filename(entity_id, title)
        file_path = self.tasks_dir / filename

        self._write_task_file(entity, file_path)
        logger.info("Backlog.md task created", entity_id=entity_id, file_path=str(file_path))

        # Update metadata with file path
        entity.metadata["file_path"] = str(file_path)
        return entity

    def read(self, entity_id: str) -> Entity:
        """Read a Backlog.md task by ID."""
        # Normalize ID
        if not entity_id.startswith("task-"):
            entity_id = f"task-{entity_id}"

        logger.info("Reading Backlog.md task", entity_id=entity_id)

        file_path = self._get_task_file_path(entity_id)
        entity = self._file_to_entity(file_path)

        logger.debug("Backlog.md task read successfully", entity_id=entity_id)
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
        """Update a Backlog.md task."""
        # Normalize ID
        if not entity_id.startswith("task-"):
            entity_id = f"task-{entity_id}"

        logger.info("Updating Backlog.md task", entity_id=entity_id, title=title, status=status)

        # Read existing entity
        file_path = self._get_task_file_path(entity_id)
        entity = self._file_to_entity(file_path)

        # Update fields
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

        # Write updated file
        # If title changed, we need to rename the file
        new_filename = self._generate_filename(entity_id, entity.title)
        new_file_path = self.tasks_dir / new_filename

        self._write_task_file(entity, new_file_path)

        # Remove old file if renamed
        if new_file_path != file_path and file_path.exists():
            file_path.unlink()

        logger.info("Backlog.md task updated successfully", entity_id=entity_id)
        return entity

    def delete(self, entity_ids: list[str]) -> None:
        """Delete (remove) Backlog.md task files."""
        logger.info("Deleting Backlog.md tasks", entity_ids=entity_ids, count=len(entity_ids))

        for entity_id in entity_ids:
            # Normalize ID
            normalized_id = entity_id if entity_id.startswith("task-") else f"task-{entity_id}"

            try:
                file_path = self._get_task_file_path(normalized_id)
                file_path.unlink()
                logger.debug("Deleted task file", entity_id=normalized_id, file_path=str(file_path))
            except ValueError:
                logger.warning("Task file not found for deletion", entity_id=normalized_id)

        logger.info("Backlog.md tasks deleted successfully", count=len(entity_ids))

    def list_entities(
        self,
        filters: dict[str, str] | None = None,
        sort_by: str | None = None,
        limit: int | None = None,
    ) -> list[Entity]:
        """List Backlog.md tasks."""
        logger.info("Listing Backlog.md tasks", filters=filters, sort_by=sort_by, limit=limit)

        if not self.tasks_dir.exists():
            return []

        entities = []
        for file_path in self.tasks_dir.glob("task-*.md"):
            try:
                entity = self._file_to_entity(file_path)
                entities.append(entity)
            except Exception as e:
                logger.warning("Failed to parse task file", file_path=str(file_path), error=str(e))

        # Apply filters
        if filters:
            filtered = []
            for entity in entities:
                match = True
                if "status" in filters:
                    # Map filter status to entity status
                    filter_status = self._map_status_to_entity(filters["status"])
                    if entity.status != filter_status:
                        match = False
                if "assignee" in filters:
                    if entity.assignee != filters["assignee"]:
                        match = False
                if match:
                    filtered.append(entity)
            entities = filtered

        # Sort by ID number (descending)
        entities.sort(key=lambda e: int(e.id.split("-")[1]) if "-" in e.id else 0, reverse=True)

        # Apply limit
        if limit:
            entities = entities[:limit]

        logger.info("Listed Backlog.md tasks", count=len(entities))
        return entities

    def add_link(self, source_id: str, target_ids: list[str], link_type: str) -> None:
        """Add dependencies between Backlog.md tasks."""
        # Normalize IDs
        source_normalized = source_id if source_id.startswith("task-") else f"task-{source_id}"
        target_normalized = [t if t.startswith("task-") else f"task-{t}" for t in target_ids]

        logger.info(
            "Adding dependencies to Backlog.md task",
            source_id=source_normalized,
            target_ids=target_normalized,
            link_type=link_type,
        )

        # Only support blocked_by for now (which maps to dependencies)
        if link_type != "blocked_by":
            logger.warning(
                "Unsupported link type for Backlog backend",
                link_type=link_type,
                supported_types=["blocked_by"],
            )
            raise ValueError(f"Unsupported link type: '{link_type}'. Backlog backend supports: 'blocked_by'")

        # Read source task
        file_path = self._get_task_file_path(source_normalized)
        frontmatter = self._parse_frontmatter(file_path)

        # Get existing dependencies
        dependencies = frontmatter.get("dependencies", [])
        if not isinstance(dependencies, list):
            dependencies = []

        # Add new dependencies
        for target_id in target_normalized:
            if target_id not in dependencies:
                dependencies.append(target_id)

        frontmatter["dependencies"] = dependencies

        # Write updated file
        # Reconstruct file content
        content_parts = file_path.read_text().split("---", 2)
        if len(content_parts) >= 3:
            # Preserve the body content after frontmatter
            body = content_parts[2] if len(content_parts) > 2 else ""
            frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
            new_content = f"---\n{frontmatter_yaml}---{body}"

            file_path.write_text(new_content)

        logger.info("Dependencies added successfully", source_id=source_normalized, target_ids=target_normalized)

    def remove_link(self, source_id: str, target_ids: list[str], link_type: str, recursive: bool = False) -> None:
        """Remove dependencies between Backlog.md tasks."""
        # Normalize IDs
        source_normalized = source_id if source_id.startswith("task-") else f"task-{source_id}"
        target_normalized = [t if t.startswith("task-") else f"task-{t}" for t in target_ids]

        logger.info(
            "Removing dependencies from Backlog.md task",
            source_id=source_normalized,
            target_ids=target_normalized,
            link_type=link_type,
        )

        if link_type != "blocked_by":
            raise ValueError(f"Unsupported link type: '{link_type}'. Backlog backend supports: 'blocked_by'")

        # Read source task
        file_path = self._get_task_file_path(source_normalized)
        frontmatter = self._parse_frontmatter(file_path)

        # Get existing dependencies
        dependencies = frontmatter.get("dependencies", [])
        if not isinstance(dependencies, list):
            dependencies = []

        # Remove specified dependencies
        new_dependencies = [d for d in dependencies if d not in target_normalized]

        if len(new_dependencies) != len(dependencies):
            frontmatter["dependencies"] = new_dependencies

            # Write updated file
            content_parts = file_path.read_text().split("---", 2)
            if len(content_parts) >= 3:
                body = content_parts[2] if len(content_parts) > 2 else ""
                frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
                new_content = f"---\n{frontmatter_yaml}---{body}"

                file_path.write_text(new_content)

        logger.info("Dependencies removed successfully", source_id=source_normalized, target_ids=target_normalized)

    def list_links(self, entity_id: str, link_type: str | None = None) -> list[Link]:
        """List dependencies for a Backlog.md task."""
        # Normalize ID
        normalized_id = entity_id if entity_id.startswith("task-") else f"task-{entity_id}"

        logger.debug("Listing dependencies for Backlog.md task", entity_id=normalized_id, link_type=link_type)

        # Read task
        file_path = self._get_task_file_path(normalized_id)
        frontmatter = self._parse_frontmatter(file_path)

        # Get dependencies
        dependencies = frontmatter.get("dependencies", [])
        if not isinstance(dependencies, list):
            dependencies = []

        links = []
        for dep_id in dependencies:
            # Filter by link type if specified
            if link_type is None or link_type == "blocked_by":
                links.append(Link(source_id=normalized_id, target_id=dep_id, link_type="blocked_by"))

        logger.debug("Listed dependencies", entity_id=normalized_id, count=len(links))
        return links

    def get_link_tree(self, entity_id: str) -> dict[str, Any]:
        """Get the dependency tree for a Backlog.md task.

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
        # Normalize ID
        normalized_id = entity_id if entity_id.startswith("task-") else f"task-{entity_id}"

        logger.debug("Getting dependency tree for Backlog.md task", entity_id=normalized_id)

        # Get the main entity
        entity = self.read(normalized_id)

        # Get dependencies (blocked_by)
        blocked_by = []
        for link in self.list_links(normalized_id):
            try:
                target_entity = self.read(link.target_id)
                blocked_by.append(
                    {
                        "id": target_entity.id,
                        "title": target_entity.title,
                        "state": target_entity.status,
                    }
                )
            except ValueError:
                # Target doesn't exist, skip
                pass

        # Build tree structure
        tree: dict[str, Any] = {
            "entity": {
                "id": entity.id,
                "title": entity.title,
                "state": entity.status,
            },
            "links": {
                "children": [],
                "blocking": [],
                "blocked_by": blocked_by,
                "parent": [],
            },
        }

        return tree

    def find_cycles(self) -> list[list[str]]:
        """Find cycles in the dependency graph."""
        logger.debug("Finding cycles in Backlog.md dependency graph")

        # Build adjacency list
        graph: dict[str, list[str]] = {}
        all_ids = set()

        # Collect all tasks and their dependencies
        for file_path in self.tasks_dir.glob("task-*.md"):
            try:
                frontmatter = self._parse_frontmatter(file_path)
                entity_id = frontmatter.get("id", "")
                if not entity_id:
                    match = re.match(r"(task-\d+)", file_path.stem)
                    if match:
                        entity_id = match.group(1)
                    else:
                        continue

                all_ids.add(entity_id)

                dependencies = frontmatter.get("dependencies", [])
                if isinstance(dependencies, list):
                    # Filter dependencies to only those that exist
                    valid_deps = [d for d in dependencies if d in all_ids or d.startswith("task-")]
                    graph[entity_id] = valid_deps
            except Exception:
                continue

        # Find cycles using DFS
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for node in all_ids:
            if node not in visited:
                dfs(node)

        logger.debug("Found cycles", count=len(cycles))
        return cycles

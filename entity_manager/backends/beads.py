"""Beads backend implementation using bd CLI."""

import json
import subprocess
from typing import Any

import structlog

from entity_manager.backend import Backend
from entity_manager.models import Entity, Link

logger = structlog.get_logger()


class BeadsBackend(Backend):
    """Beads-based backend using bd CLI for issue tracking."""

    def __init__(self, project_path: str | None = None) -> None:
        """Initialize Beads backend.

        Args:
            project_path: Path to the project directory with .beads/ (defaults to current directory)
        """
        self.project_path = project_path or "."
        logger.debug("Initializing Beads backend", project_path=self.project_path)

        # Verify bd is installed and project is initialized
        try:
            result = self._run_bd_command(["info", "--json"])
            logger.info("Beads backend initialized", status=result)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to initialize Beads backend", error=str(e))
            raise ValueError(
                "bd command failed. Ensure beads is installed and project is initialized with 'bd init'"
            ) from e

    def _run_bd_command(self, args: list[str], input_data: str | None = None) -> dict[str, Any] | list[dict] | None:
        """Run a bd CLI command and return JSON output.

        Args:
            args: Command arguments (excluding 'bd')
            input_data: Optional stdin input

        Returns:
            Parsed JSON output or None if no output
        """
        cmd = ["bd"] + args
        logger.debug("Running bd command", cmd=cmd)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True,
                input=input_data,
            )

            if result.stdout.strip():
                output = json.loads(result.stdout)
                logger.debug("bd command completed", output_length=len(str(output)))
                return output
            return None
        except subprocess.CalledProcessError as e:
            logger.error("bd command failed", cmd=cmd, stderr=e.stderr, returncode=e.returncode)
            raise
        except json.JSONDecodeError as e:
            logger.error("Failed to parse bd JSON output", stdout=result.stdout, error=str(e))
            raise

    def _bead_to_entity(self, bead: dict[str, Any]) -> Entity:
        """Convert a beads issue to an Entity.

        Args:
            bead: Beads issue dictionary from JSON output

        Returns:
            Entity object
        """
        logger.debug("Converting bead to entity", bead_id=bead.get("id"))

        # Parse labels - beads uses a list of strings
        labels = {}
        for label in bead.get("labels", []):
            if ":" in label:
                key, value = label.split(":", 1)
                labels[key] = value
            else:
                labels[label] = ""

        entity = Entity(
            id=str(bead["id"]),  # Using the hash ID directly (bd-a1b2 format), converted to str
            title=bead.get("title", ""),
            description=bead.get("description", ""),
            labels=labels,
            assignee=bead.get("assignee"),
            status=bead.get("status", "open"),
            metadata={
                "type": bead.get("type"),
                "priority": bead.get("priority"),
                "created_at": bead.get("created_at"),
                "updated_at": bead.get("updated_at"),
                "notes": bead.get("notes"),
                "design": bead.get("design"),
                "acceptance_criteria": bead.get("acceptance_criteria"),
            },
        )
        logger.debug("Converted bead to entity", entity_id=entity.id, title=entity.title)
        return entity

    def _entity_id_to_bead_id(self, entity_id: str) -> str:
        """Convert entity ID to beads ID format.

        Args:
            entity_id: Entity ID (string)

        Returns:
            Beads ID string (bd-xxxx format)
        """
        # If already in beads format, return as-is
        if entity_id.startswith("bd-"):
            return entity_id

        # Otherwise, assume it's a bead hash ID without the bd- prefix
        return f"bd-{entity_id}"

    def create(
        self,
        title: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Create a new beads issue."""
        logger.info("Creating beads issue", title=title, assignee=assignee)

        args = ["create", title, "--json"]

        if description:
            args.extend(["-d", description])

        # Labels in beads are strings, formatted as key:value or just key
        if labels:
            label_list = [f"{k}:{v}" if v else k for k, v in labels.items()]
            for label in label_list:
                args.extend(["-l", label])

        if assignee:
            args.extend(["-a", assignee])

        result = self._run_bd_command(args)
        if isinstance(result, dict):
            entity = self._bead_to_entity(result)
            logger.info("Beads issue created", entity_id=entity.id)
            return entity
        raise ValueError("Unexpected response from bd create command")

    def read(self, entity_id: str) -> Entity:
        """Read a beads issue by ID."""
        bead_id = self._entity_id_to_bead_id(entity_id)
        logger.info("Reading beads issue", entity_id=bead_id)

        result = self._run_bd_command(["show", bead_id, "--json"])
        if isinstance(result, dict):
            entity = self._bead_to_entity(result)
            logger.debug("Beads issue read successfully", entity_id=bead_id)
            return entity
        raise ValueError("Unexpected response from bd show command")

    def update(
        self,
        entity_id: str,
        title: str | None = None,
        description: str | None = None,
        labels: dict[str, str] | None = None,
        status: str | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Update a beads issue."""
        bead_id = self._entity_id_to_bead_id(entity_id)
        logger.info("Updating beads issue", entity_id=bead_id, title=title, status=status, assignee=assignee)

        args = ["update", bead_id, "--json"]

        if title:
            args.extend(["--title", title])
        if description is not None:
            args.extend(["--description", description])
        if status:
            args.extend(["--status", status])
        if assignee:
            args.extend(["--assignee", assignee])

        # Update labels separately using label commands
        if labels is not None:
            # First, get current issue to see existing labels
            current = self.read(entity_id)

            # Remove old labels
            for old_label in current.labels:
                old_label_str = f"{old_label}:{current.labels[old_label]}" if current.labels[old_label] else old_label
                self._run_bd_command(["label", "remove", bead_id, old_label_str])

            # Add new labels
            for key, value in labels.items():
                new_label = f"{key}:{value}" if value else key
                self._run_bd_command(["label", "add", bead_id, new_label])

        self._run_bd_command(args)

        # Read back the updated entity
        entity = self.read(entity_id)
        logger.info("Beads issue updated successfully", entity_id=bead_id)
        return entity

    def delete(self, entity_ids: list[str]) -> None:
        """Delete (close) beads issues."""
        logger.info("Deleting (closing) beads issues", entity_ids=entity_ids, count=len(entity_ids))

        for entity_id in entity_ids:
            bead_id = self._entity_id_to_bead_id(entity_id)
            self._run_bd_command(["close", bead_id, "--reason", "Deleted via entity manager", "--json"])

        logger.info("Beads issues deleted successfully", count=len(entity_ids))

    def list_entities(
        self,
        filters: dict[str, str] | None = None,
        sort_by: str | None = None,
        limit: int | None = None,
    ) -> list[Entity]:
        """List beads issues."""
        logger.info("Listing beads issues", filters=filters, sort_by=sort_by, limit=limit)

        args = ["list", "--json"]

        if filters:
            if "status" in filters:
                args.extend(["--status", filters["status"]])
            if "assignee" in filters:
                args.extend(["--assignee", filters["assignee"]])
            if "type" in filters:
                args.extend(["--type", filters["type"]])
            if "priority" in filters:
                args.extend(["--priority", filters["priority"]])

        result = self._run_bd_command(args)

        if isinstance(result, list):
            entities = [self._bead_to_entity(bead) for bead in result]

            # Apply limit if specified
            if limit:
                entities = entities[:limit]

            logger.info("Listed beads issues", count=len(entities))
            return entities

        return []

    def add_link(self, source_id: str, target_ids: list[str], link_type: str) -> None:
        """Add dependencies between beads issues."""
        source_bead_id = self._entity_id_to_bead_id(source_id)
        logger.info(
            "Adding dependencies to beads issue", source_id=source_bead_id, target_ids=target_ids, link_type=link_type
        )

        # Map entity manager link types to beads dependency types
        # beads supports: blocks, related, parent-child, discovered-from
        beads_type = link_type
        if link_type == "relates_to":
            beads_type = "related"

        for target_id in target_ids:
            target_bead_id = self._entity_id_to_bead_id(target_id)
            self._run_bd_command(["dep", "add", source_bead_id, target_bead_id, "--type", beads_type, "--json"])

        logger.info("Dependencies added successfully", source_id=source_bead_id, target_ids=target_ids)

    def remove_link(self, source_id: str, target_ids: list[str], link_type: str, recursive: bool = False) -> None:
        """Remove dependencies between beads issues."""
        source_bead_id = self._entity_id_to_bead_id(source_id)
        logger.info(
            "Removing dependencies from beads issue",
            source_id=source_bead_id,
            target_ids=target_ids,
            link_type=link_type,
        )

        beads_type = link_type
        if link_type == "relates_to":
            beads_type = "related"

        for target_id in target_ids:
            target_bead_id = self._entity_id_to_bead_id(target_id)
            self._run_bd_command(["dep", "remove", source_bead_id, target_bead_id, "--type", beads_type, "--json"])

        logger.info("Dependencies removed successfully", source_id=source_bead_id, target_ids=target_ids)

    def list_links(self, entity_id: str, link_type: str | None = None) -> list[Link]:
        """List dependencies for a beads issue."""
        bead_id = self._entity_id_to_bead_id(entity_id)
        logger.debug("Listing dependencies for beads issue", entity_id=bead_id, link_type=link_type)

        # Get the issue details which includes dependencies
        result = self._run_bd_command(["show", bead_id, "--json"])

        links = []
        if isinstance(result, dict):
            dependencies = result.get("dependencies", [])
            for dep in dependencies:
                # Parse dependency information
                dep_type = dep.get("type", "related")
                target_id = dep.get("target_id")

                if target_id:
                    # Filter by link type if specified
                    if link_type is None or dep_type == link_type:
                        links.append(Link(source_id=bead_id, target_id=target_id, link_type=dep_type))

        logger.debug("Listed dependencies", entity_id=bead_id, count=len(links))
        return links

    def get_link_tree(self, entity_id: str) -> dict[str, Any]:
        """Get the dependency tree for a beads issue.

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
        bead_id = self._entity_id_to_bead_id(entity_id)
        logger.debug("Getting dependency tree for beads issue", entity_id=bead_id)

        # Get the issue details
        issue = self.read(entity_id)

        # Use bd dep tree command
        result = self._run_bd_command(["dep", "tree", bead_id, "--json"])

        # Transform beads tree format to our standard format
        tree: dict[str, Any] = {
            "entity": {
                "id": issue.id,
                "title": issue.title,
                "state": issue.status,
            },
            "links": {
                "children": [],
                "blocking": [],
                "blocked_by": [],
                "parent": [],
            },
        }

        if isinstance(result, dict):
            # Map beads tree structure to our structure
            # Beads may return different formats, so handle gracefully
            tree["links"]["children"] = result.get("children", [])
            tree["links"]["blocking"] = result.get("blocking", [])
            tree["links"]["blocked_by"] = result.get("blocked_by", [])
            # Convert parent from single object to list if present
            parent = result.get("parent")
            if parent:
                tree["links"]["parent"] = [parent] if isinstance(parent, dict) else parent

        return tree

    def find_cycles(self) -> list[list[str]]:
        """Find cycles in the dependency graph."""
        logger.debug("Finding cycles in beads dependency graph")

        result = self._run_bd_command(["dep", "cycles", "--json"])

        if isinstance(result, list):
            return result

        return []

    def get_config(self, key: str) -> str | None:
        """Get beads configuration value."""
        logger.debug("Getting beads config value", key=key)

        try:
            result = self._run_bd_command(["config", "get", key, "--json"])
            if isinstance(result, dict):
                return result.get("value")
        except subprocess.CalledProcessError:
            # Config key doesn't exist
            return None

        return None

    def set_config(self, key: str, value: str) -> None:
        """Set beads configuration value."""
        logger.debug("Setting beads config value", key=key, value=value)
        self._run_bd_command(["config", "set", key, value, "--json"])

    def unset_config(self, key: str) -> None:
        """Unset beads configuration value."""
        logger.debug("Unsetting beads config value", key=key)
        self._run_bd_command(["config", "unset", key, "--json"])

    def list_config(self) -> dict[str, str]:
        """List all beads configuration."""
        logger.debug("Listing all beads config values")

        result = self._run_bd_command(["config", "list", "--json"])

        if isinstance(result, dict):
            return result

        return {}

    def sync(self) -> None:
        """Sync beads database (useful to call at end of operations)."""
        logger.info("Syncing beads database")
        self._run_bd_command(["sync"])
        logger.info("Beads database synced successfully")

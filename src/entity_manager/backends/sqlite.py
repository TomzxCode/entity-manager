"""SQLite backend implementation for entity management."""

import json
import sqlite3
from typing import Any

import structlog

from entity_manager.backend import Backend
from entity_manager.models import Entity, Link

logger = structlog.get_logger()


class SQLiteBackend(Backend):
    """SQLite-based backend for local entity storage."""

    def __init__(self, db_path: str | None = None) -> None:
        """Initialize SQLite backend.

        Args:
            db_path: Path to the SQLite database file (defaults to .em.db in current directory)
        """
        self.db_path = db_path or ".em.db"
        logger.debug("Initializing SQLite backend", db_path=self.db_path)

        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        cursor = self._conn.cursor()

        # Entities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                labels TEXT,
                assignee TEXT,
                status TEXT DEFAULT 'open',
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Links table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS links (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                link_type TEXT NOT NULL DEFAULT 'relates_to',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source_id, target_id, link_type),
                FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_status
            ON entities(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_assignee
            ON entities(assignee)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_links_target
            ON links(target_id, link_type)
        """)

        self._conn.commit()
        logger.debug("Database schema initialized")

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        """Convert a database row to an Entity.

        Args:
            row: SQLite row object

        Returns:
            Entity object
        """
        labels = {}
        if row["labels"]:
            labels = json.loads(row["labels"])

        metadata = {}
        if row["metadata"]:
            metadata = json.loads(row["metadata"])

        return Entity(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            labels=labels,
            assignee=row["assignee"],
            status=row["status"] or "open",
            metadata=metadata,
        )

    def create(
        self,
        title: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Create a new entity."""
        import uuid

        cursor = self._conn.cursor()

        entity_id = f"sql-{uuid.uuid4().hex[:8]}"
        labels_json = json.dumps(labels) if labels else None
        metadata_json = json.dumps({"backend": "sqlite"})

        try:
            cursor.execute(
                """
                INSERT INTO entities (id, title, description, labels, assignee, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (entity_id, title, description, labels_json, assignee, metadata_json),
            )
            self._conn.commit()

            logger.info("Entity created", entity_id=entity_id, title=title)
            return self.read(entity_id)
        except sqlite3.IntegrityError:
            logger.error("Failed to create entity", entity_id=entity_id, error="Duplicate ID")
            raise ValueError(f"Entity with ID {entity_id} already exists")

    def read(self, entity_id: str) -> Entity:
        """Read an entity by ID."""
        cursor = self._conn.cursor()

        cursor.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
        row = cursor.fetchone()

        if not row:
            logger.error("Entity not found", entity_id=entity_id)
            raise ValueError(f"Entity {entity_id} not found")

        return self._row_to_entity(row)

    def update(
        self,
        entity_id: str,
        title: str | None = None,
        description: str | None = None,
        labels: dict[str, str] | None = None,
        status: str | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Update an entity."""
        cursor = self._conn.cursor()

        # Check if entity exists
        cursor.execute("SELECT id FROM entities WHERE id = ?", (entity_id,))
        if not cursor.fetchone():
            logger.error("Entity not found", entity_id=entity_id)
            raise ValueError(f"Entity {entity_id} not found")

        # Build update query dynamically based on provided parameters
        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)

        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if labels is not None:
            updates.append("labels = ?")
            params.append(json.dumps(labels))

        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if assignee is not None:
            updates.append("assignee = ?")
            params.append(assignee)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(entity_id)

            query = f"UPDATE entities SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            self._conn.commit()

            logger.info("Entity updated", entity_id=entity_id)

        return self.read(entity_id)

    def delete(self, entity_ids: list[str]) -> None:
        """Delete one or more entities."""
        cursor = self._conn.cursor()

        if not entity_ids:
            return

        placeholders = ",".join("?" * len(entity_ids))
        cursor.execute(f"DELETE FROM entities WHERE id IN ({placeholders})", entity_ids)

        deleted_count = cursor.rowcount
        self._conn.commit()

        logger.info("Entities deleted", count=deleted_count, entity_ids=entity_ids)

    def list_entities(
        self,
        filters: dict[str, str] | None = None,
        sort_by: str | None = None,
        limit: int | None = None,
    ) -> list[Entity]:
        """List entities with optional filtering, sorting, and limiting."""
        cursor = self._conn.cursor()

        query = "SELECT * FROM entities WHERE 1=1"
        params = []

        if filters:
            for key, value in filters.items():
                if key == "status":
                    query += " AND status = ?"
                    params.append(value)
                elif key == "assignee":
                    query += " AND assignee = ?"
                    params.append(value)
                elif key == "title":
                    query += " AND title LIKE ?"
                    params.append(f"%{value}%")
                else:
                    # Filter by label (JSON contains)
                    query += " AND labels LIKE ?"
                    params.append(f"%{key}%{value}%")

        if sort_by:
            # Validate sort_by to prevent SQL injection
            allowed_columns = {"id", "title", "status", "assignee", "created_at", "updated_at"}
            if sort_by in allowed_columns:
                query += f" ORDER BY {sort_by}"
            else:
                logger.warning("Invalid sort column", sort_by=sort_by)

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [self._row_to_entity(row) for row in rows]

    def add_link(self, source_id: str, target_ids: list[str], link_type: str) -> None:
        """Add links from source entity to target entities."""
        cursor = self._conn.cursor()

        # Verify source and target entities exist
        all_ids = [source_id] + target_ids
        placeholders = ",".join("?" * len(all_ids))
        cursor.execute(f"SELECT id FROM entities WHERE id IN ({placeholders})", all_ids)

        found_ids = {row["id"] for row in cursor.fetchall()}
        missing_ids = set(all_ids) - found_ids

        if missing_ids:
            logger.error("Entities not found", missing_ids=list(missing_ids))
            raise ValueError(f"Entities not found: {missing_ids}")

        # Add links
        for target_id in target_ids:
            try:
                cursor.execute(
                    "INSERT INTO links (source_id, target_id, link_type) VALUES (?, ?, ?)",
                    (source_id, target_id, link_type),
                )
            except sqlite3.IntegrityError:
                # Link already exists, skip
                logger.debug("Link already exists", source_id=source_id, target_id=target_id, link_type=link_type)

        self._conn.commit()
        logger.info("Links added", source_id=source_id, target_ids=target_ids, link_type=link_type)

    def remove_link(self, source_id: str, target_ids: list[str], link_type: str, recursive: bool = False) -> None:
        """Remove links from source entity to target entities."""
        cursor = self._conn.cursor()

        if recursive:
            # Remove all transitive links
            for target_id in target_ids:
                cursor.execute(
                    "DELETE FROM links WHERE source_id = ? AND link_type = ?",
                    (target_id, link_type),
                )
                logger.debug("Removed recursive link", source_id=source_id, target_id=target_id, link_type=link_type)

        placeholders = ",".join("?" * len(target_ids))
        cursor.execute(
            f"DELETE FROM links WHERE source_id = ? AND target_id IN ({placeholders}) AND link_type = ?",
            [source_id] + target_ids + [link_type],
        )

        self._conn.commit()
        logger.info(
            "Links removed", source_id=source_id, target_ids=target_ids, link_type=link_type, recursive=recursive
        )

    def list_links(self, entity_id: str, link_type: str | None = None) -> list[Link]:
        """List all links for an entity."""
        cursor = self._conn.cursor()

        if link_type:
            cursor.execute(
                "SELECT source_id, target_id, link_type FROM links WHERE source_id = ? AND link_type = ?",
                (entity_id, link_type),
            )
        else:
            cursor.execute(
                "SELECT source_id, target_id, link_type FROM links WHERE source_id = ?",
                (entity_id,),
            )

        return [
            Link(source_id=row["source_id"], target_id=row["target_id"], link_type=row["link_type"])
            for row in cursor.fetchall()
        ]

    def get_link_tree(self, entity_id: str) -> dict[str, Any]:
        """Get the link tree for an entity."""
        cursor = self._conn.cursor()

        # Get the entity
        entity = self.read(entity_id)

        # Standard link types
        link_types = {
            "children": "child",
            "blocking": "blocking",
            "parent": "parent",
            "blocked_by": "blocked_by",
        }

        links: dict[str, Any] = {key: [] for key in link_types}

        # Get outgoing links
        cursor.execute("SELECT target_id, link_type FROM links WHERE source_id = ?", (entity_id,))
        for row in cursor.fetchall():
            target = self.read(row["target_id"])
            link_info = {"id": target.id, "title": target.title, "state": target.status}

            # Map link types to standard categories
            if row["link_type"] in ("child", "children"):
                links["children"].append(link_info)
            elif row["link_type"] == "blocking":
                links["blocking"].append(link_info)
            elif row["link_type"] == "parent":
                links["parent"].append(link_info)

        # Get incoming links for blocked_by
        cursor.execute(
            "SELECT source_id FROM links WHERE target_id = ? AND link_type = ?",
            (entity_id, "blocking"),
        )
        for row in cursor.fetchall():
            source = self.read(row["source_id"])
            links["blocked_by"].append({"id": source.id, "title": source.title, "state": source.status})

        return {
            "entity": {"id": entity.id, "title": entity.title, "state": entity.status},
            "links": links,
        }

    def find_cycles(self) -> list[list[str]]:
        """Find and return all cycles in the link graph."""
        cursor = self._conn.cursor()

        # Get all links
        cursor.execute("SELECT source_id, target_id FROM links")
        all_links = [(row["source_id"], row["target_id"]) for row in cursor.fetchall()]

        # Build adjacency list
        graph: dict[str, list[str]] = {}
        for source, target in all_links:
            if source not in graph:
                graph[source] = []
            graph[source].append(target)

        # Find cycles using DFS
        visited: set[str] = set()
        cycles: list[list[str]] = []

        def dfs(node: str, path: list[str]) -> None:
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            path.append(node)

            if node in graph:
                for neighbor in graph[node]:
                    dfs(neighbor, path.copy())

        for node in graph:
            if node not in visited:
                dfs(node, [])

        # Remove duplicate cycles (same cycle in different order or starting point)
        unique_cycles: list[list[str]] = []
        seen_cycles: set[tuple[str, ...]] = set()

        for cycle in cycles:
            # Normalize cycle by starting from smallest ID and treating as circular
            min_idx = cycle.index(min(cycle))
            normalized = tuple(cycle[min_idx:-1] + cycle[:min_idx])
            if normalized not in seen_cycles:
                seen_cycles.add(normalized)
                unique_cycles.append(list(normalized))

        logger.info("Cycles found", count=len(unique_cycles))
        return unique_cycles

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
        self._conn = None
        logger.debug("Database connection closed")

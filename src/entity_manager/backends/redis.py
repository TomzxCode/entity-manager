"""Redis backend implementation for entity management."""

import json
import uuid
from typing import Any

import structlog
from redis import Redis, RedisError

from entity_manager.backend import Backend
from entity_manager.models import Entity, Link

logger = structlog.get_logger()


class RedisBackend(Backend):
    """Redis-based backend for fast, distributed entity storage."""

    _ENTITY_PREFIX = "entity:"
    _LINK_PREFIX = "link:"
    _INDEX_KEY = "em:entities"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        decode_responses: bool = True,
    ) -> None:
        """Initialize Redis backend.

        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password (optional)
            decode_responses: Whether to decode responses to strings
        """
        self._redis = Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses,
        )
        logger.debug("Initializing Redis backend", host=host, port=port, db=db)

        # Test connection
        try:
            self._redis.ping()
            logger.info("Connected to Redis", host=host, port=port)
        except RedisError as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise

    def _entity_key(self, entity_id: str) -> str:
        """Get the Redis key for an entity."""
        return f"{self._ENTITY_PREFIX}{entity_id}"

    def _link_key(self, source_id: str, target_id: str, link_type: str) -> str:
        """Get the Redis key for a link."""
        return f"{self._LINK_PREFIX}{source_id}:{target_id}:{link_type}"

    def _entity_from_hash(self, entity_id: str, data: dict[str, str]) -> Entity:
        """Convert a Redis hash to an Entity.

        Args:
            entity_id: Entity ID
            data: Redis hash data

        Returns:
            Entity object
        """
        properties: dict[str, Any] = {
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "status": data.get("status", "open"),
        }

        # Parse labels from JSON and merge into properties
        if data.get("labels"):
            try:
                labels = json.loads(data["labels"])
                if isinstance(labels, dict):
                    properties.update(labels)
            except json.JSONDecodeError:
                logger.warning("Invalid labels JSON", entity_id=entity_id, labels=data.get("labels"))

        # Add assignee if present
        if data.get("assignee"):
            properties["assignee"] = data.get("assignee")

        # Parse metadata
        metadata: dict[str, Any] = {}
        if data.get("metadata"):
            try:
                metadata = json.loads(data["metadata"])
            except json.JSONDecodeError:
                logger.warning("Invalid metadata JSON", entity_id=entity_id, metadata=data.get("metadata"))

        return Entity(
            id=entity_id,
            type=data.get("type", "default"),
            properties=properties,
            metadata=metadata,
        )

    def create(
        self,
        type: str = "default",
        properties: dict[str, Any] | None = None,
    ) -> Entity:
        """Create a new entity."""
        properties = properties or {}
        title = properties.get("title", "")
        description = properties.get("description", "")
        assignee = properties.get("assignee")

        entity_id = f"r-{uuid.uuid4().hex[:8]}"

        # Extract labels from properties (excluding standard fields)
        labels = {k: v for k, v in properties.items() if k not in ("title", "description", "assignee", "status")}

        data = {
            "id": entity_id,
            "type": type,
            "title": title,
            "description": description,
            "labels": json.dumps(labels) if labels else "",
            "assignee": assignee or "",
            "status": properties.get("status", "open"),
            "metadata": json.dumps({"backend": "redis"}),
        }

        key = self._entity_key(entity_id)
        self._redis.hset(key, mapping=data)
        self._redis.sadd(self._INDEX_KEY, entity_id)

        logger.info("Entity created", entity_id=entity_id, title=title)
        return self.read(entity_id)

    def read(self, entity_id: str) -> Entity:
        """Read an entity by ID."""
        key = self._entity_key(entity_id)
        data = self._redis.hgetall(key)

        if not data:
            logger.error("Entity not found", entity_id=entity_id)
            raise ValueError(f"Entity {entity_id} not found")

        return self._entity_from_hash(entity_id, data)

    def update(
        self,
        entity_id: str,
        type: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> Entity:
        """Update an entity."""
        properties = properties or {}
        key = self._entity_key(entity_id)

        # Check if entity exists
        if not self._redis.exists(key):
            logger.error("Entity not found", entity_id=entity_id)
            raise ValueError(f"Entity {entity_id} not found")

        # Build update data
        updates = {}
        if type is not None:
            updates["type"] = type

        if "title" in properties:
            updates["title"] = properties["title"]
        if "description" in properties:
            updates["description"] = properties["description"]
        if "status" in properties:
            updates["status"] = properties["status"]
        if "assignee" in properties:
            updates["assignee"] = properties["assignee"]

        # Extract labels from properties (excluding standard fields)
        labels = {k: v for k, v in properties.items() if k not in ("title", "description", "assignee", "status")}
        if labels:
            updates["labels"] = json.dumps(labels)

        if updates:
            self._redis.hset(key, mapping=updates)
            logger.info("Entity updated", entity_id=entity_id, updates=list(updates.keys()))

        return self.read(entity_id)

    def delete(self, entity_ids: list[str]) -> None:
        """Delete one or more entities."""
        if not entity_ids:
            return

        pipe = self._redis.pipeline()

        # Delete entities
        keys = [self._entity_key(eid) for eid in entity_ids]
        pipe.delete(*keys)

        # Remove from index
        pipe.srem(self._INDEX_KEY, *entity_ids)

        # Delete all links associated with these entities
        for entity_id in entity_ids:
            # Find and delete all links where this entity is source
            for link_key in self._redis.scan_iter(match=f"{self._LINK_PREFIX}{entity_id}:*"):
                pipe.delete(link_key)

            # Find and delete all links where this entity is target
            pattern = f"{self._LINK_PREFIX}*:{entity_id}:*"
            for link_key in self._redis.scan_iter(match=pattern):
                pipe.delete(link_key)

        pipe.execute()
        logger.info("Entities deleted", count=len(entity_ids), entity_ids=entity_ids)

    def list_entities(
        self,
        filters: dict[str, str] | None = None,
        sort_by: str | None = None,
        limit: int | None = None,
    ) -> list[Entity]:
        """List entities with optional filtering, sorting, and limiting."""
        # Get all entity IDs from index
        entity_ids = list(self._redis.smembers(self._INDEX_KEY))

        if not entity_ids:
            return []

        # Fetch all entities
        entities = []
        for entity_id in entity_ids:
            try:
                entity = self.read(entity_id)
                entities.append(entity)
            except ValueError:
                # Entity may have been deleted but not removed from index
                continue

        # Apply filters
        if filters:
            filtered = []
            for entity in entities:
                match = True
                for key, value in filters.items():
                    if key == "status":
                        if entity.properties.get("status") != value:
                            match = False
                            break
                    elif key == "assignee":
                        if entity.properties.get("assignee") != value:
                            match = False
                            break
                    elif key == "title":
                        if value.lower() not in str(entity.properties.get("title", "")).lower():
                            match = False
                            break
                    else:
                        # Filter by property
                        if entity.properties.get(key) != value:
                            match = False
                            break
                if match:
                    filtered.append(entity)
            entities = filtered

        # Apply sorting
        if sort_by:
            reverse = False
            if sort_by.startswith("-"):
                sort_by = sort_by[1:]
                reverse = True

            if sort_by == "id":
                entities.sort(key=lambda e: e.id, reverse=reverse)
            elif sort_by == "title":
                entities.sort(key=lambda e: str(e.properties.get("title", "")).lower(), reverse=reverse)
            elif sort_by == "status":
                entities.sort(key=lambda e: e.properties.get("status", ""), reverse=reverse)
            elif sort_by == "assignee":
                entities.sort(key=lambda e: e.properties.get("assignee") or "", reverse=reverse)

        # Apply limit
        if limit:
            entities = entities[:limit]

        return entities

    def add_link(self, source_id: str, target_ids: list[str], link_type: str) -> None:
        """Add links from source entity to target entities."""
        # Verify entities exist
        try:
            self.read(source_id)
            for target_id in target_ids:
                self.read(target_id)
        except ValueError as e:
            logger.error("Entity not found for link", error=str(e))
            raise

        pipe = self._redis.pipeline()

        for target_id in target_ids:
            link_key = self._link_key(source_id, target_id, link_type)
            pipe.set(link_key, 1)  # Use set to allow duplicate detection

        pipe.execute()
        logger.info("Links added", source_id=source_id, target_ids=target_ids, link_type=link_type)

    def remove_link(self, source_id: str, target_ids: list[str], link_type: str, recursive: bool = False) -> None:
        """Remove links from source entity to target entities."""
        pipe = self._redis.pipeline()

        if recursive:
            # Remove all transitive links
            for target_id in target_ids:
                pattern = f"{self._LINK_PREFIX}{target_id}:*:{link_type}"
                for link_key in self._redis.scan_iter(match=pattern):
                    pipe.delete(link_key)
                logger.debug("Removed recursive links", source_id=source_id, target_id=target_id, link_type=link_type)

        # Remove direct links
        for target_id in target_ids:
            link_key = self._link_key(source_id, target_id, link_type)
            pipe.delete(link_key)

        pipe.execute()
        logger.info(
            "Links removed", source_id=source_id, target_ids=target_ids, link_type=link_type, recursive=recursive
        )

    def list_links(self, entity_id: str, link_type: str | None = None) -> list[Link]:
        """List all links for an entity."""
        links = []

        if link_type:
            pattern = f"{self._LINK_PREFIX}{entity_id}:*:{link_type}"
        else:
            pattern = f"{self._LINK_PREFIX}{entity_id}:*"

        for link_key in self._redis.scan_iter(match=pattern):
            # Parse key: link:source:target:type
            parts = link_key.split(":")
            if len(parts) >= 4:
                source = parts[1]
                target = parts[2]
                l_type = parts[3]
                links.append(Link(source_id=source, target_id=target, link_type=l_type))

        return links

    def get_link_tree(self, entity_id: str) -> dict[str, Any]:
        """Get the link tree for an entity."""
        entity = self.read(entity_id)

        # Standard link types
        links: dict[str, Any] = {
            "children": [],
            "blocking": [],
            "blocked_by": [],
            "parent": [],
        }

        # Get all links
        all_links = self.list_links(entity_id)

        # Get incoming links for blocked_by
        # We need to scan all links to find ones pointing to this entity
        for link_key in self._redis.scan_iter(match=f"{self._LINK_PREFIX}*:{entity_id}:blocking"):
            parts = link_key.split(":")
            if len(parts) >= 4:
                source_id = parts[1]
                try:
                    source = self.read(source_id)
                    links["blocked_by"].append(
                        {
                            "id": source.id,
                            "title": source.properties.get("title", ""),
                            "state": source.properties.get("status", ""),
                        }
                    )
                except ValueError:
                    pass

        # Process outgoing links
        for link in all_links:
            try:
                target = self.read(link.target_id)
                link_info = {
                    "id": target.id,
                    "title": target.properties.get("title", ""),
                    "state": target.properties.get("status", ""),
                }

                # Map link types to standard categories
                if link.link_type in ("child", "children"):
                    links["children"].append(link_info)
                elif link.link_type == "blocking":
                    links["blocking"].append(link_info)
                elif link.link_type == "parent":
                    links["parent"].append(link_info)
            except ValueError:
                pass

        return {
            "entity": {
                "id": entity.id,
                "title": entity.properties.get("title", ""),
                "state": entity.properties.get("status", ""),
            },
            "links": links,
        }

    def find_cycles(self) -> list[list[str]]:
        """Find and return all cycles in the link graph."""
        # Build adjacency list
        graph: dict[str, list[str]] = {}
        all_entity_ids = set()

        for link_key in self._redis.scan_iter(match=f"{self._LINK_PREFIX}*"):
            parts = link_key.split(":")
            if len(parts) >= 4:
                source = parts[1]
                target = parts[2]
                all_entity_ids.add(source)
                all_entity_ids.add(target)

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

        # Remove duplicate cycles
        unique_cycles: list[list[str]] = []
        seen_cycles: set[tuple[str, ...]] = set()

        for cycle in cycles:
            min_idx = cycle.index(min(cycle))
            normalized = tuple(cycle[min_idx:-1] + cycle[:min_idx])
            if normalized not in seen_cycles:
                seen_cycles.add(normalized)
                unique_cycles.append(list(normalized))

        logger.info("Cycles found", count=len(unique_cycles))
        return unique_cycles

    def close(self) -> None:
        """Close the Redis connection."""
        self._redis.close()
        logger.debug("Redis connection closed")

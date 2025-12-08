"""Notion backend implementation using notion-client."""

from typing import Any

import structlog
from notion_client import Client

from entity_manager.backend import Backend
from entity_manager.models import Entity, Link

logger = structlog.get_logger()


class NotionBackend(Backend):
    """Notion-based backend using database entries as entities."""

    def __init__(self, token: str, database_id: str) -> None:
        """Initialize Notion backend.

        Args:
            token: Notion integration token
            database_id: Notion database ID to use for entities
        """
        self.token = token
        self.database_id = database_id

        if not self.token:
            raise ValueError("Notion token required")
        if not self.database_id:
            raise ValueError("Notion database_id required")

        logger.debug("Initializing Notion backend", database_id=database_id)
        self.client = Client(auth=self.token)
        logger.info("Notion backend initialized", database_id=database_id)

    def _parse_properties(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Parse Notion properties into simple values."""
        parsed = {}
        for key, value in properties.items():
            prop_type = value.get("type")

            if prop_type == "title":
                title_array = value.get("title", [])
                parsed[key] = "".join([t.get("plain_text", "") for t in title_array])
            elif prop_type == "rich_text":
                text_array = value.get("rich_text", [])
                parsed[key] = "".join([t.get("plain_text", "") for t in text_array])
            elif prop_type == "select":
                select = value.get("select")
                parsed[key] = select.get("name") if select else None
            elif prop_type == "multi_select":
                multi_select = value.get("multi_select", [])
                parsed[key] = [item.get("name") for item in multi_select]
            elif prop_type == "status":
                status = value.get("status")
                parsed[key] = status.get("name") if status else None
            elif prop_type == "people":
                people = value.get("people", [])
                parsed[key] = [person.get("name", person.get("id")) for person in people]
            elif prop_type == "relation":
                relations = value.get("relation", [])
                parsed[key] = [rel.get("id") for rel in relations]
            else:
                parsed[key] = value

        return parsed

    def _page_to_entity(self, page: dict[str, Any]) -> Entity:
        """Convert Notion page to Entity."""
        logger.debug("Converting Notion page to entity", page_id=page["id"])

        properties = self._parse_properties(page.get("properties", {}))

        # Extract common fields
        title = properties.get("Name") or properties.get("Title") or ""
        description = properties.get("Description") or ""
        status = properties.get("Status") or "open"

        # Extract labels from multi-select property
        labels = {}
        multi_select_labels = properties.get("Labels") or properties.get("Tags") or []
        if isinstance(multi_select_labels, list):
            for label in multi_select_labels:
                if isinstance(label, str):
                    if ":" in label:
                        key, value = label.split(":", 1)
                        labels[key.strip()] = value.strip()
                    else:
                        labels[label] = ""

        # Extract assignee
        assignee = None
        people = properties.get("Assignee") or []
        if isinstance(people, list) and len(people) > 0:
            assignee = people[0]

        entity = Entity(
            id=page["id"],
            title=title,
            description=description,
            labels=labels,
            assignee=assignee,
            status=status.lower() if isinstance(status, str) else "open",
            metadata={
                "url": page.get("url"),
                "created_time": page.get("created_time"),
                "last_edited_time": page.get("last_edited_time"),
                "properties": properties,
            },
        )
        logger.debug("Converted Notion page to entity", entity_id=entity.id, title=entity.title)
        return entity

    def _build_properties(
        self,
        title: str | None = None,
        description: str | None = None,
        labels: dict[str, str] | None = None,
        status: str | None = None,
        assignee: str | None = None,
    ) -> dict[str, Any]:
        """Build Notion properties object."""
        properties: dict[str, Any] = {}

        if title is not None:
            properties["Name"] = {"title": [{"text": {"content": title}}]}

        if description is not None:
            properties["Description"] = {"rich_text": [{"text": {"content": description}}]}

        if status is not None:
            properties["Status"] = {"status": {"name": status.title()}}

        if labels is not None:
            label_names = [f"{k}:{v}" if v else k for k, v in labels.items()]
            properties["Labels"] = {"multi_select": [{"name": name} for name in label_names]}

        if assignee is not None:
            # Note: In Notion, people properties require user IDs, not names
            # This is a simplified implementation - in production you'd need to resolve names to IDs
            properties["Assignee"] = {"people": [{"id": assignee}]} if assignee else {"people": []}

        return properties

    def create(
        self,
        title: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Create a new Notion page in the database."""
        logger.info("Creating Notion page", title=title, assignee=assignee)

        properties = self._build_properties(
            title=title, description=description, labels=labels, status="open", assignee=assignee
        )

        response = self.client.pages.create(parent={"database_id": self.database_id}, properties=properties)

        entity = self._page_to_entity(response)
        logger.info("Notion page created", entity_id=entity.id)
        return entity

    def read(self, entity_id: str) -> Entity:
        """Read a Notion page by ID."""
        logger.info("Reading Notion page", entity_id=entity_id)
        page = self.client.pages.retrieve(page_id=entity_id)
        entity = self._page_to_entity(page)
        logger.debug("Notion page read successfully", entity_id=entity_id)
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
        """Update a Notion page."""
        logger.info("Updating Notion page", entity_id=entity_id, title=title, status=status, assignee=assignee)

        properties = self._build_properties(
            title=title, description=description, labels=labels, status=status, assignee=assignee
        )

        self.client.pages.update(page_id=entity_id, properties=properties)

        # Retrieve updated page
        entity = self.read(entity_id)
        logger.info("Notion page updated successfully", entity_id=entity_id)
        return entity

    def delete(self, entity_ids: list[str]) -> None:
        """Delete (archive) Notion pages."""
        logger.info("Deleting (archiving) Notion pages", entity_ids=entity_ids, count=len(entity_ids))
        for entity_id in entity_ids:
            self.client.pages.update(page_id=entity_id, archived=True)
        logger.info("Notion pages deleted successfully", count=len(entity_ids))

    def list_entities(
        self,
        filters: dict[str, str] | None = None,
        sort_by: str | None = None,
        limit: int | None = None,
    ) -> list[Entity]:
        """List Notion pages in the database."""
        logger.info("Listing Notion pages", filters=filters, sort_by=sort_by, limit=limit)

        query_params: dict[str, Any] = {"database_id": self.database_id}

        # Build filter
        if filters:
            filter_conditions = []
            if "status" in filters:
                filter_conditions.append({"property": "Status", "status": {"equals": filters["status"].title()}})

            if filter_conditions:
                if len(filter_conditions) == 1:
                    query_params["filter"] = filter_conditions[0]
                else:
                    query_params["filter"] = {"and": filter_conditions}

        # Build sorts
        if sort_by:
            query_params["sorts"] = [{"property": sort_by.title(), "direction": "descending"}]

        # Set page size
        if limit:
            query_params["page_size"] = min(limit, 100)

        response = self.client.databases.query(**query_params)

        entities = []
        for page in response.get("results", []):
            entities.append(self._page_to_entity(page))
            if limit and len(entities) >= limit:
                break

        logger.info("Listed Notion pages", count=len(entities))
        return entities

    def add_link(self, source_id: str, target_ids: list[str], link_type: str) -> None:
        """Add links using Notion's relation properties.

        Note: This implementation assumes the database has relation properties
        named 'Blocked By', 'Blocking', 'Parent', and 'Children'.
        """
        logger.info("Adding link to Notion page", source_id=source_id, target_ids=target_ids, link_type=link_type)

        # Normalize link type
        link_type = link_type.lower().strip()

        # Map link types to relation property names
        property_map = {
            "blocked by": "Blocked By",
            "blocking": "Blocking",
            "parent": "Parent",
            "children": "Children",
        }

        if link_type not in property_map:
            logger.warning(
                "Unsupported link type for Notion backend",
                link_type=link_type,
                supported_types=list(property_map.keys()),
            )
            supported_types = list(property_map.keys())
            raise ValueError(f"Unsupported link type: '{link_type}'. Notion backend supports: {supported_types}")

        property_name = property_map[link_type]

        # Get current page to retrieve existing relations
        page = self.client.pages.retrieve(page_id=source_id)
        properties = self._parse_properties(page.get("properties", {}))
        existing_relations = properties.get(property_name, [])

        # Combine existing and new relations
        all_relation_ids = set(existing_relations) if isinstance(existing_relations, list) else set()
        all_relation_ids.update(target_ids)

        # Update the relation property
        update_properties = {property_name: {"relation": [{"id": rel_id} for rel_id in all_relation_ids]}}

        self.client.pages.update(page_id=source_id, properties=update_properties)

        logger.info("Link added successfully", source_id=source_id, target_ids=target_ids, link_type=link_type)

    def remove_link(self, source_id: str, target_ids: list[str], link_type: str, recursive: bool = False) -> None:
        """Remove links from Notion relation properties.

        Args:
            source_id: Source page ID
            target_ids: List of target page IDs to remove
            link_type: Type of link to remove
            recursive: Not used for Notion backend
        """
        logger.info("Removing link from Notion page", source_id=source_id, target_ids=target_ids, link_type=link_type)

        # Normalize link type
        link_type = link_type.lower().strip()

        # Map link types to relation property names
        property_map = {
            "blocked by": "Blocked By",
            "blocking": "Blocking",
            "parent": "Parent",
            "children": "Children",
        }

        if link_type not in property_map:
            logger.warning(
                "Unsupported link type for Notion backend",
                link_type=link_type,
                supported_types=list(property_map.keys()),
            )
            supported_types = list(property_map.keys())
            raise ValueError(f"Unsupported link type: '{link_type}'. Notion backend supports: {supported_types}")

        property_name = property_map[link_type]

        # Get current page to retrieve existing relations
        page = self.client.pages.retrieve(page_id=source_id)
        properties = self._parse_properties(page.get("properties", {}))
        existing_relations = properties.get(property_name, [])

        # Remove specified relations
        if isinstance(existing_relations, list):
            remaining_relations = [rel_id for rel_id in existing_relations if rel_id not in target_ids]
        else:
            remaining_relations = []

        # Update the relation property
        update_properties = {property_name: {"relation": [{"id": rel_id} for rel_id in remaining_relations]}}

        self.client.pages.update(page_id=source_id, properties=update_properties)

        logger.info("Link removed successfully", source_id=source_id, target_ids=target_ids, link_type=link_type)

    def list_links(self, entity_id: str, link_type: str | None = None) -> list[Link]:
        """List links for a Notion page.

        Args:
            entity_id: Page ID to get links for
            link_type: Optional filter for link type (None returns all)

        Returns:
            List of Link objects
        """
        logger.debug("Listing links for Notion page", entity_id=entity_id, link_type=link_type)

        # Normalize link type if provided
        if link_type:
            link_type = link_type.lower().strip()

        # Get the page
        page = self.client.pages.retrieve(page_id=entity_id)
        properties = self._parse_properties(page.get("properties", {}))

        links: list[Link] = []

        # Map relation properties to link types
        property_map = {
            "Blocked By": "blocked by",
            "Blocking": "blocking",
            "Parent": "parent",
            "Children": "children",
        }

        for property_name, relation_type in property_map.items():
            # Skip if filtering by link type and this doesn't match
            if link_type and relation_type != link_type:
                continue

            relations = properties.get(property_name, [])
            if isinstance(relations, list):
                for target_id in relations:
                    links.append(Link(source_id=entity_id, target_id=target_id, link_type=relation_type))

        logger.debug("Retrieved Notion page links", entity_id=entity_id, count=len(links))
        return links

    def get_link_tree(self, entity_id: str) -> dict[str, Any]:
        """Get hierarchical link tree for a Notion page.

        Args:
            entity_id: Page ID to get tree for

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
        logger.info("Getting link tree for Notion page", entity_id=entity_id)

        # Get the main page
        entity = self.read(entity_id)

        # Build tree structure
        tree: dict[str, Any] = {
            "entity": {"id": entity.id, "title": entity.title, "state": entity.status},
            "links": {"children": [], "blocking": [], "blocked_by": [], "parent": []},
        }

        # Get all links
        links = self.list_links(entity_id)

        # Organize by type and fetch details for each linked entity
        for link in links:
            try:
                linked_entity = self.read(link.target_id)
                link_info = {"id": linked_entity.id, "title": linked_entity.title, "state": linked_entity.status}

                if link.link_type == "blocked by":
                    tree["links"]["blocked_by"].append(link_info)
                elif link.link_type == "blocking":
                    tree["links"]["blocking"].append(link_info)
                elif link.link_type == "parent":
                    tree["links"]["parent"].append(link_info)
                elif link.link_type == "children":
                    tree["links"]["children"].append(link_info)
            except Exception as e:
                logger.warning("Failed to fetch linked entity", target_id=link.target_id, error=str(e))

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
        """Find cycles in link graph.

        Note: This is a simplified implementation that doesn't traverse all relations.
        A full implementation would need to query all pages and build a complete graph.
        """
        logger.debug("Finding cycles in link graph")
        # This would require querying all pages and analyzing the relation graph
        # For now, return empty list as a placeholder
        return []

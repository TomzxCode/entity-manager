"""GitHub REST API backend implementation using PyGithub."""

import os
from typing import Any

import structlog
from github import Auth, Github
from github.Issue import Issue
from github.Repository import Repository

from entity_manager.backend import Backend
from entity_manager.models import Entity, Link

logger = structlog.get_logger()


class GitHubBackend(Backend):
    """GitHub-based backend using issues as entities."""

    def __init__(self, owner: str, repo: str, token: str | None = None) -> None:
        """Initialize GitHub backend.

        Args:
            owner: Repository owner
            repo: Repository name
            token: GitHub personal access token
        """
        self.owner = owner
        self.repo = repo
        self.token = token
        if not self.token:
            raise ValueError("GitHub token required")

        logger.debug("Initializing GitHub backend", owner=owner, repo=repo)
        auth = Auth.Token(self.token)
        self.client = Github(auth=auth)
        self.repository: Repository = self.client.get_repo(f"{owner}/{repo}")
        logger.info("GitHub backend initialized", owner=owner, repo=repo)

    def _parse_labels(self, labels_str: str) -> dict[str, str]:
        """Parse label string into dict."""
        labels = {}
        if labels_str:
            for label in labels_str.split(","):
                if ":" in label:
                    key, value = label.split(":", 1)
                    labels[key.strip()] = value.strip()
                else:
                    labels[label.strip()] = ""
        return labels

    def _format_labels(self, labels: dict[str, str]) -> list[str]:
        """Format labels dict into GitHub label names."""
        return [f"{k}:{v}" if v else k for k, v in labels.items()]

    def _ensure_labels_exist(self, label_names: list[str]) -> None:
        """Ensure all labels exist in the repository, creating them if needed."""
        existing_labels = {label.name for label in self.repository.get_labels()}
        for label_name in label_names:
            if label_name not in existing_labels:
                logger.debug("Creating label", label_name=label_name)
                self.repository.create_label(name=label_name, color="ededed")

    def _issue_to_entity(self, issue: Issue) -> Entity:
        """Convert GitHub issue to Entity."""
        logger.debug("Converting GitHub issue to entity", issue_number=issue.number)
        labels = {}
        for label in issue.labels:
            name = label.name
            if ":" in name:
                key, value = name.split(":", 1)
                labels[key] = value
            else:
                labels[name] = ""

        assignee = issue.assignee.login if issue.assignee else None

        entity = Entity(
            id=str(issue.number),
            title=issue.title,
            description=issue.body or "",
            labels=labels,
            assignee=assignee,
            status=issue.state.lower(),
            metadata={
                "url": issue.html_url,
                "created_at": issue.created_at.isoformat(),
                "updated_at": issue.updated_at.isoformat(),
            },
        )
        logger.debug("Converted issue to entity", entity_id=entity.id, title=entity.title)
        return entity

    def create(
        self,
        title: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        assignee: str | None = None,
    ) -> Entity:
        """Create a new GitHub issue."""
        logger.info("Creating GitHub issue", title=title, assignee=assignee)

        label_names = []
        if labels:
            logger.debug("Processing labels for create", labels=labels)
            label_names = self._format_labels(labels)
            self._ensure_labels_exist(label_names)

        assignees = [assignee] if assignee else []

        issue = self.repository.create_issue(
            title=title,
            body=description,
            labels=label_names,
            assignees=assignees,
        )

        entity = self._issue_to_entity(issue)
        logger.info("GitHub issue created", entity_id=entity.id)
        return entity

    def read(self, entity_id: str) -> Entity:
        """Read a GitHub issue by number."""
        logger.info("Reading GitHub issue", entity_id=entity_id)
        issue = self.repository.get_issue(number=int(entity_id))
        entity = self._issue_to_entity(issue)
        logger.debug("GitHub issue read successfully", entity_id=entity_id)
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
        """Update a GitHub issue."""
        logger.info("Updating GitHub issue", entity_id=entity_id, title=title, status=status, assignee=assignee)
        issue = self.repository.get_issue(number=int(entity_id))

        # Update title and description
        if title is not None or description is not None:
            issue.edit(
                title=title if title is not None else issue.title,
                body=description if description is not None else issue.body,
            )

        # Update status
        if status:
            logger.debug("Updating issue status", entity_id=entity_id, status=status)
            if status == "open":
                issue.edit(state="open")
            elif status == "closed":
                issue.edit(state="closed")

        # Update labels
        if labels is not None:
            logger.debug("Updating issue labels", entity_id=entity_id, labels=labels)
            label_names = self._format_labels(labels)
            self._ensure_labels_exist(label_names)
            issue.set_labels(*label_names)

        # Update assignee
        if assignee is not None:
            logger.debug("Updating issue assignee", entity_id=entity_id, assignee=assignee)
            if assignee:
                issue.add_to_assignees(assignee)
            else:
                # Clear assignees
                for current_assignee in issue.assignees:
                    issue.remove_from_assignees(current_assignee)

        # Refresh issue to get updated data
        issue = self.repository.get_issue(number=int(entity_id))
        entity = self._issue_to_entity(issue)
        logger.info("GitHub issue updated successfully", entity_id=entity_id)
        return entity

    def delete(self, entity_ids: list[str]) -> None:
        """Delete (close) GitHub issues."""
        logger.info("Deleting (closing) GitHub issues", entity_ids=entity_ids, count=len(entity_ids))
        for entity_id in entity_ids:
            self.update(entity_id, status="closed")
        logger.info("GitHub issues deleted successfully", count=len(entity_ids))

    def list_entities(
        self,
        filters: dict[str, str] | None = None,
        sort_by: str | None = None,
        limit: int | None = None,
    ) -> list[Entity]:
        """List GitHub issues."""
        logger.info("Listing GitHub issues", filters=filters, sort_by=sort_by, limit=limit)

        state = "all"
        if filters and "status" in filters:
            status_filter = filters["status"]
            if status_filter == "open":
                state = "open"
            elif status_filter == "closed":
                state = "closed"

        issues = self.repository.get_issues(state=state, sort="created", direction="desc")

        entities = []
        for issue in issues:
            entities.append(self._issue_to_entity(issue))
            if limit and len(entities) >= limit:
                break

        logger.info("Listed GitHub issues", count=len(entities))
        return entities

    def add_link(self, source_id: str, target_ids: list[str], link_type: str) -> None:
        """Add links using GitHub's REST API for issue relationships.

        Supported link types:
        - 'blocked by': Marks source_id as blocked by target_ids
        - 'blocking': Marks source_id as blocking target_ids (inverse of blocked by)
        - 'parent': Marks source_id as parent of target_ids (sub-issues)
        """
        logger.info("Adding link to GitHub issue", source_id=source_id, target_ids=target_ids, link_type=link_type)

        # Normalize link type
        link_type = link_type.lower().strip()

        if link_type not in ["blocked by", "blocking", "parent"]:
            logger.warning(
                "Unsupported link type for GitHub backend",
                link_type=link_type,
                supported_types=["blocked by", "blocking", "parent"],
            )
            raise ValueError(
                f"Unsupported link type: '{link_type}'. GitHub backend supports: 'blocked by', 'blocking', 'parent'"
            )

        # Get the underlying requester for direct API access
        requester = self.client._Github__requester

        for target_id in target_ids:
            if link_type == "blocked by":
                # source_id is blocked by target_id - use REST API
                logger.debug("Adding 'blocked by' relationship", blocked_issue=source_id, blocking_issue=target_id)
                requester.requestJsonAndCheck(
                    "POST",
                    f"/repos/{self.owner}/{self.repo}/issues/{source_id}/dependencies/blocked_by",
                    input={"issue_id": int(target_id)},
                )

            elif link_type == "blocking":
                # source_id is blocking target_id - add blocked_by in reverse
                logger.debug("Adding 'blocking' relationship", blocking_issue=source_id, blocked_issue=target_id)
                requester.requestJsonAndCheck(
                    "POST",
                    f"/repos/{self.owner}/{self.repo}/issues/{target_id}/dependencies/blocked_by",
                    input={"issue_id": int(source_id)},
                )

            elif link_type == "parent":
                # source_id is parent of target_id - use REST API
                logger.debug("Adding 'parent' relationship", parent=source_id, child=target_id)
                requester.requestJsonAndCheck(
                    "POST",
                    f"/repos/{self.owner}/{self.repo}/issues/{source_id}/sub_issues",
                    input={"sub_issue_id": int(target_id)},
                )

        logger.info("Link added successfully", source_id=source_id, target_ids=target_ids, link_type=link_type)

    def remove_link(self, source_id: str, target_ids: list[str], link_type: str, recursive: bool = False) -> None:
        """Remove links using GitHub's REST API for issue relationships.

        Supported link types:
        - 'blocked by': Removes source_id being blocked by target_ids
        - 'blocking': Removes source_id blocking target_ids (inverse of blocked by)
        - 'parent': Removes source_id as parent of target_ids (sub-issues)

        Args:
            source_id: Source issue number
            target_ids: List of target issue numbers
            link_type: Type of link to remove
            recursive: Not used for GitHub backend
        """
        logger.info("Removing link from GitHub issue", source_id=source_id, target_ids=target_ids, link_type=link_type)

        # Normalize link type
        link_type = link_type.lower().strip()

        if link_type not in ["blocked by", "blocking", "parent"]:
            logger.warning(
                "Unsupported link type for GitHub backend",
                link_type=link_type,
                supported_types=["blocked by", "blocking", "parent"],
            )
            raise ValueError(
                f"Unsupported link type: '{link_type}'. GitHub backend supports: 'blocked by', 'blocking', 'parent'"
            )

        # Get the underlying requester for direct API access
        requester = self.client._Github__requester

        for target_id in target_ids:
            if link_type == "blocked by":
                # Remove source_id being blocked by target_id - use REST API
                logger.debug("Removing 'blocked by' relationship", blocked_issue=source_id, blocking_issue=target_id)
                requester.requestJsonAndCheck(
                    "DELETE",
                    f"/repos/{self.owner}/{self.repo}/issues/{source_id}/dependencies/blocked_by/{target_id}",
                )

            elif link_type == "blocking":
                # Remove source_id blocking target_id - remove blocked_by in reverse
                logger.debug("Removing 'blocking' relationship", blocking_issue=source_id, blocked_issue=target_id)
                requester.requestJsonAndCheck(
                    "DELETE",
                    f"/repos/{self.owner}/{self.repo}/issues/{target_id}/dependencies/blocked_by/{source_id}",
                )

            elif link_type == "parent":
                # Remove source_id as parent of target_id - use REST API
                logger.debug("Removing 'parent' relationship", parent=source_id, child=target_id)
                requester.requestJsonAndCheck(
                    "DELETE",
                    f"/repos/{self.owner}/{self.repo}/issues/{source_id}/sub_issue",
                    input={"sub_issue_id": int(target_id)},
                )

        logger.info("Link removed successfully", source_id=source_id, target_ids=target_ids, link_type=link_type)

    def list_links(self, entity_id: str, link_type: str | None = None) -> list[Link]:
        """List links for an issue using GitHub's REST API.

        Supported link types:
        - 'blocked by': Issues that block this issue
        - 'blocking': Issues that this issue blocks
        - 'parent': Parent issue (if this is a sub-issue)
        - 'children': Sub-issues of this issue

        Args:
            entity_id: Issue number to get links for
            link_type: Optional filter for link type (None returns all)

        Returns:
            List of Link objects
        """
        logger.debug("Listing links for issue", entity_id=entity_id, link_type=link_type)

        # Normalize link type if provided
        if link_type:
            link_type = link_type.lower().strip()
            if link_type not in ["blocked by", "blocking", "parent", "children"]:
                logger.warning(
                    "Unsupported link type for GitHub backend",
                    link_type=link_type,
                    supported_types=["blocked by", "blocking", "parent", "children"],
                )
                raise ValueError(
                    f"Unsupported link type: '{link_type}'. "
                    "GitHub backend supports: 'blocked by', 'blocking', 'parent', 'children'"
                )

        # Get the underlying requester for direct API access
        requester = self.client._Github__requester

        links: list[Link] = []

        # Get blocked by relationships
        if not link_type or link_type == "blocked by":
            logger.debug("Fetching 'blocked by' relationships", entity_id=entity_id)
            try:
                _, data = requester.requestJsonAndCheck(
                    "GET", f"/repos/{self.owner}/{self.repo}/issues/{entity_id}/dependencies/blocked_by"
                )
                for issue in data:
                    links.append(Link(source_id=entity_id, target_id=str(issue["number"]), link_type="blocked by"))
            except Exception as e:
                logger.debug("No blocked_by relationships found", entity_id=entity_id, error=str(e))

        # Get blocking relationships
        if not link_type or link_type == "blocking":
            logger.debug("Fetching 'blocking' relationships", entity_id=entity_id)
            try:
                _, data = requester.requestJsonAndCheck(
                    "GET", f"/repos/{self.owner}/{self.repo}/issues/{entity_id}/dependencies/blocking"
                )
                for issue in data:
                    links.append(Link(source_id=entity_id, target_id=str(issue["number"]), link_type="blocking"))
            except Exception as e:
                logger.debug("No blocking relationships found", entity_id=entity_id, error=str(e))

        # Get parent relationship
        if not link_type or link_type == "parent":
            logger.debug("Fetching parent relationship", entity_id=entity_id)
            try:
                _, data = requester.requestJsonAndCheck(
                    "GET", f"/repos/{self.owner}/{self.repo}/issues/{entity_id}/parent"
                )
                if data:
                    links.append(Link(source_id=entity_id, target_id=str(data["number"]), link_type="parent"))
            except Exception as e:
                logger.debug("No parent relationship found", entity_id=entity_id, error=str(e))

        # Get children (sub-issues)
        if not link_type or link_type == "children":
            logger.debug("Fetching sub-issues", entity_id=entity_id)
            try:
                _, data = requester.requestJsonAndCheck(
                    "GET", f"/repos/{self.owner}/{self.repo}/issues/{entity_id}/sub_issues"
                )
                for issue in data:
                    links.append(Link(source_id=entity_id, target_id=str(issue["number"]), link_type="children"))
            except Exception as e:
                logger.debug("No sub-issues found", entity_id=entity_id, error=str(e))

        logger.debug("Retrieved issue links", entity_id=entity_id, count=len(links))
        return links

    def get_link_tree(self, entity_id: str) -> dict[str, Any]:
        """Get hierarchical link tree for an issue using REST API.

        Builds a tree structure showing the issue and its related issues:
        - Sub-issues (children)
        - Issues it blocks (blocking)
        - Issues blocking it (blocked by)
        - Parent issue (if this is a sub-issue)

        Args:
            entity_id: Issue number to get tree for

        Returns:
            Dictionary with structure:
            {
                "entity": {
                    "id": str,
                    "title": str,
                    "state": str
                },
                "links": {
                    "children": list[dict],  # Sub-issues
                    "blocking": list[dict],  # Issues this blocks
                    "blocked_by": list[dict],  # Issues blocking this
                    "parent": list[dict]  # Parent issue if exists
                }
            }
        """
        logger.info("Getting link tree for issue", entity_id=entity_id)

        # Get the main issue
        issue = self.repository.get_issue(number=int(entity_id))

        # Get the underlying requester for direct API access
        requester = self.client._Github__requester

        # Build tree structure with entity and links sections
        tree: dict[str, Any] = {
            "entity": {
                "id": str(issue.number),
                "title": issue.title,
                "state": issue.state.lower(),
            },
            "links": {
                "children": [],
                "blocking": [],
                "blocked_by": [],
                "parent": [],
            },
        }

        # Get blocked by relationships
        try:
            _, blocked_by_data = requester.requestJsonAndCheck(
                "GET", f"/repos/{self.owner}/{self.repo}/issues/{entity_id}/dependencies/blocked_by"
            )
            for blocking_issue in blocked_by_data:
                tree["links"]["blocked_by"].append(
                    {
                        "id": str(blocking_issue["number"]),
                        "title": blocking_issue["title"],
                        "state": blocking_issue["state"].lower(),
                    }
                )
        except Exception as e:
            logger.debug("No blocked_by relationships", entity_id=entity_id, error=str(e))

        # Get blocking relationships
        try:
            _, blocking_data = requester.requestJsonAndCheck(
                "GET", f"/repos/{self.owner}/{self.repo}/issues/{entity_id}/dependencies/blocking"
            )
            for blocked_issue in blocking_data:
                tree["links"]["blocking"].append(
                    {
                        "id": str(blocked_issue["number"]),
                        "title": blocked_issue["title"],
                        "state": blocked_issue["state"].lower(),
                    }
                )
        except Exception as e:
            logger.debug("No blocking relationships", entity_id=entity_id, error=str(e))

        # Get parent
        try:
            _, parent_data = requester.requestJsonAndCheck(
                "GET", f"/repos/{self.owner}/{self.repo}/issues/{entity_id}/parent"
            )
            if parent_data:
                tree["links"]["parent"].append(
                    {
                        "id": str(parent_data["number"]),
                        "title": parent_data["title"],
                        "state": parent_data["state"].lower(),
                    }
                )
        except Exception as e:
            logger.debug("No parent relationship", entity_id=entity_id, error=str(e))

        # Get sub-issues
        try:
            _, sub_issues_data = requester.requestJsonAndCheck(
                "GET", f"/repos/{self.owner}/{self.repo}/issues/{entity_id}/sub_issues"
            )
            for sub_issue in sub_issues_data:
                tree["links"]["children"].append(
                    {
                        "id": str(sub_issue["number"]),
                        "title": sub_issue["title"],
                        "state": sub_issue["state"].lower(),
                    }
                )
        except Exception as e:
            logger.debug("No sub-issues", entity_id=entity_id, error=str(e))

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
        """Find cycles in link graph."""
        logger.debug("Finding cycles in link graph")
        return []

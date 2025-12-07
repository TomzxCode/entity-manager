"""GitHub GraphQL backend implementation."""

import os
from typing import Any

import structlog
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

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
            token: GitHub personal access token (defaults to GITHUB_TOKEN env var)
        """
        self.owner = owner
        self.repo = repo
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token required (set GITHUB_TOKEN env var or pass token)")

        logger.debug("Initializing GitHub backend", owner=owner, repo=repo)
        transport = AIOHTTPTransport(
            url="https://api.github.com/graphql",
            headers={"Authorization": f"bearer {self.token}"},
        )
        self.client = Client(transport=transport, fetch_schema_from_transport=True)
        self._config: dict[str, str] = {}
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

    def _issue_to_entity(self, issue: dict[str, Any]) -> Entity:
        """Convert GitHub issue to Entity."""
        logger.debug("Converting GitHub issue to entity", issue_number=issue["number"])
        labels = {}
        for label in issue.get("labels", {}).get("nodes", []):
            name = label["name"]
            if ":" in name:
                key, value = name.split(":", 1)
                labels[key] = value
            else:
                labels[name] = ""

        assignee = None
        if issue.get("assignees", {}).get("nodes"):
            assignee = issue["assignees"]["nodes"][0]["login"]

        entity = Entity(
            id=str(issue["number"]),
            title=issue["title"],
            description=issue.get("body", "") or "",
            labels=labels,
            assignee=assignee,
            status=issue["state"].lower(),
            metadata={
                "url": issue["url"],
                "created_at": issue["createdAt"],
                "updated_at": issue["updatedAt"],
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
        mutation = gql(
            """
            mutation CreateIssue(
                $repositoryId: ID!
                $title: String!
                $body: String
                $labelIds: [ID!]
                $assigneeIds: [ID!]
            ) {
                createIssue(input: {
                    repositoryId: $repositoryId
                    title: $title
                    body: $body
                    labelIds: $labelIds
                    assigneeIds: $assigneeIds
                }) {
                    issue {
                        number
                        title
                        body
                        state
                        url
                        createdAt
                        updatedAt
                        labels(first: 100) {
                            nodes {
                                name
                            }
                        }
                        assignees(first: 1) {
                            nodes {
                                login
                            }
                        }
                    }
                }
            }
        """
        )

        repo_query = gql(
            """
            query GetRepo($owner: String!, $name: String!) {
                repository(owner: $owner, name: $name) {
                    id
                }
            }
        """
        )

        logger.debug("Fetching repository ID")
        result = self.client.execute(repo_query, variable_values={"owner": self.owner, "name": self.repo})
        repo_id = result["repository"]["id"]
        logger.debug("Repository ID fetched", repo_id=repo_id)

        label_ids = []
        assignee_ids = []

        if labels:
            logger.debug("Processing labels for create", labels=labels)
            # Get all existing label IDs from the repository
            repo_labels_query = gql(
                """
                query GetRepoLabels($owner: String!, $name: String!) {
                    repository(owner: $owner, name: $name) {
                        labels(first: 100) {
                            nodes {
                                id
                                name
                            }
                        }
                    }
                }
            """
            )

            repo_labels_result = self.client.execute(
                repo_labels_query, variable_values={"owner": self.owner, "name": self.repo}
            )

            # Create a map of label names to IDs
            label_name_to_id = {
                label["name"]: label["id"] for label in repo_labels_result["repository"]["labels"]["nodes"]
            }

            # Format the labels we want to set
            desired_label_names = self._format_labels(labels)

            # Find which labels need to be created
            labels_to_create = [name for name in desired_label_names if name not in label_name_to_id]

            # Create missing labels
            for label_name in labels_to_create:
                create_label_mutation = gql(
                    """
                    mutation CreateLabel($repositoryId: ID!, $name: String!, $color: String!) {
                        createLabel(input: {
                            repositoryId: $repositoryId
                            name: $name
                            color: $color
                        }) {
                            label {
                                id
                                name
                            }
                        }
                    }
                """
                )

                create_result = self.client.execute(
                    create_label_mutation,
                    variable_values={
                        "repositoryId": repo_id,
                        "name": label_name,
                        "color": "ededed",  # Default gray color
                    },
                )
                label_name_to_id[label_name] = create_result["createLabel"]["label"]["id"]

            # Get the label IDs we want to set
            label_ids = [label_name_to_id[name] for name in desired_label_names if name in label_name_to_id]

        params: dict[str, Any] = {
            "repositoryId": repo_id,
            "title": title,
            "body": description,
            "labelIds": label_ids,
            "assigneeIds": assignee_ids,
        }

        logger.debug("Executing create issue mutation")
        result = self.client.execute(mutation, variable_values=params)
        entity = self._issue_to_entity(result["createIssue"]["issue"])
        logger.info("GitHub issue created", entity_id=entity.id)
        return entity

    def read(self, entity_id: str) -> Entity:
        """Read a GitHub issue by number."""
        logger.info("Reading GitHub issue", entity_id=entity_id)
        query = gql(
            """
            query GetIssue($owner: String!, $name: String!, $number: Int!) {
                repository(owner: $owner, name: $name) {
                    issue(number: $number) {
                        number
                        title
                        body
                        state
                        url
                        createdAt
                        updatedAt
                        labels(first: 100) {
                            nodes {
                                name
                            }
                        }
                        assignees(first: 1) {
                            nodes {
                                login
                            }
                        }
                    }
                }
            }
        """
        )

        logger.debug("Executing read issue query", entity_id=entity_id)
        result = self.client.execute(
            query, variable_values={"owner": self.owner, "name": self.repo, "number": int(entity_id)}
        )
        entity = self._issue_to_entity(result["repository"]["issue"])
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
        query = gql(
            """
            query GetIssueId($owner: String!, $name: String!, $number: Int!) {
                repository(owner: $owner, name: $name) {
                    issue(number: $number) {
                        id
                    }
                }
            }
        """
        )

        logger.debug("Fetching issue ID for update", entity_id=entity_id)
        result = self.client.execute(
            query, variable_values={"owner": self.owner, "name": self.repo, "number": int(entity_id)}
        )
        issue_id = result["repository"]["issue"]["id"]
        logger.debug("Issue ID fetched", entity_id=entity_id, issue_id=issue_id)

        mutation = gql(
            """
            mutation UpdateIssue($issueId: ID!, $title: String, $body: String) {
                updateIssue(input: {
                    id: $issueId
                    title: $title
                    body: $body
                }) {
                    issue {
                        number
                        title
                        body
                        state
                        url
                        createdAt
                        updatedAt
                        labels(first: 100) {
                            nodes {
                                name
                            }
                        }
                        assignees(first: 1) {
                            nodes {
                                login
                            }
                        }
                    }
                }
            }
        """
        )

        params: dict[str, Any] = {"issueId": issue_id}
        if title:
            params["title"] = title
        if description is not None:
            params["body"] = description

        logger.debug("Executing update issue mutation", entity_id=entity_id)
        result = self.client.execute(mutation, variable_values=params)

        if status:
            logger.debug("Updating issue status", entity_id=entity_id, status=status)
            state_mutation = gql(
                """
                mutation UpdateIssueState($issueId: ID!, $state: IssueState!) {
                    updateIssue(input: {
                        id: $issueId
                        state: $state
                    }) {
                        issue {
                            number
                        }
                    }
                }
            """
            )
            state_value = "OPEN" if status == "open" else "CLOSED"
            self.client.execute(state_mutation, variable_values={"issueId": issue_id, "state": state_value})

        if labels is not None:
            logger.debug("Updating issue labels", entity_id=entity_id, labels=labels)
            # First, get all existing label IDs from the repository
            repo_labels_query = gql(
                """
                query GetRepoLabels($owner: String!, $name: String!) {
                    repository(owner: $owner, name: $name) {
                        labels(first: 100) {
                            nodes {
                                id
                                name
                            }
                        }
                    }
                }
            """
            )

            repo_labels_result = self.client.execute(
                repo_labels_query, variable_values={"owner": self.owner, "name": self.repo}
            )

            # Create a map of label names to IDs
            label_name_to_id = {
                label["name"]: label["id"] for label in repo_labels_result["repository"]["labels"]["nodes"]
            }

            # Format the labels we want to set
            desired_label_names = self._format_labels(labels)

            # Find which labels need to be created
            labels_to_create = [name for name in desired_label_names if name not in label_name_to_id]

            # Create missing labels
            for label_name in labels_to_create:
                create_label_mutation = gql(
                    """
                    mutation CreateLabel($repositoryId: ID!, $name: String!, $color: String!) {
                        createLabel(input: {
                            repositoryId: $repositoryId
                            name: $name
                            color: $color
                        }) {
                            label {
                                id
                                name
                            }
                        }
                    }
                """
                )

                # Get repository ID
                repo_query = gql(
                    """
                    query GetRepo($owner: String!, $name: String!) {
                        repository(owner: $owner, name: $name) {
                            id
                        }
                    }
                """
                )
                repo_result = self.client.execute(repo_query, variable_values={"owner": self.owner, "name": self.repo})
                repo_id = repo_result["repository"]["id"]

                create_result = self.client.execute(
                    create_label_mutation,
                    variable_values={
                        "repositoryId": repo_id,
                        "name": label_name,
                        "color": "ededed",  # Default gray color
                    },
                )
                label_name_to_id[label_name] = create_result["createLabel"]["label"]["id"]

            # Get the label IDs we want to set
            label_ids = [label_name_to_id[name] for name in desired_label_names if name in label_name_to_id]

            # Use updateIssue mutation with labelIds to replace all labels
            update_labels_mutation = gql(
                """
                mutation UpdateIssueLabels($issueId: ID!, $labelIds: [ID!]) {
                    updateIssue(input: {
                        id: $issueId
                        labelIds: $labelIds
                    }) {
                        issue {
                            number
                        }
                    }
                }
            """
            )

            self.client.execute(update_labels_mutation, variable_values={"issueId": issue_id, "labelIds": label_ids})

        entity = self._issue_to_entity(result["updateIssue"]["issue"])
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
        query = gql(
            """
            query ListIssues($owner: String!, $name: String!, $first: Int, $states: [IssueState!]) {
                repository(owner: $owner, name: $name) {
                    issues(first: $first, states: $states, orderBy: {field: CREATED_AT, direction: DESC}) {
                        nodes {
                            number
                            title
                            body
                            state
                            url
                            createdAt
                            updatedAt
                            labels(first: 100) {
                                nodes {
                                    name
                                }
                            }
                            assignees(first: 1) {
                                nodes {
                                    login
                                }
                            }
                        }
                    }
                }
            }
        """
        )

        states = None
        if filters and "status" in filters:
            status = filters["status"]
            if status == "open":
                states = ["OPEN"]
            elif status == "closed":
                states = ["CLOSED"]

        params: dict[str, Any] = {
            "owner": self.owner,
            "name": self.repo,
            "first": limit or 100,
            "states": states,
        }

        logger.debug("Executing list issues query", params=params)
        result = self.client.execute(query, variable_values=params)
        entities = [self._issue_to_entity(issue) for issue in result["repository"]["issues"]["nodes"]]
        logger.info("Listed GitHub issues", count=len(entities))
        return entities

    def add_link(self, source_id: str, target_ids: list[str], link_type: str) -> None:
        """Add links using GitHub's native issue relationships.

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

        # Get issue IDs for source and all targets
        query = gql(
            """
            query GetIssueId($owner: String!, $name: String!, $number: Int!) {
                repository(owner: $owner, name: $name) {
                    issue(number: $number) {
                        id
                    }
                }
            }
        """
        )

        logger.debug("Fetching issue ID for source", source_id=source_id)
        result = self.client.execute(
            query, variable_values={"owner": self.owner, "name": self.repo, "number": int(source_id)}
        )
        source_issue_id = result["repository"]["issue"]["id"]

        # Process each target
        for target_id in target_ids:
            logger.debug("Fetching issue ID for target", target_id=target_id)
            result = self.client.execute(
                query, variable_values={"owner": self.owner, "name": self.repo, "number": int(target_id)}
            )
            target_issue_id = result["repository"]["issue"]["id"]

            if link_type == "blocked by":
                # source_id is blocked by target_id
                mutation = gql(
                    """
                    mutation AddBlockedBy($issueId: ID!, $blockingIssueId: ID!) {
                        addBlockedBy(input: {
                            issueId: $issueId
                            blockingIssueId: $blockingIssueId
                        }) {
                            issue {
                                number
                            }
                            blockingIssue {
                                number
                            }
                        }
                    }
                """
                )
                logger.debug("Adding 'blocked by' relationship", blocked_issue=source_id, blocking_issue=target_id)
                self.client.execute(
                    mutation, variable_values={"issueId": source_issue_id, "blockingIssueId": target_issue_id}
                )
            elif link_type == "blocking":
                # source_id is blocking target_id (inverse: target is blocked by source)
                mutation = gql(
                    """
                    mutation AddBlockedBy($issueId: ID!, $blockingIssueId: ID!) {
                        addBlockedBy(input: {
                            issueId: $issueId
                            blockingIssueId: $blockingIssueId
                        }) {
                            issue {
                                number
                            }
                            blockingIssue {
                                number
                            }
                        }
                    }
                """
                )
                logger.debug("Adding 'blocking' relationship", blocking_issue=source_id, blocked_issue=target_id)
                self.client.execute(
                    mutation, variable_values={"issueId": target_issue_id, "blockingIssueId": source_issue_id}
                )
            elif link_type == "parent":
                # source_id is parent of target_id
                mutation = gql(
                    """
                    mutation AddSubIssue($issueId: ID!, $subIssueId: ID!) {
                        addSubIssue(input: {
                            issueId: $issueId
                            subIssueId: $subIssueId
                        }) {
                            issue {
                                number
                            }
                            subIssue {
                                number
                            }
                        }
                    }
                """
                )
                logger.debug("Adding 'parent' relationship", parent=source_id, child=target_id)
                self.client.execute(
                    mutation, variable_values={"issueId": source_issue_id, "subIssueId": target_issue_id}
                )

        logger.info("Link added successfully", source_id=source_id, target_ids=target_ids, link_type=link_type)

    def remove_link(self, source_id: str, target_ids: list[str], link_type: str, recursive: bool = False) -> None:
        """Remove links using GitHub's native issue relationships.

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

        # Get issue IDs for source and all targets
        query = gql(
            """
            query GetIssueId($owner: String!, $name: String!, $number: Int!) {
                repository(owner: $owner, name: $name) {
                    issue(number: $number) {
                        id
                    }
                }
            }
        """
        )

        logger.debug("Fetching issue ID for source", source_id=source_id)
        result = self.client.execute(
            query, variable_values={"owner": self.owner, "name": self.repo, "number": int(source_id)}
        )
        source_issue_id = result["repository"]["issue"]["id"]

        # Process each target
        for target_id in target_ids:
            logger.debug("Fetching issue ID for target", target_id=target_id)
            result = self.client.execute(
                query, variable_values={"owner": self.owner, "name": self.repo, "number": int(target_id)}
            )
            target_issue_id = result["repository"]["issue"]["id"]

            if link_type == "blocked by":
                # Remove source_id being blocked by target_id
                mutation = gql(
                    """
                    mutation RemoveBlockedBy($issueId: ID!, $blockingIssueId: ID!) {
                        removeBlockedBy(input: {
                            issueId: $issueId
                            blockingIssueId: $blockingIssueId
                        }) {
                            issue {
                                number
                            }
                            blockingIssue {
                                number
                            }
                        }
                    }
                """
                )
                logger.debug("Removing 'blocked by' relationship", blocked_issue=source_id, blocking_issue=target_id)
                self.client.execute(
                    mutation, variable_values={"issueId": source_issue_id, "blockingIssueId": target_issue_id}
                )
            elif link_type == "blocking":
                # Remove source_id blocking target_id (inverse: target blocked by source)
                mutation = gql(
                    """
                    mutation RemoveBlockedBy($issueId: ID!, $blockingIssueId: ID!) {
                        removeBlockedBy(input: {
                            issueId: $issueId
                            blockingIssueId: $blockingIssueId
                        }) {
                            issue {
                                number
                            }
                            blockingIssue {
                                number
                            }
                        }
                    }
                """
                )
                logger.debug("Removing 'blocking' relationship", blocking_issue=source_id, blocked_issue=target_id)
                self.client.execute(
                    mutation, variable_values={"issueId": target_issue_id, "blockingIssueId": source_issue_id}
                )
            elif link_type == "parent":
                # Remove source_id as parent of target_id
                mutation = gql(
                    """
                    mutation RemoveSubIssue($issueId: ID!, $subIssueId: ID!) {
                        removeSubIssue(input: {
                            issueId: $issueId
                            subIssueId: $subIssueId
                        }) {
                            issue {
                                number
                            }
                            subIssue {
                                number
                            }
                        }
                    }
                """
                )
                logger.debug("Removing 'parent' relationship", parent=source_id, child=target_id)
                self.client.execute(
                    mutation, variable_values={"issueId": source_issue_id, "subIssueId": target_issue_id}
                )

        logger.info("Link removed successfully", source_id=source_id, target_ids=target_ids, link_type=link_type)

    def list_links(self, entity_id: str, link_type: str | None = None) -> list[Link]:
        """List links for an issue using GitHub's native issue relationships.

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

        # Query to get all relationship types
        query = gql(
            """
            query GetIssueLinks($owner: String!, $name: String!, $number: Int!) {
                repository(owner: $owner, name: $name) {
                    issue(number: $number) {
                        number
                        blockedBy(first: 100) {
                            nodes {
                                number
                            }
                        }
                        blocking(first: 100) {
                            nodes {
                                number
                            }
                        }
                        parent {
                            number
                        }
                        subIssues(first: 100) {
                            nodes {
                                number
                            }
                        }
                    }
                }
            }
        """
        )

        logger.debug("Fetching issue relationships", entity_id=entity_id)
        result = self.client.execute(
            query, variable_values={"owner": self.owner, "name": self.repo, "number": int(entity_id)}
        )
        issue_data = result["repository"]["issue"]

        links: list[Link] = []

        # Process blocked by relationships
        if not link_type or link_type == "blocked by":
            for blocking_issue in issue_data.get("blockedBy", {}).get("nodes", []):
                links.append(Link(source_id=entity_id, target_id=str(blocking_issue["number"]), link_type="blocked by"))

        # Process blocking relationships
        if not link_type or link_type == "blocking":
            for blocked_issue in issue_data.get("blocking", {}).get("nodes", []):
                links.append(Link(source_id=entity_id, target_id=str(blocked_issue["number"]), link_type="blocking"))

        # Process parent relationship
        if not link_type or link_type == "parent":
            parent = issue_data.get("parent")
            if parent:
                links.append(Link(source_id=entity_id, target_id=str(parent["number"]), link_type="parent"))

        # Process children (sub-issues)
        if not link_type or link_type == "children":
            for sub_issue in issue_data.get("subIssues", {}).get("nodes", []):
                links.append(Link(source_id=entity_id, target_id=str(sub_issue["number"]), link_type="children"))

        logger.debug("Retrieved issue links", entity_id=entity_id, count=len(links))
        return links

    def get_link_tree(self, entity_id: str) -> dict[str, Any]:
        """Get hierarchical link tree for an issue.

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

        # Query to get all relationships
        query = gql(
            """
            query GetIssueLinks($owner: String!, $name: String!, $number: Int!) {
                repository(owner: $owner, name: $name) {
                    issue(number: $number) {
                        number
                        title
                        state
                        blockedBy(first: 100) {
                            nodes {
                                number
                                title
                                state
                            }
                        }
                        blocking(first: 100) {
                            nodes {
                                number
                                title
                                state
                            }
                        }
                        parent {
                            number
                            title
                            state
                        }
                        subIssues(first: 100) {
                            nodes {
                                number
                                title
                                state
                            }
                        }
                    }
                }
            }
        """
        )

        logger.debug("Fetching issue relationships for tree", entity_id=entity_id)
        result = self.client.execute(
            query, variable_values={"owner": self.owner, "name": self.repo, "number": int(entity_id)}
        )
        issue_data = result["repository"]["issue"]

        # Build tree structure with entity and links sections
        tree: dict[str, Any] = {
            "entity": {
                "id": str(issue_data["number"]),
                "title": issue_data["title"],
                "state": issue_data["state"].lower(),
            },
            "links": {
                "children": [],
                "blocking": [],
                "blocked_by": [],
                "parent": [],
            },
        }

        # Add sub-issues (children)
        for sub_issue in issue_data.get("subIssues", {}).get("nodes", []):
            tree["links"]["children"].append(
                {
                    "id": str(sub_issue["number"]),
                    "title": sub_issue["title"],
                    "state": sub_issue["state"].lower(),
                }
            )

        # Add issues this one blocks
        for blocked_issue in issue_data.get("blocking", {}).get("nodes", []):
            tree["links"]["blocking"].append(
                {
                    "id": str(blocked_issue["number"]),
                    "title": blocked_issue["title"],
                    "state": blocked_issue["state"].lower(),
                }
            )

        # Add issues blocking this one
        for blocking_issue in issue_data.get("blockedBy", {}).get("nodes", []):
            tree["links"]["blocked_by"].append(
                {
                    "id": str(blocking_issue["number"]),
                    "title": blocking_issue["title"],
                    "state": blocking_issue["state"].lower(),
                }
            )

        # Add parent if exists
        parent = issue_data.get("parent")
        if parent:
            tree["links"]["parent"].append(
                {
                    "id": str(parent["number"]),
                    "title": parent["title"],
                    "state": parent["state"].lower(),
                }
            )

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

    def get_config(self, key: str) -> str | None:
        """Get configuration value."""
        logger.debug("Getting config value", key=key)
        return self._config.get(key)

    def set_config(self, key: str, value: str) -> None:
        """Set configuration value."""
        logger.debug("Setting config value", key=key, value=value)
        self._config[key] = value

    def unset_config(self, key: str) -> None:
        """Unset configuration value."""
        logger.debug("Unsetting config value", key=key)
        self._config.pop(key, None)

    def list_config(self) -> dict[str, str]:
        """List all configuration."""
        logger.debug("Listing all config values")
        return self._config.copy()

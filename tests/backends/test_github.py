"""Tests for GitHub backend link functionality."""

from unittest.mock import MagicMock, Mock

import pytest
from gql import Client

from entity_manager.backends.github import GitHubBackend


@pytest.fixture
def mock_client() -> Mock:
    """Create a mock GraphQL client."""
    return MagicMock(spec=Client)


@pytest.fixture
def github_backend(mock_client: Mock, monkeypatch: pytest.MonkeyPatch) -> GitHubBackend:
    """Create a GitHub backend with mocked client."""
    monkeypatch.setenv("GITHUB_TOKEN", "fake_token")
    backend = GitHubBackend(owner="test_owner", repo="test_repo", token="fake_token")
    backend.client = mock_client
    return backend


def test_add_link_blocked_by(github_backend: GitHubBackend, mock_client: Mock) -> None:
    """Test adding a 'blocked by' link."""
    # Mock responses for getting issue IDs
    mock_client.execute.side_effect = [
        {"repository": {"issue": {"id": "source_issue_id"}}},  # source issue ID
        {"repository": {"issue": {"id": "target_issue_id"}}},  # target issue ID
        {"issue": {"number": 1}, "blockingIssue": {"number": 2}},  # mutation result
    ]

    github_backend.add_link(1, [2], "blocked by")

    # Verify the mutation was called
    assert mock_client.execute.call_count == 3
    mutation_call = mock_client.execute.call_args_list[2]
    assert "addBlockedBy" in str(mutation_call[0][0])
    assert mutation_call[1]["variable_values"]["issueId"] == "source_issue_id"
    assert mutation_call[1]["variable_values"]["blockingIssueId"] == "target_issue_id"


def test_add_link_blocking(github_backend: GitHubBackend, mock_client: Mock) -> None:
    """Test adding a 'blocking' link."""
    # Mock responses
    mock_client.execute.side_effect = [
        {"repository": {"issue": {"id": "source_issue_id"}}},
        {"repository": {"issue": {"id": "target_issue_id"}}},
        {"issue": {"number": 2}, "blockingIssue": {"number": 1}},
    ]

    github_backend.add_link(1, [2], "blocking")

    # Verify the mutation was called with inverted IDs (blocking is inverse of blocked by)
    assert mock_client.execute.call_count == 3
    mutation_call = mock_client.execute.call_args_list[2]
    assert "addBlockedBy" in str(mutation_call[0][0])
    assert mutation_call[1]["variable_values"]["issueId"] == "target_issue_id"
    assert mutation_call[1]["variable_values"]["blockingIssueId"] == "source_issue_id"


def test_add_link_parent(github_backend: GitHubBackend, mock_client: Mock) -> None:
    """Test adding a 'parent' link (sub-issue)."""
    # Mock responses
    mock_client.execute.side_effect = [
        {"repository": {"issue": {"id": "parent_issue_id"}}},
        {"repository": {"issue": {"id": "child_issue_id"}}},
        {"issue": {"number": 1}, "subIssue": {"number": 2}},
    ]

    github_backend.add_link(1, [2], "parent")

    # Verify the mutation was called
    assert mock_client.execute.call_count == 3
    mutation_call = mock_client.execute.call_args_list[2]
    assert "addSubIssue" in str(mutation_call[0][0])
    assert mutation_call[1]["variable_values"]["issueId"] == "parent_issue_id"
    assert mutation_call[1]["variable_values"]["subIssueId"] == "child_issue_id"


def test_add_link_invalid_type(github_backend: GitHubBackend) -> None:
    """Test adding a link with an invalid type."""
    with pytest.raises(ValueError, match="Unsupported link type"):
        github_backend.add_link(1, [2], "invalid_type")


def test_add_link_multiple_targets(github_backend: GitHubBackend, mock_client: Mock) -> None:
    """Test adding links to multiple targets."""
    # Mock responses for source + 2 targets
    mock_client.execute.side_effect = [
        {"repository": {"issue": {"id": "source_issue_id"}}},
        {"repository": {"issue": {"id": "target_issue_1_id"}}},
        {"issue": {"number": 1}, "blockingIssue": {"number": 2}},
        {"repository": {"issue": {"id": "target_issue_2_id"}}},
        {"issue": {"number": 1}, "blockingIssue": {"number": 3}},
    ]

    github_backend.add_link(1, [2, 3], "blocked by")

    # Should have 5 calls: 1 for source, 2 for targets, 2 for mutations
    assert mock_client.execute.call_count == 5


def test_remove_link_blocked_by(github_backend: GitHubBackend, mock_client: Mock) -> None:
    """Test removing a 'blocked by' link."""
    # Mock responses
    mock_client.execute.side_effect = [
        {"repository": {"issue": {"id": "source_issue_id"}}},
        {"repository": {"issue": {"id": "target_issue_id"}}},
        {"issue": {"number": 1}, "blockingIssue": {"number": 2}},
    ]

    github_backend.remove_link(1, [2], "blocked by")

    # Verify the mutation was called
    assert mock_client.execute.call_count == 3
    mutation_call = mock_client.execute.call_args_list[2]
    assert "removeBlockedBy" in str(mutation_call[0][0])
    assert mutation_call[1]["variable_values"]["issueId"] == "source_issue_id"
    assert mutation_call[1]["variable_values"]["blockingIssueId"] == "target_issue_id"


def test_remove_link_blocking(github_backend: GitHubBackend, mock_client: Mock) -> None:
    """Test removing a 'blocking' link."""
    # Mock responses
    mock_client.execute.side_effect = [
        {"repository": {"issue": {"id": "source_issue_id"}}},
        {"repository": {"issue": {"id": "target_issue_id"}}},
        {"issue": {"number": 2}, "blockingIssue": {"number": 1}},
    ]

    github_backend.remove_link(1, [2], "blocking")

    # Verify the mutation was called with inverted IDs
    assert mock_client.execute.call_count == 3
    mutation_call = mock_client.execute.call_args_list[2]
    assert "removeBlockedBy" in str(mutation_call[0][0])
    assert mutation_call[1]["variable_values"]["issueId"] == "target_issue_id"
    assert mutation_call[1]["variable_values"]["blockingIssueId"] == "source_issue_id"


def test_remove_link_parent(github_backend: GitHubBackend, mock_client: Mock) -> None:
    """Test removing a 'parent' link."""
    # Mock responses
    mock_client.execute.side_effect = [
        {"repository": {"issue": {"id": "parent_issue_id"}}},
        {"repository": {"issue": {"id": "child_issue_id"}}},
        {"issue": {"number": 1}, "subIssue": {"number": 2}},
    ]

    github_backend.remove_link(1, [2], "parent")

    # Verify the mutation was called
    assert mock_client.execute.call_count == 3
    mutation_call = mock_client.execute.call_args_list[2]
    assert "removeSubIssue" in str(mutation_call[0][0])
    assert mutation_call[1]["variable_values"]["issueId"] == "parent_issue_id"
    assert mutation_call[1]["variable_values"]["subIssueId"] == "child_issue_id"


def test_remove_link_invalid_type(github_backend: GitHubBackend) -> None:
    """Test removing a link with an invalid type."""
    with pytest.raises(ValueError, match="Unsupported link type"):
        github_backend.remove_link(1, [2], "invalid_type")


def test_list_links_all_types(github_backend: GitHubBackend, mock_client: Mock) -> None:
    """Test listing all link types for an issue."""
    # Mock response with all relationship types
    mock_client.execute.return_value = {
        "repository": {
            "issue": {
                "number": 1,
                "blockedBy": {"nodes": [{"number": 2}, {"number": 3}]},
                "blocking": {"nodes": [{"number": 4}]},
                "parent": {"number": 5},
                "subIssues": {"nodes": [{"number": 6}, {"number": 7}]},
            }
        }
    }

    links = github_backend.list_links(1)

    # Should have 2 blocked by, 1 blocking, 1 parent, 2 children = 6 total
    assert len(links) == 6

    # Check each type
    blocked_by = [link for link in links if link.link_type == "blocked by"]
    assert len(blocked_by) == 2
    assert blocked_by[0].target_id in ["2", "3"]

    blocking = [link for link in links if link.link_type == "blocking"]
    assert len(blocking) == 1
    assert blocking[0].target_id == "4"

    parent = [link for link in links if link.link_type == "parent"]
    assert len(parent) == 1
    assert parent[0].target_id == "5"

    children = [link for link in links if link.link_type == "children"]
    assert len(children) == 2
    assert children[0].target_id in ["6", "7"]


def test_list_links_filtered(github_backend: GitHubBackend, mock_client: Mock) -> None:
    """Test listing links filtered by type."""
    mock_client.execute.return_value = {
        "repository": {
            "issue": {
                "number": 1,
                "blockedBy": {"nodes": [{"number": 2}]},
                "blocking": {"nodes": [{"number": 3}]},
                "parent": None,
                "subIssues": {"nodes": []},
            }
        }
    }

    # Filter by 'blocked by'
    links = github_backend.list_links(1, "blocked by")
    assert len(links) == 1
    assert links[0].link_type == "blocked by"
    assert links[0].target_id == "2"


def test_list_links_empty(github_backend: GitHubBackend, mock_client: Mock) -> None:
    """Test listing links when there are no relationships."""
    mock_client.execute.return_value = {
        "repository": {
            "issue": {
                "number": 1,
                "blockedBy": {"nodes": []},
                "blocking": {"nodes": []},
                "parent": None,
                "subIssues": {"nodes": []},
            }
        }
    }

    links = github_backend.list_links(1)
    assert len(links) == 0


def test_list_links_invalid_type(github_backend: GitHubBackend) -> None:
    """Test listing links with an invalid type."""
    with pytest.raises(ValueError, match="Unsupported link type"):
        github_backend.list_links(1, "invalid_type")


def test_add_link_case_insensitive(github_backend: GitHubBackend, mock_client: Mock) -> None:
    """Test that link types are case-insensitive."""
    # Mock responses
    mock_client.execute.side_effect = [
        {"repository": {"issue": {"id": "source_issue_id"}}},
        {"repository": {"issue": {"id": "target_issue_id"}}},
        {"issue": {"number": 1}, "blockingIssue": {"number": 2}},
    ]

    # Should accept uppercase and mixed case
    github_backend.add_link(1, [2], "BLOCKED BY")

    assert mock_client.execute.call_count == 3


def test_remove_link_case_insensitive(github_backend: GitHubBackend, mock_client: Mock) -> None:
    """Test that link types are case-insensitive for removal."""
    # Mock responses
    mock_client.execute.side_effect = [
        {"repository": {"issue": {"id": "source_issue_id"}}},
        {"repository": {"issue": {"id": "target_issue_id"}}},
        {"issue": {"number": 1}, "blockingIssue": {"number": 2}},
    ]

    github_backend.remove_link(1, [2], "Blocked By")

    assert mock_client.execute.call_count == 3

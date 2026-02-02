"""Tests for GitHub backend link functionality."""

from unittest.mock import MagicMock, Mock

import pytest
from github import Github
from github.Repository import Repository

from entity_manager.backends.github import GitHubBackend


@pytest.fixture
def mock_github_client() -> Mock:
    """Create a mock PyGithub client."""
    client = MagicMock(spec=Github)
    client._Github__requester = MagicMock()
    return client


@pytest.fixture
def mock_repository() -> Mock:
    """Create a mock repository."""
    return MagicMock(spec=Repository)


@pytest.fixture
def github_backend(mock_github_client: Mock, mock_repository: Mock, monkeypatch: pytest.MonkeyPatch) -> GitHubBackend:
    """Create a GitHub backend with mocked client."""

    # Mock the get_repo method to return our mock repository
    mock_github_client.get_repo.return_value = mock_repository

    # Patch the Github class to return our mock client
    with monkeypatch.context() as m:
        m.setattr("entity_manager.backends.github.Github", lambda auth: mock_github_client)
        backend = GitHubBackend(owner="test_owner", repo="test_repo", token="fake_token")

    return backend


def test_add_link_blocked_by(github_backend: GitHubBackend) -> None:
    """Test adding a 'blocked by' link."""
    # Mock REST API execution
    mock_requester = github_backend.client._Github__requester
    mock_requester.requestJsonAndCheck.return_value = ({}, {})

    github_backend.add_link("1", ["2"], "blocked by")

    # Verify REST API was called
    mock_requester.requestJsonAndCheck.assert_called_once()
    call_args = mock_requester.requestJsonAndCheck.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "/repos/test_owner/test_repo/issues/1/dependencies/blocked_by"
    assert call_args[1]["input"]["issue_id"] == 2


def test_add_link_blocking(github_backend: GitHubBackend) -> None:
    """Test adding a 'blocking' link."""
    # Mock REST API execution
    mock_requester = github_backend.client._Github__requester
    mock_requester.requestJsonAndCheck.return_value = ({}, {})

    github_backend.add_link("1", ["2"], "blocking")

    # Verify the REST API was called with inverted relationship (blocking is inverse of blocked_by)
    call_args = mock_requester.requestJsonAndCheck.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "/repos/test_owner/test_repo/issues/2/dependencies/blocked_by"
    assert call_args[1]["input"]["issue_id"] == 1


def test_add_link_parent(github_backend: GitHubBackend) -> None:
    """Test adding a 'parent' link (sub-issue)."""
    # Mock REST API execution
    mock_requester = github_backend.client._Github__requester
    mock_requester.requestJsonAndCheck.return_value = ({}, {})

    github_backend.add_link("1", ["2"], "parent")

    # Verify the REST API was called
    call_args = mock_requester.requestJsonAndCheck.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "/repos/test_owner/test_repo/issues/1/sub_issues"
    assert call_args[1]["input"]["sub_issue_id"] == 2


def test_add_link_invalid_type(github_backend: GitHubBackend) -> None:
    """Test adding a link with an invalid type."""
    with pytest.raises(ValueError, match="Unsupported link type"):
        github_backend.add_link("1", ["2"], "invalid_type")


def test_add_link_multiple_targets(github_backend: GitHubBackend) -> None:
    """Test adding links to multiple targets."""
    # Mock REST API execution
    mock_requester = github_backend.client._Github__requester
    mock_requester.requestJsonAndCheck.return_value = ({}, {})

    github_backend.add_link("1", ["2", "3"], "blocked by")

    # Should call REST API twice (once per target)
    assert mock_requester.requestJsonAndCheck.call_count == 2


def test_remove_link_blocked_by(github_backend: GitHubBackend) -> None:
    """Test removing a 'blocked by' link."""
    # Mock REST API execution
    mock_requester = github_backend.client._Github__requester
    mock_requester.requestJsonAndCheck.return_value = ({}, {})

    github_backend.remove_link("1", ["2"], "blocked by")

    # Verify the REST API was called
    call_args = mock_requester.requestJsonAndCheck.call_args
    assert call_args[0][0] == "DELETE"
    assert call_args[0][1] == "/repos/test_owner/test_repo/issues/1/dependencies/blocked_by/2"


def test_remove_link_blocking(github_backend: GitHubBackend) -> None:
    """Test removing a 'blocking' link."""
    # Mock REST API execution
    mock_requester = github_backend.client._Github__requester
    mock_requester.requestJsonAndCheck.return_value = ({}, {})

    github_backend.remove_link("1", ["2"], "blocking")

    # Verify the REST API was called with inverted IDs
    call_args = mock_requester.requestJsonAndCheck.call_args
    assert call_args[0][0] == "DELETE"
    assert call_args[0][1] == "/repos/test_owner/test_repo/issues/2/dependencies/blocked_by/1"


def test_remove_link_parent(github_backend: GitHubBackend) -> None:
    """Test removing a 'parent' link."""
    # Mock REST API execution
    mock_requester = github_backend.client._Github__requester
    mock_requester.requestJsonAndCheck.return_value = ({}, {})

    github_backend.remove_link("1", ["2"], "parent")

    # Verify the REST API was called
    call_args = mock_requester.requestJsonAndCheck.call_args
    assert call_args[0][0] == "DELETE"
    assert call_args[0][1] == "/repos/test_owner/test_repo/issues/1/sub_issue"
    assert call_args[1]["input"]["sub_issue_id"] == 2


def test_remove_link_invalid_type(github_backend: GitHubBackend) -> None:
    """Test removing a link with an invalid type."""
    with pytest.raises(ValueError, match="Unsupported link type"):
        github_backend.remove_link("1", ["2"], "invalid_type")


def test_list_links_all_types(github_backend: GitHubBackend) -> None:
    """Test listing all link types for an issue."""
    # Mock REST API responses
    mock_requester = github_backend.client._Github__requester

    def mock_api_call(method: str, url: str):
        if "blocked_by" in url:
            return ({}, [{"number": 2}, {"number": 3}])
        elif "blocking" in url:
            return ({}, [{"number": 4}])
        elif "parent" in url:
            return ({}, {"number": 5})
        elif "sub_issues" in url:
            return ({}, [{"number": 6}, {"number": 7}])
        return ({}, [])

    mock_requester.requestJsonAndCheck.side_effect = mock_api_call

    links = github_backend.list_links("1")

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


def test_list_links_filtered(github_backend: GitHubBackend) -> None:
    """Test listing links filtered by type."""
    # Mock REST API response
    mock_requester = github_backend.client._Github__requester
    mock_requester.requestJsonAndCheck.return_value = ({}, [{"number": 2}])

    # Filter by 'blocked by'
    links = github_backend.list_links("1", "blocked by")
    assert len(links) == 1
    assert links[0].link_type == "blocked by"
    assert links[0].target_id == "2"


def test_list_links_empty(github_backend: GitHubBackend) -> None:
    """Test listing links when there are no relationships."""
    # Mock REST API to raise exceptions (no relationships found)
    mock_requester = github_backend.client._Github__requester
    mock_requester.requestJsonAndCheck.side_effect = Exception("Not found")

    links = github_backend.list_links("1")
    assert len(links) == 0


def test_list_links_invalid_type(github_backend: GitHubBackend) -> None:
    """Test listing links with an invalid type."""
    with pytest.raises(ValueError, match="Unsupported link type"):
        github_backend.list_links("1", "invalid_type")


def test_add_link_case_insensitive(github_backend: GitHubBackend) -> None:
    """Test that link types are case-insensitive."""
    # Mock REST API execution
    mock_requester = github_backend.client._Github__requester
    mock_requester.requestJsonAndCheck.return_value = ({}, {})

    # Should accept uppercase and mixed case
    github_backend.add_link("1", ["2"], "BLOCKED BY")

    # Verify the REST API was called
    mock_requester.requestJsonAndCheck.assert_called_once()


def test_remove_link_case_insensitive(github_backend: GitHubBackend) -> None:
    """Test that link types are case-insensitive for removal."""
    # Mock REST API execution
    mock_requester = github_backend.client._Github__requester
    mock_requester.requestJsonAndCheck.return_value = ({}, {})

    github_backend.remove_link("1", ["2"], "Blocked By")

    # Verify the REST API was called
    mock_requester.requestJsonAndCheck.assert_called_once()


def test_init_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test initialization without token raises error."""
    with pytest.raises(ValueError, match="GitHub token required"):
        GitHubBackend(owner="test_owner", repo="test_repo", token=None)


def test_create_issue(github_backend: GitHubBackend, mock_repository: Mock) -> None:
    """Test creating a GitHub issue."""
    # Mock the created issue
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.body = "Test description"
    mock_issue.state = "open"
    mock_issue.labels = []
    mock_issue.assignee = None
    mock_issue.html_url = "https://github.com/test_owner/test_repo/issues/1"
    mock_issue.created_at = MagicMock()
    mock_issue.created_at.isoformat = lambda: "2024-01-01T00:00:00"
    mock_issue.updated_at = MagicMock()
    mock_issue.updated_at.isoformat = lambda: "2024-01-01T00:00:00"

    mock_repository.create_issue.return_value = mock_issue
    mock_repository.get_labels.return_value = []

    entity = github_backend.create("Test Issue", description="Test description")

    assert entity.id == "1"
    assert entity.title == "Test Issue"
    assert entity.description == "Test description"
    mock_repository.create_issue.assert_called_once()


def test_create_issue_with_labels(github_backend: GitHubBackend, mock_repository: Mock) -> None:
    """Test creating issue with labels."""
    # Mock the created issue
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.body = ""
    mock_issue.state = "open"
    mock_label = MagicMock()
    mock_label.name = "bug"
    mock_issue.labels = [mock_label]
    mock_issue.assignee = None
    mock_issue.html_url = "https://github.com/test_owner/test_repo/issues/1"
    mock_issue.created_at = MagicMock()
    mock_issue.created_at.isoformat = lambda: "2024-01-01T00:00:00"
    mock_issue.updated_at = MagicMock()
    mock_issue.updated_at.isoformat = lambda: "2024-01-01T00:00:00"

    mock_repository.create_issue.return_value = mock_issue
    mock_repository.get_labels.return_value = []

    github_backend.create("Test Issue", labels={"bug": "", "priority": "high"})

    # Verify labels were ensured to exist
    assert mock_repository.create_label.call_count >= 1


def test_read_issue(github_backend: GitHubBackend, mock_repository: Mock) -> None:
    """Test reading a GitHub issue."""
    # Mock the issue
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.body = "Test description"
    mock_issue.state = "open"
    mock_label = MagicMock()
    mock_label.name = "bug"
    mock_issue.labels = [mock_label]
    mock_assignee = MagicMock()
    mock_assignee.login = "test_user"
    mock_issue.assignee = mock_assignee
    mock_issue.html_url = "https://github.com/test_owner/test_repo/issues/1"
    mock_issue.created_at = MagicMock()
    mock_issue.created_at.isoformat = lambda: "2024-01-01T00:00:00"
    mock_issue.updated_at = MagicMock()
    mock_issue.updated_at.isoformat = lambda: "2024-01-01T00:00:00"

    mock_repository.get_issue.return_value = mock_issue

    entity = github_backend.read("1")

    assert entity.id == "1"
    assert entity.title == "Test Issue"
    assert entity.assignee == "test_user"
    assert entity.labels == {"bug": ""}
    mock_repository.get_issue.assert_called_once_with(number=1)


def test_update_issue_title(github_backend: GitHubBackend, mock_repository: Mock) -> None:
    """Test updating issue title."""
    # Mock the issue
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Updated Title"
    mock_issue.body = "Test description"
    mock_issue.state = "open"
    mock_issue.labels = []
    mock_issue.assignee = None
    mock_issue.html_url = "https://github.com/test_owner/test_repo/issues/1"
    mock_issue.created_at = MagicMock()
    mock_issue.created_at.isoformat = lambda: "2024-01-01T00:00:00"
    mock_issue.updated_at = MagicMock()
    mock_issue.updated_at.isoformat = lambda: "2024-01-01T00:00:00"

    mock_repository.get_issue.return_value = mock_issue

    entity = github_backend.update("1", title="Updated Title")

    assert entity.title == "Updated Title"
    mock_issue.edit.assert_called_once()


def test_update_issue_status(github_backend: GitHubBackend, mock_repository: Mock) -> None:
    """Test updating issue status."""
    # Mock the issue
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.body = ""
    mock_issue.state = "closed"
    mock_issue.labels = []
    mock_issue.assignee = None
    mock_issue.html_url = "https://github.com/test_owner/test_repo/issues/1"
    mock_issue.created_at = MagicMock()
    mock_issue.created_at.isoformat = lambda: "2024-01-01T00:00:00"
    mock_issue.updated_at = MagicMock()
    mock_issue.updated_at.isoformat = lambda: "2024-01-01T00:00:00"

    mock_repository.get_issue.return_value = mock_issue

    entity = github_backend.update("1", status="closed")

    assert entity.status == "closed"
    assert mock_issue.edit.call_count >= 1


def test_update_issue_labels(github_backend: GitHubBackend, mock_repository: Mock) -> None:
    """Test updating issue labels."""
    # Mock the issue
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.body = ""
    mock_issue.state = "open"
    mock_label = MagicMock()
    mock_label.name = "bug"
    mock_issue.labels = [mock_label]
    mock_issue.assignee = None
    mock_issue.html_url = "https://github.com/test_owner/test_repo/issues/1"
    mock_issue.created_at = MagicMock()
    mock_issue.created_at.isoformat = lambda: "2024-01-01T00:00:00"
    mock_issue.updated_at = MagicMock()
    mock_issue.updated_at.isoformat = lambda: "2024-01-01T00:00:00"

    mock_repository.get_issue.return_value = mock_issue
    mock_repository.get_labels.return_value = []

    github_backend.update("1", labels={"bug": ""})

    mock_issue.set_labels.assert_called_once()


def test_update_issue_assignee(github_backend: GitHubBackend, mock_repository: Mock) -> None:
    """Test updating issue assignee."""
    # Mock the issue
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.body = ""
    mock_issue.state = "open"
    mock_issue.labels = []
    mock_assignee = MagicMock()
    mock_assignee.login = "new_user"
    mock_issue.assignee = mock_assignee
    mock_issue.assignees = []
    mock_issue.html_url = "https://github.com/test_owner/test_repo/issues/1"
    mock_issue.created_at = MagicMock()
    mock_issue.created_at.isoformat = lambda: "2024-01-01T00:00:00"
    mock_issue.updated_at = MagicMock()
    mock_issue.updated_at.isoformat = lambda: "2024-01-01T00:00:00"

    mock_repository.get_issue.return_value = mock_issue

    github_backend.update("1", assignee="new_user")

    mock_issue.add_to_assignees.assert_called_once_with("new_user")


def test_delete_issues(github_backend: GitHubBackend, mock_repository: Mock) -> None:
    """Test deleting (closing) issues."""
    # Mock the issue
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.body = ""
    mock_issue.state = "closed"
    mock_issue.labels = []
    mock_issue.assignee = None
    mock_issue.html_url = "https://github.com/test_owner/test_repo/issues/1"
    mock_issue.created_at = MagicMock()
    mock_issue.created_at.isoformat = lambda: "2024-01-01T00:00:00"
    mock_issue.updated_at = MagicMock()
    mock_issue.updated_at.isoformat = lambda: "2024-01-01T00:00:00"

    mock_repository.get_issue.return_value = mock_issue

    github_backend.delete(["1", "2"])

    # Should have been called twice (once per issue)
    assert mock_repository.get_issue.call_count >= 2


def test_list_entities_all(github_backend: GitHubBackend, mock_repository: Mock) -> None:
    """Test listing all issues."""
    # Mock issues
    mock_issue1 = MagicMock()
    mock_issue1.number = 1
    mock_issue1.title = "Issue 1"
    mock_issue1.body = ""
    mock_issue1.state = "open"
    mock_issue1.labels = []
    mock_issue1.assignee = None
    mock_issue1.html_url = "https://github.com/test_owner/test_repo/issues/1"
    mock_issue1.created_at = MagicMock()
    mock_issue1.created_at.isoformat = lambda: "2024-01-01T00:00:00"
    mock_issue1.updated_at = MagicMock()
    mock_issue1.updated_at.isoformat = lambda: "2024-01-01T00:00:00"

    mock_issue2 = MagicMock()
    mock_issue2.number = 2
    mock_issue2.title = "Issue 2"
    mock_issue2.body = ""
    mock_issue2.state = "closed"
    mock_issue2.labels = []
    mock_issue2.assignee = None
    mock_issue2.html_url = "https://github.com/test_owner/test_repo/issues/2"
    mock_issue2.created_at = MagicMock()
    mock_issue2.created_at.isoformat = lambda: "2024-01-01T00:00:00"
    mock_issue2.updated_at = MagicMock()
    mock_issue2.updated_at.isoformat = lambda: "2024-01-01T00:00:00"

    mock_repository.get_issues.return_value = [mock_issue1, mock_issue2]

    entities = github_backend.list_entities()

    assert len(entities) == 2
    mock_repository.get_issues.assert_called_once()


def test_list_entities_with_status_filter(github_backend: GitHubBackend, mock_repository: Mock) -> None:
    """Test listing issues with status filter."""
    # Mock issue
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Open Issue"
    mock_issue.body = ""
    mock_issue.state = "open"
    mock_issue.labels = []
    mock_issue.assignee = None
    mock_issue.html_url = "https://github.com/test_owner/test_repo/issues/1"
    mock_issue.created_at = MagicMock()
    mock_issue.created_at.isoformat = lambda: "2024-01-01T00:00:00"
    mock_issue.updated_at = MagicMock()
    mock_issue.updated_at.isoformat = lambda: "2024-01-01T00:00:00"

    mock_repository.get_issues.return_value = [mock_issue]

    entities = github_backend.list_entities(filters={"status": "open"})

    assert len(entities) == 1
    assert entities[0].status == "open"


def test_list_entities_with_limit(github_backend: GitHubBackend, mock_repository: Mock) -> None:
    """Test listing issues with limit."""
    # Mock multiple issues
    issues = []
    for i in range(10):
        mock_issue = MagicMock()
        mock_issue.number = i
        mock_issue.title = f"Issue {i}"
        mock_issue.body = ""
        mock_issue.state = "open"
        mock_issue.labels = []
        mock_issue.assignee = None
        mock_issue.html_url = f"https://github.com/test_owner/test_repo/issues/{i}"
        mock_issue.created_at = MagicMock()
        mock_issue.created_at.isoformat = lambda: "2024-01-01T00:00:00"
        mock_issue.updated_at = MagicMock()
        mock_issue.updated_at.isoformat = lambda: "2024-01-01T00:00:00"
        issues.append(mock_issue)

    mock_repository.get_issues.return_value = issues

    entities = github_backend.list_entities(limit=5)

    assert len(entities) == 5


def test_get_link_tree(github_backend: GitHubBackend, mock_repository: Mock) -> None:
    """Test getting link tree."""
    # Mock the issue
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.state = "open"
    mock_repository.get_issue.return_value = mock_issue

    # Mock REST API responses
    mock_requester = github_backend.client._Github__requester

    def mock_api_call(method: str, url: str):
        if "blocked_by" in url:
            return ({}, [{"number": 2, "title": "Blocking Issue", "state": "open"}])
        elif "blocking" in url:
            return ({}, [{"number": 3, "title": "Blocked Issue", "state": "open"}])
        elif "parent" in url:
            return ({}, {"number": 4, "title": "Parent Issue", "state": "open"})
        elif "sub_issues" in url:
            return ({}, [{"number": 5, "title": "Child Issue", "state": "open"}])
        return ({}, [])

    mock_requester.requestJsonAndCheck.side_effect = mock_api_call

    tree = github_backend.get_link_tree("1")

    assert tree["entity"]["id"] == "1"
    assert len(tree["links"]["blocked_by"]) == 1
    assert len(tree["links"]["blocking"]) == 1
    assert len(tree["links"]["parent"]) == 1
    assert len(tree["links"]["children"]) == 1


def test_find_cycles(github_backend: GitHubBackend) -> None:
    """Test finding cycles (not implemented, returns empty list)."""
    cycles = github_backend.find_cycles()
    assert cycles == []

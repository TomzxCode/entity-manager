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

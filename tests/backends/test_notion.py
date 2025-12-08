"""Tests for Notion backend functionality."""

from unittest.mock import MagicMock, Mock

import pytest
from notion_client import Client

from entity_manager.backends.notion import NotionBackend


@pytest.fixture
def mock_notion_client() -> Mock:
    """Create a mock Notion client."""
    client = MagicMock(spec=Client)
    client.pages = MagicMock()
    client.databases = MagicMock()
    return client


@pytest.fixture
def notion_backend(mock_notion_client: Mock, monkeypatch: pytest.MonkeyPatch) -> NotionBackend:
    """Create a Notion backend with mocked client."""
    with monkeypatch.context() as m:
        m.setattr("entity_manager.backends.notion.Client", lambda auth: mock_notion_client)
        backend = NotionBackend(token="fake_token", database_id="fake_db_id")

    return backend


@pytest.fixture
def sample_notion_page() -> dict:
    """Create a sample Notion page response."""
    return {
        "id": "test-page-id-123",
        "url": "https://notion.so/test-page-id-123",
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-01T00:00:00.000Z",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "Test Task"}]},
            "Description": {"type": "rich_text", "rich_text": [{"plain_text": "Test description"}]},
            "Status": {"type": "status", "status": {"name": "Open"}},
            "Labels": {"type": "multi_select", "multi_select": [{"name": "bug"}, {"name": "priority:high"}]},
            "Assignee": {"type": "people", "people": [{"id": "user-123", "name": "Test User"}]},
        },
    }


def test_create_entity(notion_backend: NotionBackend, mock_notion_client: Mock, sample_notion_page: dict) -> None:
    """Test creating a new entity."""
    mock_notion_client.pages.create.return_value = sample_notion_page

    entity = notion_backend.create(
        title="Test Task", description="Test description", labels={"priority": "high"}, assignee="user-123"
    )

    assert entity.id == "test-page-id-123"
    assert entity.title == "Test Task"
    assert entity.description == "Test description"
    assert entity.status == "open"

    # Verify the API was called with correct parameters
    mock_notion_client.pages.create.assert_called_once()
    call_kwargs = mock_notion_client.pages.create.call_args[1]
    assert call_kwargs["parent"]["database_id"] == "fake_db_id"
    assert "Name" in call_kwargs["properties"]


def test_read_entity(notion_backend: NotionBackend, mock_notion_client: Mock, sample_notion_page: dict) -> None:
    """Test reading an entity."""
    mock_notion_client.pages.retrieve.return_value = sample_notion_page

    entity = notion_backend.read("test-page-id-123")

    assert entity.id == "test-page-id-123"
    assert entity.title == "Test Task"
    assert entity.description == "Test description"
    assert entity.status == "open"

    mock_notion_client.pages.retrieve.assert_called_once_with(page_id="test-page-id-123")


def test_update_entity(notion_backend: NotionBackend, mock_notion_client: Mock, sample_notion_page: dict) -> None:
    """Test updating an entity."""
    # Setup mocks - update doesn't return anything, read returns updated page
    updated_page = sample_notion_page.copy()
    updated_page["properties"]["Name"]["title"] = [{"plain_text": "Updated Task"}]
    mock_notion_client.pages.retrieve.return_value = updated_page

    entity = notion_backend.update("test-page-id-123", title="Updated Task")

    assert entity.title == "Updated Task"

    # Verify update was called
    mock_notion_client.pages.update.assert_called_once()
    call_kwargs = mock_notion_client.pages.update.call_args[1]
    assert call_kwargs["page_id"] == "test-page-id-123"


def test_delete_entity(notion_backend: NotionBackend, mock_notion_client: Mock) -> None:
    """Test deleting (archiving) entities."""
    notion_backend.delete(["page-1", "page-2"])

    # Verify pages were archived
    assert mock_notion_client.pages.update.call_count == 2
    calls = mock_notion_client.pages.update.call_args_list
    assert calls[0][1]["page_id"] == "page-1"
    assert calls[0][1]["archived"] is True
    assert calls[1][1]["page_id"] == "page-2"
    assert calls[1][1]["archived"] is True


def test_list_entities(notion_backend: NotionBackend, mock_notion_client: Mock, sample_notion_page: dict) -> None:
    """Test listing entities."""
    mock_notion_client.databases.query.return_value = {"results": [sample_notion_page]}

    entities = notion_backend.list_entities()

    assert len(entities) == 1
    assert entities[0].id == "test-page-id-123"
    assert entities[0].title == "Test Task"

    mock_notion_client.databases.query.assert_called_once()


def test_list_entities_with_filters(
    notion_backend: NotionBackend, mock_notion_client: Mock, sample_notion_page: dict
) -> None:
    """Test listing entities with filters."""
    mock_notion_client.databases.query.return_value = {"results": [sample_notion_page]}

    entities = notion_backend.list_entities(filters={"status": "open"}, limit=10)

    assert len(entities) == 1

    # Verify filter was applied
    call_kwargs = mock_notion_client.databases.query.call_args[1]
    assert "filter" in call_kwargs
    assert call_kwargs["page_size"] == 10


def test_add_link(notion_backend: NotionBackend, mock_notion_client: Mock, sample_notion_page: dict) -> None:
    """Test adding a link."""
    # Setup - retrieve returns existing page, update adds the link
    existing_page = sample_notion_page.copy()
    existing_page["properties"]["Blocked By"] = {"type": "relation", "relation": [{"id": "existing-page"}]}
    mock_notion_client.pages.retrieve.return_value = existing_page

    notion_backend.add_link("test-page-id-123", ["target-page-id"], "blocked by")

    # Verify retrieve was called to get existing relations
    mock_notion_client.pages.retrieve.assert_called_with(page_id="test-page-id-123")

    # Verify update was called with combined relations
    mock_notion_client.pages.update.assert_called_once()
    call_kwargs = mock_notion_client.pages.update.call_args[1]
    assert call_kwargs["page_id"] == "test-page-id-123"
    assert "Blocked By" in call_kwargs["properties"]


def test_add_link_invalid_type(notion_backend: NotionBackend) -> None:
    """Test adding a link with invalid type."""
    with pytest.raises(ValueError, match="Unsupported link type"):
        notion_backend.add_link("source", ["target"], "invalid_type")


def test_remove_link(notion_backend: NotionBackend, mock_notion_client: Mock, sample_notion_page: dict) -> None:
    """Test removing a link."""
    # Setup - retrieve returns page with existing relations
    existing_page = sample_notion_page.copy()
    existing_page["properties"]["Blocked By"] = {
        "type": "relation",
        "relation": [{"id": "page-1"}, {"id": "page-2"}],
    }
    mock_notion_client.pages.retrieve.return_value = existing_page

    notion_backend.remove_link("test-page-id-123", ["page-1"], "blocked by")

    # Verify update was called with page-2 remaining
    mock_notion_client.pages.update.assert_called_once()
    call_kwargs = mock_notion_client.pages.update.call_args[1]
    relations = call_kwargs["properties"]["Blocked By"]["relation"]
    assert len(relations) == 1
    assert relations[0]["id"] == "page-2"


def test_remove_link_invalid_type(notion_backend: NotionBackend) -> None:
    """Test removing a link with invalid type."""
    with pytest.raises(ValueError, match="Unsupported link type"):
        notion_backend.remove_link("source", ["target"], "invalid_type")


def test_list_links(notion_backend: NotionBackend, mock_notion_client: Mock, sample_notion_page: dict) -> None:
    """Test listing links."""
    # Setup page with relations
    page_with_links = sample_notion_page.copy()
    page_with_links["properties"]["Blocked By"] = {"type": "relation", "relation": [{"id": "page-1"}]}
    page_with_links["properties"]["Blocking"] = {"type": "relation", "relation": [{"id": "page-2"}]}
    page_with_links["properties"]["Parent"] = {"type": "relation", "relation": [{"id": "page-3"}]}
    page_with_links["properties"]["Children"] = {"type": "relation", "relation": [{"id": "page-4"}]}

    mock_notion_client.pages.retrieve.return_value = page_with_links

    links = notion_backend.list_links("test-page-id-123")

    assert len(links) == 4
    link_types = {link.link_type for link in links}
    assert link_types == {"blocked by", "blocking", "parent", "children"}


def test_list_links_filtered(notion_backend: NotionBackend, mock_notion_client: Mock, sample_notion_page: dict) -> None:
    """Test listing links filtered by type."""
    page_with_links = sample_notion_page.copy()
    page_with_links["properties"]["Blocked By"] = {"type": "relation", "relation": [{"id": "page-1"}]}
    page_with_links["properties"]["Blocking"] = {"type": "relation", "relation": [{"id": "page-2"}]}

    mock_notion_client.pages.retrieve.return_value = page_with_links

    links = notion_backend.list_links("test-page-id-123", "blocked by")

    assert len(links) == 1
    assert links[0].link_type == "blocked by"
    assert links[0].target_id == "page-1"


def test_get_link_tree(notion_backend: NotionBackend, mock_notion_client: Mock, sample_notion_page: dict) -> None:
    """Test getting link tree."""
    # Setup page with relations
    page_with_links = sample_notion_page.copy()
    page_with_links["properties"]["Blocked By"] = {"type": "relation", "relation": [{"id": "blocking-page"}]}
    page_with_links["properties"]["Children"] = {"type": "relation", "relation": [{"id": "child-page"}]}

    # Mock the retrieve calls - first for main page, then for linked pages
    def mock_retrieve(page_id: str):
        if page_id == "test-page-id-123":
            return page_with_links
        elif page_id == "blocking-page":
            return {
                "id": "blocking-page",
                "url": "https://notion.so/blocking-page",
                "created_time": "2024-01-01T00:00:00.000Z",
                "last_edited_time": "2024-01-01T00:00:00.000Z",
                "properties": {
                    "Name": {"type": "title", "title": [{"plain_text": "Blocking Task"}]},
                    "Status": {"type": "status", "status": {"name": "Open"}},
                },
            }
        elif page_id == "child-page":
            return {
                "id": "child-page",
                "url": "https://notion.so/child-page",
                "created_time": "2024-01-01T00:00:00.000Z",
                "last_edited_time": "2024-01-01T00:00:00.000Z",
                "properties": {
                    "Name": {"type": "title", "title": [{"plain_text": "Child Task"}]},
                    "Status": {"type": "status", "status": {"name": "Open"}},
                },
            }
        return sample_notion_page

    mock_notion_client.pages.retrieve.side_effect = mock_retrieve

    tree = notion_backend.get_link_tree("test-page-id-123")

    assert tree["entity"]["id"] == "test-page-id-123"
    assert tree["entity"]["title"] == "Test Task"
    assert len(tree["links"]["blocked_by"]) == 1
    assert len(tree["links"]["children"]) == 1
    assert tree["links"]["blocked_by"][0]["title"] == "Blocking Task"
    assert tree["links"]["children"][0]["title"] == "Child Task"


def test_parse_properties_title(notion_backend: NotionBackend) -> None:
    """Test parsing title property."""
    properties = {"Name": {"type": "title", "title": [{"plain_text": "Test"}]}}
    parsed = notion_backend._parse_properties(properties)
    assert parsed["Name"] == "Test"


def test_parse_properties_rich_text(notion_backend: NotionBackend) -> None:
    """Test parsing rich text property."""
    properties = {"Description": {"type": "rich_text", "rich_text": [{"plain_text": "Test description"}]}}
    parsed = notion_backend._parse_properties(properties)
    assert parsed["Description"] == "Test description"


def test_parse_properties_multi_select(notion_backend: NotionBackend) -> None:
    """Test parsing multi-select property."""
    properties = {"Tags": {"type": "multi_select", "multi_select": [{"name": "tag1"}, {"name": "tag2"}]}}
    parsed = notion_backend._parse_properties(properties)
    assert parsed["Tags"] == ["tag1", "tag2"]


def test_parse_properties_status(notion_backend: NotionBackend) -> None:
    """Test parsing status property."""
    properties = {"Status": {"type": "status", "status": {"name": "In Progress"}}}
    parsed = notion_backend._parse_properties(properties)
    assert parsed["Status"] == "In Progress"


def test_parse_properties_people(notion_backend: NotionBackend) -> None:
    """Test parsing people property."""
    properties = {"Assignee": {"type": "people", "people": [{"id": "user-1", "name": "User One"}]}}
    parsed = notion_backend._parse_properties(properties)
    assert parsed["Assignee"] == ["User One"]


def test_parse_properties_relation(notion_backend: NotionBackend) -> None:
    """Test parsing relation property."""
    properties = {"Related": {"type": "relation", "relation": [{"id": "page-1"}, {"id": "page-2"}]}}
    parsed = notion_backend._parse_properties(properties)
    assert parsed["Related"] == ["page-1", "page-2"]


def test_find_cycles(notion_backend: NotionBackend) -> None:
    """Test find_cycles returns empty list (placeholder implementation)."""
    cycles = notion_backend.find_cycles()
    assert cycles == []

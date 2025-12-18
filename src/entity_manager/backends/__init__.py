"""Backend implementations for entity manager."""

from entity_manager.backends.beads import BeadsBackend
from entity_manager.backends.github import GitHubBackend
from entity_manager.backends.notion import NotionBackend

__all__ = ["BeadsBackend", "GitHubBackend", "NotionBackend"]

# Backend Interface Specification

## Overview

The Backend Interface defines the abstract contract that all entity manager backends MUST implement. It provides a unified API for CRUD operations on entities, link management, and graph traversal, independent of the underlying data storage mechanism.

## Purpose

The backend interface abstracts away the differences between various data sources (GitHub, Beads, Notion, etc.) allowing the application to work with any backend through a common interface.

## Requirements

### Core Backend Contract

### Backend Implementation

- A backend implementation MUST inherit from the abstract `Backend` base class.
- A backend implementation MUST implement all abstract methods defined in the `Backend` class.
- A backend implementation MUST raise appropriate exceptions when operations cannot be completed (e.g., network errors, authentication failures, resource not found).

### Entity CRUD Operations

#### Create Operation

- The `create()` method MUST accept parameters: `title` (required), `description` (optional), `labels` (optional), and `assignee` (optional).
- The `create()` method MUST return an `Entity` object with a unique `id`.
- The `create()` method MUST create the entity in the underlying data source.
- The `create()` method MAY validate input parameters before creation.

#### Read Operation

- The `read()` method MUST accept an `entity_id` parameter.
- The `read()` method MUST return an `Entity` object populated with data from the underlying data source.
- The `read()` method MUST raise an error if the entity does not exist.
- The `read()` method SHOULD fetch the most current data from the data source (not from a stale cache).

#### Update Operation

- The `update()` method MUST accept an `entity_id` parameter and optional parameters for fields to update: `title`, `description`, `labels`, `status`, and `assignee`.
- The `update()` method MUST only update fields that are provided (non-None values).
- The `update()` method MUST return an `Entity` object reflecting the updated state.
- The `update()` method MUST raise an error if the entity does not exist.
- The `update()` MAY validate the status value against allowed values for the backend.

#### Delete Operation

- The `delete()` method MUST accept a list of `entity_ids`.
- The `delete()` method MUST remove all specified entities from the underlying data source.
- The `delete()` method SHOULD succeed silently if some entities do not exist.
- The `delete()` method MAY use "soft delete" (e.g., closing issues) if the backend does not support hard deletion.

#### List Operation

- The `list_entities()` method MUST accept optional parameters: `filters`, `sort_by`, and `limit`.
- The `list_entities()` method MUST return a list of `Entity` objects.
- The `list_entities()` method MUST support filtering by entity attributes (e.g., status, labels).
- The `list_entities()` method SHOULD support sorting results when `sort_by` is provided.
- The `list_entities()` method MUST limit results to the specified `limit` when provided.
- The `list_entities()` method SHOULD return results in a consistent order when sorting is not specified.

### Link Management Operations

#### Add Link

- The `add_link()` method MUST accept parameters: `source_id`, `target_ids` (list), and `link_type`.
- The `add_link()` method MUST create directed links from the source entity to each target entity.
- The `add_link()` method MUST persist links to the underlying data source.
- The `add_link()` method MAY validate that the link type is supported by the backend.
- The `add_link()` method MAY raise an error if creating a link would create an invalid relationship (e.g., circular dependency).

#### Remove Link

- The `remove_link()` method MUST accept parameters: `source_id`, `target_ids` (list), `link_type`, and `recursive` (boolean).
- The `remove_link()` method MUST remove the specified links from the underlying data source.
- When `recursive` is True, the `remove_link()` method SHOULD remove all transitive links as well.
- The `remove_link()` method SHOULD succeed silently if specified links do not exist.

#### List Links

- The `list_links()` method MUST accept an `entity_id` parameter and an optional `link_type` parameter.
- The `list_links()` method MUST return a list of `Link` objects.
- When `link_type` is provided, the `list_links()` method MUST only return links of that type.
- When `link_type` is not provided, the `list_links()` method SHOULD return all links for the entity.
- Each `Link` object MUST include `source_id`, `target_id`, and `link_type`.

### Graph Traversal Operations

#### Get Link Tree

- The `get_link_tree()` method MUST accept an `entity_id` parameter.
- The `get_link_tree()` method MUST return a dictionary with two keys: `entity` and `links`.
- The `entity` key MUST contain a dictionary with entity information: `id`, `title`, and `state`.
- The `links` key MUST contain a dictionary of link categories.
- The `links` dictionary SHOULD include standard categories: `children`, `blocking`, `blocked_by`, and `parent`.
- Each link category MUST contain a list of dictionaries, each with `id`, `title`, and `state`.

#### Find Cycles

- The `find_cycles()` method MUST return a list of cycles.
- Each cycle MUST be represented as a list of entity IDs forming the cycle.
- The `find_cycles()` method SHOULD detect all cycles in the link graph.
- The `find_cycles()` method MAY return an empty list if no cycles are found.
- The `find_cycles()` method SHOULD handle self-referential links (entity linked to itself).

### Backend-Specific Behavior

#### GitHub Backend

- The GitHub backend MUST map GitHub issues to entities.
- The GitHub backend MUST use issue numbers as entity IDs.
- The GitHub backend MUST support link types: `blocked by`, `blocking`, and `parent`.
- The GitHub backend MUST use GitHub's REST API for dependency and sub-issue relationships.
- The GitHub backend MUST create GitHub labels if they don't exist.
- The GitHub backend MUST handle authentication via personal access tokens.

#### Beads Backend

- The Beads backend MUST use beads hash format (e.g., `bd-a1b2`) for entity IDs.
- The Beads backend MUST store entities in the beads database format.
- The Beads backend MUST support the same link types as other backends where possible.

#### Notion Backend

- The Notion backend MUST use page IDs (UUIDs) as entity IDs.
- The Notion backend MUST map Notion database properties to entity attributes.
- The Notion backend MUST require a database with specific properties: Name, Description, Status, Labels, Assignee, Blocked By, Blocking, Parent, and Children.
- The Notion backend MUST use Notion's relation properties for links.

### Error Handling

- All backend methods MUST raise descriptive exceptions when operations fail.
- Backend methods SHOULD wrap underlying API errors in backend-agnostic exception types.
- Backend methods SHOULD log errors with sufficient context for debugging.

### Concurrency

- Backends MAY implement optimistic locking for update operations.
- Backends SHOULD handle rate limiting appropriately for external APIs.
- Backends SHOULD NOT maintain local state that could become stale.

### Testing Considerations

- Backend implementations SHOULD be testable with mock APIs.
- Backend implementations SHOULD provide a way to run against test data.
- Backend implementations SHOULD handle edge cases like empty results, missing entities, and malformed data gracefully.

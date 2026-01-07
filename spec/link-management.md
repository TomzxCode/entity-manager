# Link Management Specification

## Overview

The Link Management feature provides directed graph relationships between entities. Links enable expressing dependencies, hierarchical relationships, and other connections essential for coordinating work among multiple agents and tracking complex project structures.

## Purpose

Links solve the critical challenge of coordinating work in complex projects by:
- Expressing dependencies between requirements (blocked by, blocking)
- Representing hierarchical structures (parent/child sub-issues)
- Enabling agents to understand what work is blocked or blocking
- Supporting graph traversal and cycle detection
- Providing visibility into project structure and dependencies

## Requirements

### Link Data Model

#### Core Link Fields

- A link MUST have a `source_id` field (string) identifying the source entity.
- A link MUST have a `target_id` field (string) identifying the target entity.
- A link MUST have a `link_type` field (string) describing the relationship.
- Links MUST be directed (from source to target).

#### Link Identification

- A link is uniquely identified by the combination of `source_id`, `target_id`, and `link_type`.
- Multiple links MAY exist between the same entities with different link types.
- Multiple links of the same type MUST NOT exist between the same entities (idempotent add operations).

#### Link Types

The system MUST support the following standard link types:

- **"blocked by"**: Indicates that the source entity is blocked by the target entity. The source cannot proceed until the target is complete.
- **"blocking"**: Indicates that the source entity is blocking the target entity. Inverse of "blocked by".
- **"parent"**: Indicates that the source entity is the parent of the target entity (sub-issue relationship).
- **"children"**: Indicates that the source entity has the target as a child. Inverse of "parent".
- **"relates to"**: Generic relationship without semantic meaning (default link type).

Additional link types MAY be supported by backends or configured by users.

### Link Operations

#### Add Links

- The `add_link()` operation MUST accept a source entity ID, a list of target entity IDs, and a link type.
- The `add_link()` operation MUST create directed links from the source to each target.
- The `add_link()` operation MUST persist links to the backend storage.
- The `add_link()` operation MUST be idempotent (adding the same link twice should not create duplicates).
- The `add_link()` operation MAY validate that the link type is supported by the backend.
- The `add_link()` operation SHOULD verify that both source and target entities exist.
- When adding multiple links in one call, the operation MUST either succeed for all or fail for all (atomic).

#### Remove Links

- The `remove_link()` operation MUST accept a source entity ID, a list of target entity IDs, a link type, and a recursive flag.
- The `remove_link()` operation MUST remove the specified links from the backend storage.
- The `remove_link()` operation MUST be idempotent (removing a non-existent link should succeed silently).
- When the `recursive` flag is True, the `remove_link()` operation SHOULD also remove all transitive links reachable from the removed links.
- When the `recursive` flag is False (default), the `remove_link()` operation MUST only remove directly specified links.
- The `remove_link()` operation MAY validate that the link type is supported by the backend.

#### List Links

- The `list_links()` operation MUST accept an entity ID and an optional link type filter.
- The `list_links()` operation MUST return a list of `Link` objects where the entity is the source.
- When a link type is provided, the `list_links()` operation MUST only return links of that type.
- When no link type is provided, the `list_links()` operation SHOULD return all links for the entity.
- The `list_links()` operation MUST include links where the entity is the source (outgoing links).
- The `list_links()` operation MAY also include links where the entity is the target (incoming links) depending on backend capabilities.

#### Get Link Tree

- The `get_link_tree()` operation MUST accept an entity ID.
- The `get_link_tree()` operation MUST return a hierarchical structure containing:
  - The entity's ID, title, and state
  - Categorized lists of related entities by link type
- The `get_link_tree()` result MUST include at minimum these link categories:
  - `children`: Sub-issues or child entities
  - `blocking`: Entities that this entity blocks
  - `blocked_by`: Entities that block this entity
  - `parent`: Parent entity if one exists
- Each entry in link categories MUST include at minimum: entity ID, title, and state.
- The `get_link_tree()` operation MAY traverse multiple levels of links (implementation-defined).
- The `get_link_tree()` operation SHOULD handle missing or broken links gracefully.

#### Find Cycles

- The `find_cycles()` operation MUST return a list of cycles found in the link graph.
- Each cycle MUST be represented as a list of entity IDs in traversal order.
- The cycle list MUST be circular (the first entity is reachable from the last entity).
- The `find_cycles()` operation MUST detect self-referential links (entity linked to itself).
- The `find_cycles()` operation SHOULD detect all cycles in the graph.
- The `find_cycles()` operation MAY return an empty list if no cycles are found.

### Link Semantics and Behavior

#### "Blocked By" Links

- An entity with "blocked by" links represents work that cannot proceed until the blocking entities are complete.
- "Blocked by" links SHOULD be used to express hard dependencies.
- When an entity has open "blocked by" links, it SHOULD be considered unready to start.
- "Blocked by" links are the inverse of "blocking" links.
- If Entity A is "blocked by" Entity B, then Entity B is "blocking" Entity A.

#### "Parent" Links

- "Parent" links represent hierarchical decomposition of work.
- A parent entity represents a larger work item broken into child sub-issues.
- Child entities SHOULD represent smaller, more specific tasks.
- Parent-child relationships are typically used for organizing work, not expressing dependencies.
- "Parent" links are the inverse of "children" links.
- An entity SHOULD have at most one parent (acyclic hierarchy).

#### Cycle Detection and Prevention

- Cycles in "blocked by" links represent circular dependencies and SHOULD be considered invalid.
- Cycles in "parent" links represent circular hierarchies and SHOULD be considered invalid.
- The system MAY prevent creation of links that would create cycles in certain link types.
- The `find_cycles()` operation MUST be able to detect cycles regardless of link type.
- Applications SHOULD use `find_cycles()` to validate link structures before assuming no cycles exist.

### Link Storage and Persistence

- Links MUST be persisted to the backend storage system.
- Links MUST survive backend restarts and reconnections.
- Link persistence MUST be atomic (all links in an operation are saved or none are).
- Backends MAY store links differently based on their native capabilities:
  - GitHub: Uses issue dependencies API and sub-issues API
  - Notion: Uses relation properties
  - Beads: Uses native relationship fields

### Link Consistency

- When an entity is deleted, its associated links MAY be removed or become orphaned (backend-dependent).
- When a link is added, backends SHOULD verify that both entities exist.
- Links MAY become stale if target entities are deleted (backends SHOULD handle this gracefully).
- Backends MAY implement referential integrity for links where supported by the underlying system.

### Backend-Specific Link Support

#### GitHub Backend

- GitHub backend MUST support "blocked by", "blocking", and "parent" link types.
- GitHub backend MUST use the issue dependencies API for "blocked by" and "blocking" links.
- GitHub backend MUST use the sub-issues API for "parent" and "children" links.
- GitHub backend MUST synchronize bidirectional links (adding "blocked by" from A to B must make B "blocking" A).
- GitHub backend MAY not support arbitrary link types beyond the standard ones.

#### Notion Backend

- Notion backend MUST support all standard link types via relation properties.
- Notion backend MUST configure database schema with relation properties for each link type.
- Notion relation properties MUST be bidirectional (creating one direction creates the inverse).
- Notion backend MAY limit the number of relation properties in a database.

#### Beads Backend

- Beads backend MUST support link types compatible with beads' relationship model.
- Beads backend MAY have limitations on link type complexity.

### Link Queries and Traversal

#### Directional Traversal

- Links MUST support querying by direction (incoming vs outgoing).
- Outgoing links are links where the entity is the source.
- Incoming links are links where the entity is the target.
- The `get_link_tree()` operation SHOULD provide both incoming and outgoing links organized by type.

#### Graph Algorithms

- Cycle detection MUST use graph traversal algorithms (DFS or BFS).
- Cycle detection SHOULD have reasonable time complexity for the expected graph size.
- Cycle detection MAY use caching to improve performance on repeated calls.
- Graph traversal operations SHOULD handle disconnected graphs gracefully.

### Link Validation

#### Pre-creation Validation

- Systems MAY validate links before creation to prevent invalid relationships.
- Validation MAY include checking for cycles in certain link types.
- Validation MAY include checking for duplicate links (idempotent add should handle this).
- Validation MAY include checking entity existence.

#### Post-creation Validation

- Systems SHOULD use `find_cycles()` to detect invalid link structures after bulk operations.
- Systems SHOULD validate link integrity after external changes (e.g., manual GitHub edits).
- Systems SHOULD warn users about circular dependencies in "blocked by" links.

### Use Cases for LLM Collaboration

#### Dependency Awareness

- Agents MUST be able to query "blocked by" links to understand what they're waiting for.
- Agents MUST be able to query "blocking" links to understand what depends on their work.
- Agents SHOULD check dependencies before claiming work (avoid claiming blocked tasks).

#### Work Coordination

- Multiple agents can work on different branches of a parent-child hierarchy simultaneously.
- "Blocked by" links prevent agents from starting work that depends on incomplete work.
- Parent-child links help agents understand the context and scope of their assigned work.

#### Collision Prevention

- Before claiming work, agents SHOULD check if the entity is "blocked by" open entities.
- Before claiming work, agents SHOULD check if another agent is assigned to blocking entities.
- Agents SHOULD prioritize unblocked work over blocked work.

#### Progress Tracking

- Agents can use link trees to understand the full scope and status of related work.
- Project managers can use link structures to identify critical paths and bottlenecks.
- "Blocked by" links help identify what's blocking progress on high-priority items.

### Error Handling

- Link operations MUST raise descriptive errors for invalid operations.
- Error messages MUST include relevant context (entity IDs, link type, etc.).
- Attempting to add a link to a non-existent entity SHOULD raise an error.
- Attempting to create unsupported link types MUST raise an error with a list of supported types.

### Performance Considerations

- Link queries SHOULD be optimized for the expected graph size.
- `get_link_tree()` operations MAY limit traversal depth for performance.
- `find_cycles()` operations SHOULD use efficient graph algorithms.
- Backends MAY cache link information to reduce API calls.

### Security and Access Control

- Link operations MUST respect the backend's access control rules.
- Agents should only be able to add/remove links for entities they have permission to modify.
- Link visibility (list_links, get_link_tree) MUST respect entity read permissions.

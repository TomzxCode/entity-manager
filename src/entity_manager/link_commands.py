"""Link management commands for entity manager CLI."""

from cyclopts import App

link_app = App(name="link", help="Manage links between entities")


@link_app.command
def add(
    source_id: str,
    *target_ids: str,
    type: str = "relates-to",
) -> None:
    """Add links from source entity to target entities."""
    from entity_manager.cli import get_backend

    backend = get_backend()
    backend.add_link(source_id, list(target_ids), type)
    print(f"Added {len(target_ids)} link(s) from {source_id}")


@link_app.command
def remove(
    source_id: str,
    *target_ids: str,
    type: str = "relates-to",
    recursive: bool = False,
) -> None:
    """Remove links from source entity to target entities."""
    from entity_manager.cli import get_backend

    backend = get_backend()
    backend.remove_link(source_id, list(target_ids), type, recursive)
    print(f"Removed {len(target_ids)} link(s) from {source_id}")


@link_app.command(name="list")
def list_links(
    entity_id: str,
    type: str | None = None,
) -> None:
    """List all links for an entity."""
    from entity_manager.cli import get_backend

    backend = get_backend()
    links = backend.list_links(entity_id, type)

    if not links:
        print(f"No links found for entity {entity_id}")
        return

    print(f"Links for entity {entity_id}:\n")
    for link in links:
        print(f"  {link.source_id} --[{link.link_type}]--> {link.target_id}")


@link_app.command
def tree(entity_id: str) -> None:
    """Display the link tree of an entity."""
    from entity_manager.cli import get_backend

    backend = get_backend()
    tree = backend.get_link_tree(entity_id)

    # Print entity
    entity = tree["entity"]
    print(f"Entity: {entity['id']} {entity['title']} ({entity['state']})\n")

    # Print links dynamically
    links = tree["links"]

    for link_type, link_data in links.items():
        if not link_data:
            continue

        # Format the link type for display
        display_name = link_type.replace("_", " ").title()

        print(f"{display_name}:")
        for item in link_data:
            print(f"  - {item['id']} {item['title']}")
        print()


@link_app.command
def cycle() -> None:
    """Find and display cycles in links."""
    from entity_manager.cli import get_backend

    backend = get_backend()
    cycles = backend.find_cycles()

    if not cycles:
        print("No cycles found")
        return

    print(f"Found {len(cycles)} cycle(s):\n")
    for i, cycle in enumerate(cycles, 1):
        cycle_str = " -> ".join([f"{eid}" for eid in cycle])
        print(f"{i}. {cycle_str} -> {cycle[0]}")

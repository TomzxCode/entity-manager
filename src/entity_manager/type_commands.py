"""Type management commands for entity manager CLI."""

from cyclopts import App
from rich.console import Console

from entity_manager.models import PropertyDefinition, PropertyType
from entity_manager.type_manager import TypeManager

type_app = App(name="type", help="Manage entity types")
console = Console()


@type_app.command(name="list")
def list_types() -> None:
    """List all available entity types."""
    manager = TypeManager()
    types = manager.list_types()

    if not types:
        console.print("No entity types configured")
        return

    table_title = "Entity Types"
    console.print(f"\n[bold]{table_title}[/bold]\n")

    for entity_type in types:
        console.print(f"[cyan]{entity_type.name}[/cyan]")
        if entity_type.description:
            console.print(f"  Description: {entity_type.description}")
        if entity_type.properties:
            props_str = ", ".join([p.name for p in entity_type.properties])
            console.print(f"  Properties: {props_str}")
        console.print()


@type_app.command
def show(type_name: str) -> None:
    """Show details of a specific entity type.

    Args:
        type_name: Name of the type to show
    """
    manager = TypeManager()
    entity_type = manager.get_type(type_name)

    console.print(f"\n[bold cyan]{entity_type.name}[/bold cyan]")
    if entity_type.description:
        console.print(f"Description: {entity_type.description}")

    if not entity_type.properties:
        console.print("  No properties defined")
    else:
        console.print("\n[bold]Properties:[/bold]")
        for prop in entity_type.properties:
            required_str = "[red]required[/red]" if prop.required else ""
            default_str = f" (default: {prop.default})" if prop.default is not None else ""
            options_str = f" (options: {', '.join(str(o) for o in prop.options)})" if prop.options else ""
            console.print(f"  [cyan]{prop.name}[/cyan]: {prop.type.value}{default_str}{options_str} {required_str}")
            if prop.description:
                console.print(f"    {prop.description}")
    console.print()


@type_app.command
def create(name: str, description: str = "") -> None:
    """Create a new entity type.

    Args:
        name: Type name (must be unique)
        description: Type description
    """
    manager = TypeManager()

    console.print(f"\nCreating entity type [bold cyan]{name}[/bold cyan]")
    console.print("Add properties (press Enter with empty name to finish):\n")

    properties: list[PropertyDefinition] = []

    while True:
        prop_name = console.input("[cyan]Property name[/cyan]: ").strip()
        if not prop_name:
            break

        console.print("Available types: string, integer, float, boolean, array, dict")
        prop_type_str = console.input("[cyan]Property type[/cyan] [string]: ").strip() or "string"

        try:
            prop_type = PropertyType(prop_type_str)
        except ValueError:
            console.print("[red]Invalid type, using 'string'[/red]")
            prop_type = PropertyType.STRING

        default_input = console.input("[cyan]Default value[/cyan] (optional): ").strip()
        default_value = None if not default_input else default_input

        required_input = console.input("[cyan]Required[/cyan] [y/N]: ").strip().lower()
        required = required_input == "y"

        prop_description = console.input("[cyan]Description[/cyan] (optional): ").strip()

        options_input = console.input("[cyan]Options[/cyan] (comma-separated, optional): ").strip()
        options = None
        if options_input:
            options = [o.strip() for o in options_input.split(",")]

        prop = PropertyDefinition(
            name=prop_name,
            type=prop_type,
            default=default_value,
            required=required,
            description=prop_description,
            options=options,
        )
        properties.append(prop)
        console.print("[green]Property added[/green]\n")

    if not properties:
        console.print("[yellow]Type created with no properties[/yellow]")
    else:
        console.print(f"[green]Added {len(properties)} propert(ies)[/green]")

    manager.create_type(name=name, properties=properties, description=description)

    console.print(f"\n[green]Entity type '{name}' created successfully[/green]")


@type_app.command
def delete(type_name: str) -> None:
    """Delete an entity type.

    Args:
        type_name: Name of the type to delete
    """
    manager = TypeManager()

    confirm = console.input(f"Delete type '{type_name}'? [y/N]: ").strip().lower()
    if confirm != "y":
        console.print("Cancelled")
        return

    try:
        manager.delete_type(type_name)
        console.print(f"[green]Entity type '{type_name}' deleted[/green]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@type_app.command
def update(type_name: str, description: str | None = None) -> None:
    """Update an entity type.

    Args:
        type_name: Name of the type to update
        description: New description (optional)
    """
    manager = TypeManager()

    try:
        manager.update_type(name=type_name, description=description)
        console.print(f"[green]Entity type '{type_name}' updated[/green]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")

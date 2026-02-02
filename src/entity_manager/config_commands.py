"""Configuration commands for entity manager CLI."""

from cyclopts import App
from rich.console import Console
from rich.prompt import Prompt

from entity_manager.config import get_config

config_app = App(name="config", help="Manage configuration")

SENSITIVE_KEY_PATTERNS = ("token", "password", "secret", "api_key", "auth")
console = Console()


def _redact_value(key: str, value: str) -> str:
    """Redact a sensitive configuration value.

    Shows first 4 and last 4 characters, or "-redacted-" if 8 chars or less.

    Args:
        key: Configuration key
        value: Configuration value to potentially redact

    Returns:
        Original value or redacted version
    """
    key_lower = key.lower()
    if not any(pattern in key_lower for pattern in SENSITIVE_KEY_PATTERNS):
        return value
    if not value:
        return value
    if len(value) <= 8:
        return "-redacted-"
    return f"{value[:4]}...{value[-4:]}"


@config_app.command
def set(key: str, value: str, global_: bool = False) -> None:
    """Set a configuration setting.

    Args:
        key: Configuration key
        value: Configuration value
        global_: If True, set in global config. If False, set in local config.
    """
    config = get_config(use_global=global_)
    config.set(key, value)
    scope = "global" if global_ else "local"
    print(f"Set {key} = {value} ({scope})")


@config_app.command
def unset(key: str, global_: bool = False) -> None:
    """Unset a configuration setting.

    Args:
        key: Configuration key
        global_: If True, unset from global config. If False, unset from local config.
    """
    config = get_config(use_global=global_)
    config.unset(key)
    scope = "global" if global_ else "local"
    print(f"Unset {key} ({scope})")


@config_app.command
def get(key: str, global_: bool = False) -> None:
    """Get the value of a configuration setting.

    Args:
        key: Configuration key
        global_: If True, get from global config only. If False, get with global fallback.
    """
    config = get_config(use_global=global_)
    value = config.get(key)
    if value is None:
        print(f"{key} is not set")
    else:
        redacted_value = _redact_value(key, value)
        print(f"{key} = {redacted_value}")


@config_app.command(name="list")
def list_config(global_: bool = False) -> None:
    """List all configuration settings.

    Args:
        global_: If True, list global config only. If False, list merged config.
    """
    config = get_config(use_global=global_)
    settings = config.list()

    if not settings:
        scope = "global" if global_ else "local"
        print(f"No {scope} configuration settings")
        return

    scope = "Global" if global_ else "Configuration"
    print(f"{scope} settings:\n")
    for key, value in settings.items():
        redacted_value = _redact_value(key, value)
        print(f"{key} = {redacted_value}")


@config_app.command
def init(global_: bool = False) -> None:
    """Initialize or update backend configuration interactively.

    Args:
        global_: If True, set in global config. If False, set in local config.
    """
    config = get_config(use_global=global_)
    cfg = config._config

    console.print("\n[bold]Entity Manager Configuration[/bold]")
    console.print("Select the backend to use", style="dim")
    console.print("Available backends: backlog, beads, github, markdown, notion, redis, sqlite", style="dim")

    valid_backends = ["backlog", "beads", "github", "markdown", "notion", "redis", "sqlite"]
    backend = None
    existing_backend = cfg.get("backend")

    while backend not in valid_backends:
        backend = Prompt.ask("Backend", default=existing_backend or "")

        if existing_backend and backend == existing_backend:
            break

        if backend not in valid_backends:
            console.print(f"Unknown backend: {backend}. Please try again.", style="red")

    config.set("backend", backend)

    if backend == "backlog":
        existing_path = cfg.get("backlog.path")
        path = Prompt.ask("Backlog.md path", default=existing_path or "")
        if path:
            config.set("backlog.path", path)

    elif backend == "beads":
        existing_path = cfg.get("beads.project_path")
        project_path = Prompt.ask("Beads project path", default=existing_path or "")
        if project_path:
            config.set("beads.project_path", project_path)

    elif backend == "github":
        existing_owner = cfg.get("github.owner")
        owner = Prompt.ask("GitHub owner", default=existing_owner or "")
        if owner:
            config.set("github.owner", owner)

        existing_repo = cfg.get("github.repository")
        repo = Prompt.ask("GitHub repository", default=existing_repo or "")
        if repo:
            config.set("github.repository", repo)

        token = Prompt.ask("GitHub token", password=True, default="")
        if token:
            config.set("github.token", token)

    elif backend == "markdown":
        existing_path = cfg.get("markdown.directory_path")
        directory_path = Prompt.ask("Markdown directory path", default=existing_path or ".")
        config.set("markdown.directory_path", directory_path)

    elif backend == "notion":
        token = Prompt.ask("Notion token", password=True, default="")
        if token:
            config.set("notion.token", token)

        existing_db = cfg.get("notion.database_id")
        database_id = Prompt.ask("Notion database ID", default=existing_db or "")
        if database_id:
            config.set("notion.database_id", database_id)

    elif backend == "redis":
        existing_host = cfg.get("redis.host")
        host = Prompt.ask("Redis host", default=existing_host or "localhost")
        config.set("redis.host", host)

        existing_port = cfg.get("redis.port")
        port = Prompt.ask("Redis port", default=existing_port or "6379")
        config.set("redis.port", port)

        existing_db = cfg.get("redis.db")
        db = Prompt.ask("Redis database number", default=existing_db or "0")
        config.set("redis.db", db)

        password = Prompt.ask("Redis password (leave empty if none)", password=True, default="")
        if password:
            config.set("redis.password", password)

    elif backend == "sqlite":
        existing_path = cfg.get("sqlite.db_path")
        db_path = Prompt.ask("SQLite database path", default=existing_path or ".em.db")
        if db_path:
            config.set("sqlite.db_path", db_path)

    else:
        console.print(f"Unknown backend: {backend}", style="red")
        return

    scope = "global" if global_ else "local"
    console.print(f"\nInitialized {backend} backend ({scope})", style="green")

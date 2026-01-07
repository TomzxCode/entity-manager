# Getting Started

## Installation

### Using uv

```bash
uv tool install git+https://github.com/TomzxCode/entity-manager
```

## Configuration

Entity Manager requires configuration for various integrations. Create a `.env` file in your project directory:

```bash
# GitHub integration (optional)
GITHUB_TOKEN=your_github_token_here

# Notion integration (optional)
NOTION_TOKEN=your_notion_token_here
NOTION_DATABASE_ID=your_database_id_here
```

## Basic Usage

Once installed, you can use the CLI:

```bash
# Show help/available commands
entity-manager --help
```

## Next Steps

- Check out the [Usage](usage.md) guide for detailed command examples
- Read the [Architecture](architecture.md) documentation to understand how it works

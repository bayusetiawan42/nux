"""Internal skill discovery tool."""

from sharkyo.config import Config
from sharkyo.display import print_info
from sharkyo.search import search_skills

SCHEMA = {
    "type": "function",
    "function": {
        "name": "SKILL",
        "description": (
            "Search internal skills and guides for best practices or instructions on "
            "handling specialized tasks (such as 'reminder', 'timer', 'alarm', etc.). "
            "Call this when the user asks for a feature or task you need instructions to perform."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords describing the required skill or task (e.g. 'reminder', 'timer').",
                },
            },
            "required": ["query"],
        },
    },
}


def execute(args: dict, config: Config | None = None) -> tuple[str, bool]:
    """Execute skill search and return guide for the model."""
    query = args.get("query", "").strip()
    if not query:
        return "Error: 'query' parameter is required for SKILL search.", True

    guide = search_skills(query)
    if guide:
        print_info(f"Retrieved internal skill for: [bold cyan]{query}[/bold cyan]")
        return guide, True

    return f"No internal skill found matching '{query}'. Proceed using standard tools.", True

"""Tool registry — collects definitions and dispatches calls."""

from __future__ import annotations

from typing import Any

from climbers_journal.tools import intervals as intervals_tools

# All tool modules. Add new modules here.
_MODULES = [intervals_tools]


def get_all_definitions() -> list[dict[str, Any]]:
    """Return OpenAI-format tool definitions from all registered modules."""
    defs: list[dict[str, Any]] = []
    for mod in _MODULES:
        defs.extend(mod.definitions)
    return defs


async def dispatch(tool_name: str, arguments: dict[str, Any]) -> str:
    """Call the handler for *tool_name* and return the result string."""
    for mod in _MODULES:
        result = await mod.handle(tool_name, arguments)
        if result is not None:
            return result
    return f"Unknown tool: {tool_name}"

"""Tool registry — collects definitions and dispatches calls."""

from __future__ import annotations

from typing import Any

from climbers_journal.tools import intervals as intervals_tools
from climbers_journal.tools import journal as journal_tools
from climbers_journal.tools import record as record_tools

# All tool modules. Add new modules here.
_MODULES = [intervals_tools, journal_tools, record_tools]


def get_all_definitions() -> list[dict[str, Any]]:
    """Return OpenAI-format tool definitions from all registered modules."""
    defs: list[dict[str, Any]] = []
    for mod in _MODULES:
        defs.extend(mod.definitions)
    return defs


async def dispatch(
    tool_name: str, arguments: dict[str, Any], context: dict[str, Any] | None = None
) -> str:
    """Call the handler for *tool_name* and return the result string.

    *context* carries request-scoped resources (e.g. ``db_session``).
    """
    ctx = context or {}
    for mod in _MODULES:
        result = await mod.handle(tool_name, arguments, ctx)
        if result is not None:
            return result
    return f"Unknown tool: {tool_name}"

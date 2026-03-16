"""LLM service — multi-provider support via OpenAI-compatible API."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from openai import AsyncOpenAI, RateLimitError

from climbers_journal.config import get_settings
from climbers_journal.tools.registry import dispatch, get_all_definitions

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful training assistant for a climber and endurance athlete. "
    "You have access to two data sources:\n"
    "1. **Local climbing journal** — ascents, routes, crags, sessions, and climbing stats stored in the database. "
    "Use search_routes, get_ascents, get_sessions, get_climbing_stats, and get_training_overview to query this data. "
    "Use get_sessions for session-grouped queries (e.g. 'what did I climb last week at Kletterhalle Wien?').\n"
    "2. **intervals.icu** — live endurance training data (activities, wellness/CTL/ATL/HRV). "
    "Use get_activities, get_latest_activity, and get_wellness to fetch this data.\n\n"
    "Always use the available tools to fetch real data before answering questions about "
    "activities, training load, wellness, or performance trends. "
    "When the user describes a climbing session (routes climbed, attempted, etc.), "
    "use the parse_climbing_session tool to create a structured draft for them to review. "
    "For training overview questions, use get_training_overview to show both climbing and endurance side by side. "
    "Be concise and specific — reference actual numbers from the data."
)
MAX_TOOL_ROUNDS = 10
MAX_RETRIES = 2
RETRY_DELAY_S = 6

_clients: dict[str, AsyncOpenAI] = {}


def clear_clients() -> None:
    """Reset cached AsyncOpenAI instances (for tests)."""
    _clients.clear()


def _get_client(provider_name: str) -> AsyncOpenAI:
    """Get or create an AsyncOpenAI client for the given provider."""
    if provider_name not in _clients:
        settings = get_settings()
        provider_cfg = settings.llm.providers[provider_name]
        _clients[provider_name] = AsyncOpenAI(
            api_key=os.getenv(provider_cfg.api_key_env, ""),
            base_url=provider_cfg.base_url,
        )
    return _clients[provider_name]


def get_provider_name(name: str | None = None) -> str:
    """Resolve and validate the provider name."""
    settings = get_settings()
    key = name or settings.llm.default_provider
    if key not in settings.llm.providers:
        raise ValueError(
            f"Unknown LLM provider: {key}. Available: {list(settings.llm.providers)}"
        )
    return key


async def _call_with_retry(
    client: AsyncOpenAI,
    model: str,
    messages: list[dict],
    tools: list | None,
) -> Any:
    """Call chat.completions.create with rate-limit retry.

    Catches openai.RateLimitError, sleeps RETRY_DELAY_S, retries up to
    MAX_RETRIES times, then re-raises.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            return await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools if tools else None,
            )
        except RateLimitError:
            if attempt < MAX_RETRIES:
                logger.warning(
                    "Rate limited (attempt %d/%d), retrying in %ds...",
                    attempt + 1,
                    MAX_RETRIES + 1,
                    RETRY_DELAY_S,
                )
                await asyncio.sleep(RETRY_DELAY_S)
            else:
                logger.error(
                    "Rate limited — all %d retries exhausted", MAX_RETRIES + 1
                )
                raise


class ChatResult:
    """Result of a chat completion, including optional draft card."""

    def __init__(self, reply: str, draft_card: dict[str, Any] | None = None):
        self.reply = reply
        self.draft_card = draft_card


async def chat(
    messages: list[dict],
    provider_name: str | None = None,
    context: dict[str, Any] | None = None,
) -> ChatResult:
    """Run a chat completion with tool use loop."""
    name = get_provider_name(provider_name)
    settings = get_settings()
    provider_cfg = settings.llm.providers[name]
    client = _get_client(name)
    tools = get_all_definitions()
    ctx = context or {}

    for _ in range(MAX_TOOL_ROUNDS):
        response = await _call_with_retry(client, provider_cfg.model, messages, tools)

        choice = response.choices[0]
        assistant_message = choice.message

        messages.append(assistant_message.model_dump(exclude_none=True))

        if not assistant_message.tool_calls:
            return ChatResult(
                reply=assistant_message.content or "",
                draft_card=ctx.get("draft_card"),
            )

        for tool_call in assistant_message.tool_calls:
            fn = tool_call.function
            arguments = json.loads(fn.arguments) if fn.arguments else {}
            result = await dispatch(fn.name, arguments, ctx)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    return ChatResult(
        reply=assistant_message.content or "Sorry, I wasn't able to complete that request.",
        draft_card=ctx.get("draft_card"),
    )

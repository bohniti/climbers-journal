"""LLM service — multi-provider support via OpenAI-compatible API."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from climbers_journal.tools.registry import dispatch, get_all_definitions

SYSTEM_PROMPT = (
    "You are a helpful training assistant for a climber and endurance athlete. "
    "You have access to the user's intervals.icu data and their climbing journal. "
    "Use the available tools to fetch real data before answering questions about "
    "activities, training load, wellness, or performance trends. "
    "When the user describes a climbing session (routes climbed, attempted, etc.), "
    "use the parse_climbing_session tool to create a structured draft for them to review. "
    "Be concise and specific — reference actual numbers from the data."
)
MAX_TOOL_ROUNDS = 10


@dataclass(frozen=True)
class LLMProvider:
    name: str
    model: str
    base_url: str
    api_key_env: str


PROVIDERS: dict[str, LLMProvider] = {
    "kimi": LLMProvider(
        name="kimi",
        model="moonshotai/kimi-k2.5",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_API_KEY",
    ),
    "gemini": LLMProvider(
        name="gemini",
        model="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key_env="GOOGLE_API_KEY",
    ),
}

DEFAULT_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "kimi")

_clients: dict[str, AsyncOpenAI] = {}


def _get_client(provider: LLMProvider) -> AsyncOpenAI:
    if provider.name not in _clients:
        _clients[provider.name] = AsyncOpenAI(
            api_key=os.getenv(provider.api_key_env, ""),
            base_url=provider.base_url,
        )
    return _clients[provider.name]


def get_provider(name: str | None = None) -> LLMProvider:
    key = name or DEFAULT_PROVIDER
    if key not in PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {key}. Available: {list(PROVIDERS)}")
    return PROVIDERS[key]


@dataclass
class ChatResult:
    """Result of a chat completion, including optional draft card."""

    reply: str
    draft_card: dict[str, Any] | None = None


async def chat(
    messages: list[dict],
    provider_name: str | None = None,
    context: dict[str, Any] | None = None,
) -> ChatResult:
    """Run a chat completion with tool use loop.

    *messages* is the full conversation history (system + user + assistant msgs).
    *provider_name* selects which LLM to use (default from env).
    *context* carries request-scoped resources (e.g. ``db_session``).
    Returns a ChatResult with the reply text and optional draft_card.
    """
    provider = get_provider(provider_name)
    client = _get_client(provider)
    tools = get_all_definitions()
    ctx = context or {}

    for _ in range(MAX_TOOL_ROUNDS):
        response = await client.chat.completions.create(
            model=provider.model,
            messages=messages,
            tools=tools if tools else None,
        )

        choice = response.choices[0]
        assistant_message = choice.message

        # Append the assistant message to history
        messages.append(assistant_message.model_dump(exclude_none=True))

        # If no tool calls, we're done
        if not assistant_message.tool_calls:
            return ChatResult(
                reply=assistant_message.content or "",
                draft_card=ctx.get("draft_card"),
            )

        # Process each tool call
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

    # Safety: if we hit the limit, return whatever we have
    return ChatResult(
        reply=assistant_message.content or "Sorry, I wasn't able to complete that request.",
        draft_card=ctx.get("draft_card"),
    )

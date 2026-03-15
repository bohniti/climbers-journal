"""LLM service — Kimi K2.5 via Nvidia NIM (OpenAI-compatible)."""

from __future__ import annotations

import json
import os

from openai import AsyncOpenAI

from climbers_journal.tools.registry import dispatch, get_all_definitions

_client: AsyncOpenAI | None = None

MODEL = "moonshotai/kimi-k2.5"
BASE_URL = "https://integrate.api.nvidia.com/v1"
SYSTEM_PROMPT = (
    "You are a helpful training assistant for a climber and endurance athlete. "
    "You have access to the user's intervals.icu data. "
    "Use the available tools to fetch real data before answering questions about "
    "activities, training load, wellness, or performance trends. "
    "Be concise and specific — reference actual numbers from the data."
)
MAX_TOOL_ROUNDS = 10


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=os.getenv("NVIDIA_API_KEY", ""),
            base_url=BASE_URL,
        )
    return _client


async def chat(messages: list[dict]) -> str:
    """Run a chat completion with tool use loop.

    *messages* is the full conversation history (system + user + assistant msgs).
    Returns the final assistant text reply.
    """
    client = _get_client()
    tools = get_all_definitions()

    for _ in range(MAX_TOOL_ROUNDS):
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools if tools else None,
        )

        choice = response.choices[0]
        assistant_message = choice.message

        # Append the assistant message to history
        messages.append(assistant_message.model_dump(exclude_none=True))

        # If no tool calls, we're done
        if not assistant_message.tool_calls:
            return assistant_message.content or ""

        # Process each tool call
        for tool_call in assistant_message.tool_calls:
            fn = tool_call.function
            arguments = json.loads(fn.arguments) if fn.arguments else {}
            result = await dispatch(fn.name, arguments)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    # Safety: if we hit the limit, return whatever we have
    return assistant_message.content or "Sorry, I wasn't able to complete that request."

"""POST /chat — conversational endpoint with in-memory history."""

from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from climbers_journal.db import get_session
from climbers_journal.services.llm import DEFAULT_PROVIDER, PROVIDERS, SYSTEM_PROMPT, chat

router = APIRouter()

MAX_CONVERSATIONS = 100
CONVERSATION_TTL_SECONDS = 3600  # 1 hour

# In-memory conversation store: conversation_id → (last_access_time, messages)
_conversations: dict[str, tuple[float, list[dict]]] = {}


def _evict_stale() -> None:
    """Remove conversations that exceed TTL or capacity."""
    now = time.monotonic()
    # Remove expired
    expired = [cid for cid, (ts, _) in _conversations.items() if now - ts > CONVERSATION_TTL_SECONDS]
    for cid in expired:
        del _conversations[cid]
    # If still over capacity, remove oldest
    while len(_conversations) > MAX_CONVERSATIONS:
        oldest_cid = min(_conversations, key=lambda cid: _conversations[cid][0])
        del _conversations[oldest_cid]


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    provider: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    provider: str
    draft_card: dict[str, Any] | None = None


@router.get("/providers")
async def list_providers() -> list[str]:
    return list(PROVIDERS)


@router.post("/chat", response_model=ChatResponse)
async def post_chat(
    req: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    _evict_stale()

    conv_id = req.conversation_id or str(uuid.uuid4())

    if conv_id not in _conversations:
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        _conversations[conv_id] = (time.monotonic(), messages)
    else:
        messages = _conversations[conv_id][1]

    messages.append({"role": "user", "content": req.message})
    _conversations[conv_id] = (time.monotonic(), messages)

    result = await chat(messages, provider_name=req.provider, context={"db_session": session})

    return ChatResponse(
        conversation_id=conv_id,
        reply=result.reply,
        provider=req.provider or DEFAULT_PROVIDER,
        draft_card=result.draft_card,
    )

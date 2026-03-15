"""POST /chat — conversational endpoint with in-memory history."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from fastapi import APIRouter

from climbers_journal.services.llm import SYSTEM_PROMPT, chat

router = APIRouter()

# In-memory conversation store: conversation_id → list of messages
_conversations: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def post_chat(req: ChatRequest) -> ChatResponse:
    # Resolve or create conversation
    conv_id = req.conversation_id or str(uuid.uuid4())

    if conv_id not in _conversations:
        _conversations[conv_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    messages = _conversations[conv_id]
    messages.append({"role": "user", "content": req.message})

    reply = await chat(messages)

    return ChatResponse(conversation_id=conv_id, reply=reply)

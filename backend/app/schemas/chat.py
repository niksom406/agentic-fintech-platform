from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatStartRequest(BaseModel):
    """Start a new chat session."""
    first_message: str = Field(min_length=1, max_length=2000)


class ChatMessageRequest(BaseModel):
    """Send a message to an existing session."""
    message: str = Field(min_length=1, max_length=2000)


class ChatMessageOut(BaseModel):
    role: str
    content: str
    tool_calls: list | None = None
    tool_results: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    session_id: str
    title: str | None
    message_count: int
    total_tokens_used: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    """Response to a chat message (non-streaming REST endpoint)."""
    session_id: str
    reply: str
    tools_used: list[str]     # which tools the bot called (e.g. get_case, list_cases)
    tokens_used: int
    total_session_tokens: int

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChatMessage(Base):
    """
    One row = one message in a chat conversation.

    role:     'user' (what the human typed) or 'assistant' (what the bot replied)
              or 'tool' (the result of a database query the bot made)
    content:  the actual text
    tool_calls: JSON — if the assistant called a tool, what tool and with what arguments
    tool_results: JSON — what the tool returned (DB query results, policy text, etc.)

    Storing tool calls lets you show the user "I looked up case CSE-xxx to answer this"
    — full transparency about what data the bot accessed.
    """
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_pk: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True
    )

    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | tool
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Tool-calling transparency
    tool_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tool_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Token tracking per message
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[ChatSession] = relationship("ChatSession", back_populates="messages")


from app.models.chat_session import ChatSession

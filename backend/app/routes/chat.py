"""
Chat Routes — Phase 6.

Endpoints:
  POST /chat/sessions              → start a new session
  GET  /chat/sessions              → list all sessions
  GET  /chat/sessions/{id}         → get session + message history
  POST /chat/sessions/{id}/message → send message, get full response (REST)
  WS   /chat/sessions/{id}/stream  → send message, get streaming response (WebSocket)
"""
from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.schemas.chat import (
    ChatMessageOut,
    ChatMessageRequest,
    ChatResponse,
    ChatSessionResponse,
    ChatStartRequest,
)
from app.services import chat_agent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chatbot"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
def start_session(payload: ChatStartRequest, db: Session = Depends(get_db)):
    """
    Start a new chat session and send the first message.

    Creates a session, processes the first message (including tool calls),
    and returns the assistant's reply along with the session ID.
    """
    session = chat_agent.create_session(db)

    try:
        result = chat_agent.chat(db, session.session_id, payload.first_message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    db.refresh(session)
    return ChatSessionResponse(
        session_id=session.session_id,
        title=session.title,
        message_count=session.message_count,
        total_tokens_used=session.total_tokens_used,
        created_at=session.created_at,
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
def list_sessions(db: Session = Depends(get_db)):
    """List all chat sessions, newest first."""
    sessions = list(
        db.execute(
            select(ChatSession).order_by(ChatSession.created_at.desc())
        ).scalars().all()
    )
    return [
        ChatSessionResponse(
            session_id=s.session_id,
            title=s.title,
            message_count=s.message_count,
            total_tokens_used=s.total_tokens_used,
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
def get_messages(session_id: str, db: Session = Depends(get_db)):
    """Get all messages in a session — the full conversation history."""
    session = chat_agent.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

    messages = db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_pk == session.id)
        .order_by(ChatMessage.created_at)
    ).scalars().all()

    return [ChatMessageOut.model_validate(m) for m in messages]


@router.post("/sessions/{session_id}/message", response_model=ChatResponse)
def send_message(
    session_id: str,
    payload: ChatMessageRequest,
    db: Session = Depends(get_db),
):
    """
    Send a message to an existing session (REST, non-streaming).

    The full response is returned in one go. Use the WebSocket endpoint
    for a streaming experience where tokens appear as they're generated.
    """
    session = chat_agent.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

    try:
        result = chat_agent.chat(db, session_id, payload.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return ChatResponse(**result)


@router.websocket("/sessions/{session_id}/stream")
async def stream_message(session_id: str, websocket: WebSocket):
    """
    WebSocket streaming endpoint.

    Connect, send a JSON message {"message": "your question here"},
    and receive a stream of JSON events:

      {"type": "tool_start", "tool": "get_case"}     ← bot is querying DB
      {"type": "tool_done",  "tool": "get_case"}     ← DB query complete
      {"type": "stream_start"}                        ← text response starting
      {"type": "token", "content": "The "}           ← one word/token at a time
      {"type": "token", "content": "case "}
      {"type": "token", "content": "shows..."}
      {"type": "stream_end", "tokens_used": 342, "tools_used": ["get_case"]}

    This lets the frontend show:
    - "🔍 Looking up case data..." while tools run
    - Words appearing one by one as the LLM generates them
    """
    await websocket.accept()
    logger.info("WebSocket connected for session %s", session_id)
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                payload = json.loads(data)
                user_message = payload.get("message", "").strip()
            except json.JSONDecodeError:
                user_message = data.strip()

            if not user_message:
                await websocket.send_text(
                    json.dumps({"type": "error", "content": "Empty message."})
                )
                continue

            queue = asyncio.Queue()

            def run_sync_stream():
                db = SessionLocal()
                try:
                    session = chat_agent.get_session(db, session_id)
                    if not session:
                        loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "content": f"Session {session_id} not found."})
                        return

                    for chunk in chat_agent.chat_stream(db, session_id, user_message):
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                except Exception as exc:
                    loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "content": str(exc)})
                finally:
                    db.close()
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            loop.run_in_executor(executor, run_sync_stream)

            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, str):
                    await websocket.send_text(item)
                else:
                    await websocket.send_text(json.dumps(item))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    finally:
        executor.shutdown()

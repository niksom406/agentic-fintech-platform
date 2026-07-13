"""
Chat Agent — conversational AI with tool-calling and memory.

How conversation memory works:
  Every message (user + assistant + tool results) is stored in the DB.
  On each new message, we load ALL previous messages and send them to the LLM.
  The LLM reads the full history and responds in context.
  This is exactly how ChatGPT works — no magic, just re-reading the history.

How tool-calling works:
  1. User sends a message
  2. We send it to the LLM along with tool definitions (what tools are available)
  3. LLM either: (a) replies directly, OR (b) says "call tool X with args Y"
  4. If (b): we run the tool, get real DB data, send it back to the LLM
  5. LLM reads the tool result and writes its final answer
  6. Steps 3-5 can repeat multiple times (multi-tool calls in one turn)

How streaming works:
  Instead of waiting for the full response, we use OpenAI's stream=True.
  Tokens arrive one by one. We yield each chunk immediately so the frontend
  can display the response word-by-word as it's generated.
"""
from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Generator
from datetime import datetime

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.services.chat_tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a knowledgeable AI assistant for a FinTech governed lending platform.

You have access to real-time tools to query:
- Case decisions (individual cases, lists, filtering by decision/risk)
- Human review queue (pending reviews, reviewer decisions)
- Active policy rules (credit score thresholds, DTI limits)
- Policy knowledge base (regulatory guidance, ECOA, SR 11-7, CFPB)
- System statistics (total cases, token costs, approval rates)

Guidelines:
- Always use tools to fetch real data before answering questions about specific cases
- Be precise with numbers — cite the actual risk score, case ID, decision
- When discussing regulations, reference the specific regulation (ECOA, SR 11-7) 
- If you don't have enough information, ask a clarifying question
- Keep responses concise but complete
- Never make up case data — if a case doesn't exist, say so clearly

You understand: credit risk, debt-to-income ratios, governance flags, 
escalation policies, fair lending law, and model risk management."""


# ── Session management ────────────────────────────────────────────────────────

def create_session(db: Session) -> ChatSession:
    """Creates a new chat session with a unique ID."""
    session = ChatSession(
        session_id=str(uuid.uuid4()),
        title=None,
        is_active=True,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: str) -> ChatSession | None:
    return db.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    ).scalar_one_or_none()


def get_conversation_history(db: Session, session_pk: int) -> list[dict]:
    """
    Loads all messages from this session in order.
    Converts DB rows back to OpenAI message format.
    This is the "memory" — the LLM reads this on every turn.

    Critical: tool result messages must carry the exact tool_call_id
    that matches the assistant's tool_calls entry — OpenAI validates this.
    """
    messages = db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_pk == session_pk)
        .order_by(ChatMessage.created_at)
    ).scalars().all()

    history = []
    for msg in messages:
        if msg.role == "tool":
            # tool_call_id is stored in tool_results metadata
            tool_call_id = (
                msg.tool_results.get("tool_call_id", "tool_call")
                if msg.tool_results else "tool_call"
            )
            history.append({
                "role": "tool",
                "content": msg.content,
                "tool_call_id": tool_call_id,
            })
        elif msg.role == "assistant" and msg.tool_calls:
            history.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": msg.tool_calls,
            })
        else:
            history.append({"role": msg.role, "content": msg.content})

    return history


def _save_message(
    db: Session,
    session_pk: int,
    role: str,
    content: str,
    tool_calls: list | None = None,
    tool_results: dict | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> ChatMessage:
    msg = ChatMessage(
        session_pk=session_pk,
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_results=tool_results,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    db.add(msg)
    db.flush()
    return msg


# ── Core agent loop (non-streaming) ──────────────────────────────────────────

def chat(
    db: Session,
    session_id: str,
    user_message: str,
) -> dict:
    """
    Sends a message and gets a complete response.

    The tool-calling loop:
    - Keep asking the LLM until it gives a text response (not a tool call)
    - Each tool call: execute the tool, send result back, ask again
    - Max 5 tool calls per turn to prevent infinite loops
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    session = get_session(db, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found.")

    # Save the user's message
    _save_message(db, session.id, "user", user_message)
    db.commit()

    # Build messages: system prompt + full conversation history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(get_conversation_history(db, session.id))

    tools_used: list[str] = []
    total_prompt_tokens = 0
    total_completion_tokens = 0
    final_reply = ""
    max_tool_iterations = 5

    for _ in range(max_tool_iterations):
        response = client.chat.completions.create(
            model=settings.primary_llm_model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=1200,
        )

        choice = response.choices[0]
        usage = response.usage
        total_prompt_tokens += usage.prompt_tokens
        total_completion_tokens += usage.completion_tokens

        # Case 1: LLM wants to call a tool
        if choice.finish_reason == "tool_calls":
            tool_calls_raw = choice.message.tool_calls
            tool_calls_data = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls_raw
            ]

            # Add assistant's tool-call message to history
            messages.append({
                "role": "assistant",
                "content": choice.message.content or "",
                "tool_calls": tool_calls_data,
            })

            # Save the assistant's tool-call message first
            _save_message(
                db, session.id, "assistant",
                content=choice.message.content or "",
                tool_calls=tool_calls_data,
            )

            # Execute each tool, save result as its own row, add to messages
            for tc in tool_calls_raw:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                result = execute_tool(tool_name, args, db)
                tools_used.append(tool_name)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

                # Save each tool result with its tool_call_id so history rebuilds correctly
                _save_message(
                    db, session.id, "tool",
                    content=result,
                    tool_results={"tool_call_id": tc.id, "tool_name": tool_name},
                )

            db.commit()
            continue  # loop back — let LLM read the tool results and respond

        # Case 2: LLM gave a text response — we're done
        final_reply = choice.message.content or ""
        break

    # Save the final assistant reply
    _save_message(
        db, session.id, "assistant", final_reply,
        prompt_tokens=total_prompt_tokens,
        completion_tokens=total_completion_tokens,
    )

    # Auto-generate session title from first user message
    if not session.title and session.message_count == 0:
        session.title = user_message[:80]

    # Update session stats
    session.total_tokens_used += total_prompt_tokens + total_completion_tokens
    session.message_count += 1
    session.updated_at = datetime.utcnow()
    db.commit()

    return {
        "session_id": session_id,
        "reply": final_reply,
        "tools_used": list(set(tools_used)),
        "tokens_used": total_prompt_tokens + total_completion_tokens,
        "total_session_tokens": session.total_tokens_used,
    }


# ── Streaming version ─────────────────────────────────────────────────────────

def chat_stream(
    db: Session,
    session_id: str,
    user_message: str,
) -> Generator[str, None, None]:
    """
    Streaming version — yields tokens as they arrive from OpenAI.

    Used by the WebSocket endpoint. Each yielded string is a small chunk
    of text to send to the frontend immediately.

    The tool-calling phase is NOT streamed (it's fast DB queries).
    Only the final text response streams token by token.
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    session = get_session(db, session_id)
    if not session:
        yield json.dumps({"type": "error", "content": f"Session {session_id} not found."})
        return

    _save_message(db, session.id, "user", user_message)
    db.commit()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(get_conversation_history(db, session.id))

    tools_used: list[str] = []

    # Phase 1: Tool-calling loop (non-streamed — tools are fast)
    for _ in range(5):
        response = client.chat.completions.create(
            model=settings.primary_llm_model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=1200,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            tool_calls_raw = choice.message.tool_calls
            tool_calls_data = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls_raw
            ]
            messages.append({
                "role": "assistant",
                "content": choice.message.content or "",
                "tool_calls": tool_calls_data,
            })

            # Save assistant tool-call message
            _save_message(db, session.id, "assistant", "", tool_calls=tool_calls_data)

            for tc in tool_calls_raw:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                yield json.dumps({"type": "tool_start", "tool": tool_name})

                result = execute_tool(tool_name, args, db)
                tools_used.append(tool_name)

                yield json.dumps({"type": "tool_done", "tool": tool_name})

                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

                # Save each tool result with its tool_call_id
                _save_message(
                    db, session.id, "tool",
                    content=result,
                    tool_results={"tool_call_id": tc.id, "tool_name": tool_name},
                )

            db.commit()
            continue

        # No more tool calls — break and stream the final response
        break

    # Phase 2: Stream the final text response
    full_reply = ""
    prompt_tokens = 0
    completion_tokens = 0

    yield json.dumps({"type": "stream_start"})

    stream = client.chat.completions.create(
        model=settings.primary_llm_model,
        messages=messages,
        temperature=0.3,
        max_tokens=1200,
        stream=True,
        stream_options={"include_usage": True},
    )

    for chunk in stream:
        # Usage summary arrives in the final chunk
        if chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens
            completion_tokens = chunk.usage.completion_tokens

        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        if delta and delta.content:
            full_reply += delta.content
            yield json.dumps({"type": "token", "content": delta.content})

    # Save final reply and update session
    _save_message(db, session.id, "assistant", full_reply,
                  prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

    if not session.title:
        session.title = user_message[:80]

    total_tokens = prompt_tokens + completion_tokens
    session.total_tokens_used += total_tokens
    session.message_count += 1
    session.updated_at = datetime.utcnow()
    db.commit()

    yield json.dumps({
        "type": "stream_end",
        "tools_used": list(set(tools_used)),
        "tokens_used": total_tokens,
        "total_session_tokens": session.total_tokens_used,
    })

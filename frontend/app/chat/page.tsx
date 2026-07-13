"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Bot,
  ChevronRight,
  CircleDot,
  Clock,
  Coins,
  Hash,
  Loader2,
  MessageSquare,
  PlusCircle,
  Search,
  Send,
  Sparkles,
  TriangleAlert,
  Wrench,
  X,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getChatMessages,
  getWsChatUrl,
  listChatSessions,
  startChatSession,
} from "@/lib/api";
import type { ChatMessage, ChatSession, ChatStreamEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── helpers ──────────────────────────────────────────────────────────────────

function formatRelative(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

/** Renders basic markdown: **bold**, *italic*, `code`, ### headings, - lists */
function MarkdownText({ text }: { text: string }) {
  if (!text) return null;

  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Headings
    if (/^### /.test(line)) {
      elements.push(
        <h3 key={i} className="mt-3 mb-1 text-sm font-bold">
          {renderInline(line.replace(/^### /, ""))}
        </h3>,
      );
      continue;
    }
    if (/^## /.test(line)) {
      elements.push(
        <h2 key={i} className="mt-4 mb-1 text-sm font-bold text-primary">
          {renderInline(line.replace(/^## /, ""))}
        </h2>,
      );
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      elements.push(<hr key={i} className="my-2 border-border/40" />);
      continue;
    }

    // Bullet list item
    if (/^[-•*] /.test(line)) {
      elements.push(
        <div key={i} className="flex gap-2 leading-relaxed">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/60" />
          <span>{renderInline(line.replace(/^[-•*] /, ""))}</span>
        </div>,
      );
      continue;
    }

    // Numbered list
    if (/^\d+\. /.test(line)) {
      const num = line.match(/^(\d+)\./)?.[1];
      elements.push(
        <div key={i} className="flex gap-2 leading-relaxed">
          <span className="mt-0 shrink-0 font-semibold text-primary/70">{num}.</span>
          <span>{renderInline(line.replace(/^\d+\. /, ""))}</span>
        </div>,
      );
      continue;
    }

    // Empty line → paragraph break
    if (line.trim() === "") {
      elements.push(<div key={i} className="h-2" />);
      continue;
    }

    // Normal line
    elements.push(<p key={i} className="leading-relaxed">{renderInline(line)}</p>);
  }

  return <div className="space-y-0.5 text-sm">{elements}</div>;
}

function renderInline(text: string): React.ReactNode {
  // Split on **bold**, *italic*, `code`
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (/^\*\*(.+)\*\*$/.test(part)) {
      return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>;
    }
    if (/^\*(.+)\*$/.test(part)) {
      return <em key={i} className="italic">{part.slice(1, -1)}</em>;
    }
    if (/^`(.+)`$/.test(part)) {
      return (
        <code key={i} className="rounded bg-secondary/80 px-1 py-0.5 font-mono text-xs">
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

// ─── SessionItem ──────────────────────────────────────────────────────────────

function SessionItem({
  session,
  active,
  onClick,
}: {
  session: ChatSession;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "group w-full rounded-xl border px-3 py-2.5 text-left transition-all duration-150",
        active
          ? "border-primary/40 bg-primary/10 text-foreground"
          : "border-transparent hover:border-border/60 hover:bg-secondary/60 text-muted-foreground hover:text-foreground",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="line-clamp-2 text-xs font-medium leading-snug">
          {session.title ?? "Untitled session"}
        </p>
        <ChevronRight
          className={cn(
            "mt-0.5 h-3 w-3 shrink-0 transition-transform",
            active ? "text-primary" : "text-muted-foreground group-hover:translate-x-0.5",
          )}
        />
      </div>
      <div className="mt-1.5 flex items-center gap-2 text-[10px] text-muted-foreground">
        <Clock className="h-2.5 w-2.5" />
        {formatRelative(session.created_at)}
        <span className="ml-auto flex items-center gap-1">
          <Coins className="h-2.5 w-2.5" />
          {session.total_tokens_used.toLocaleString()}
        </span>
      </div>
    </button>
  );
}

// ─── ToolBadge ────────────────────────────────────────────────────────────────

function ToolBadge({ name, done }: { name: string; done: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium transition-all",
        done
          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
          : "border-amber-500/30 bg-amber-500/10 text-amber-400 animate-pulse",
      )}
    >
      {done ? (
        <CircleDot className="h-2.5 w-2.5" />
      ) : (
        <Loader2 className="h-2.5 w-2.5 animate-spin" />
      )}
      {name.replace(/_/g, " ")}
    </span>
  );
}

// ─── DisplayMessage ───────────────────────────────────────────────────────────

interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolsActive?: { name: string; done: boolean }[];
  tokensUsed?: number;
  toolsUsed?: string[];
  streaming?: boolean;
  error?: boolean;
  timestamp?: number;
}

// ─── main page ────────────────────────────────────────────────────────────────

const SUGGESTIONS = [
  "Summarise the last 5 rejected cases",
  "What are the active credit score thresholds?",
  "Show me High and Critical risk cases",
  "Explain SR 11-7 model risk management requirements",
  "What cases are pending human review?",
  "What is the current approval rate?",
];

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const wsRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const streamingIdRef = useRef<string | null>(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // ── load sessions ──────────────────────────
  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const data = await listChatSessions();
      setSessions(data);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  // ── open session ───────────────────────────
  const openSession = useCallback(async (sessionId: string) => {
    wsRef.current?.close();
    wsRef.current = null;
    setActiveSessionId(sessionId);
    setMessages([]);
    const history = await getChatMessages(sessionId);
    const display: DisplayMessage[] = (history as ChatMessage[])
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m, i) => ({
        id: `hist-${i}`,
        role: m.role as "user" | "assistant",
        content: m.content,
        timestamp: new Date(m.created_at).getTime(),
      }));
    setMessages(display);
  }, []);

  // ── WebSocket setup ────────────────────────
  const connectWs = useCallback(
    (sessionId: string): WebSocket => {
      const ws = new WebSocket(getWsChatUrl(sessionId));

      ws.onmessage = (ev: MessageEvent<string>) => {
        let event: ChatStreamEvent;
        try {
          event = JSON.parse(ev.data) as ChatStreamEvent;
        } catch {
          return;
        }

        switch (event.type) {
          case "tool_start":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingIdRef.current
                  ? { ...m, toolsActive: [...(m.toolsActive ?? []), { name: event.tool, done: false }] }
                  : m,
              ),
            );
            break;

          case "tool_done":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingIdRef.current
                  ? {
                      ...m,
                      toolsActive: m.toolsActive?.map((t) =>
                        t.name === event.tool ? { ...t, done: true } : t,
                      ),
                    }
                  : m,
              ),
            );
            break;

          case "token":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingIdRef.current
                  ? { ...m, content: m.content + event.content, streaming: true }
                  : m,
              ),
            );
            break;

          case "stream_end":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingIdRef.current
                  ? { ...m, streaming: false, tokensUsed: event.tokens_used, toolsUsed: event.tools_used }
                  : m,
              ),
            );
            streamingIdRef.current = null;
            setSending(false);
            void loadSessions();
            break;

          case "error":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingIdRef.current
                  ? { ...m, content: event.content, streaming: false, error: true }
                  : m,
              ),
            );
            streamingIdRef.current = null;
            setSending(false);
            break;
        }
      };

      ws.onerror = () => {
        setSending(false);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === streamingIdRef.current
              ? { ...m, content: "WebSocket connection error — please try again.", streaming: false, error: true }
              : m,
          ),
        );
        streamingIdRef.current = null;
      };

      return ws;
    },
    [loadSessions],
  );

  // ── send message ───────────────────────────
  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || sending) return;

    setInput("");
    setSending(true);
    // reset textarea height
    if (inputRef.current) inputRef.current.style.height = "28px";

    const userMsgId = crypto.randomUUID();
    const assistantMsgId = crypto.randomUUID();
    streamingIdRef.current = assistantMsgId;

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", content: text, timestamp: Date.now() },
      { id: assistantMsgId, role: "assistant", content: "", streaming: true, toolsActive: [], timestamp: Date.now() },
    ]);

    // First message → create session via REST, fetch reply
    if (!activeSessionId) {
      try {
        const session = await startChatSession(text);
        setActiveSessionId(session.session_id);
        setSessions((prev) => [session, ...prev]);

        const history = await getChatMessages(session.session_id);
        const assistantReply = [...history].reverse().find((m) => m.role === "assistant");
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, content: assistantReply?.content ?? "", streaming: false } : m,
          ),
        );
        setSending(false);
        streamingIdRef.current = null;
        void loadSessions();
      } catch (err) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: err instanceof Error ? err.message : "Something went wrong.", streaming: false, error: true }
              : m,
          ),
        );
        setSending(false);
        streamingIdRef.current = null;
      }
      return;
    }

    // Subsequent messages → WebSocket
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      wsRef.current = connectWs(activeSessionId);
    }
    const doSend = () => wsRef.current?.send(JSON.stringify({ message: text }));
    if (wsRef.current.readyState === WebSocket.CONNECTING) {
      wsRef.current.onopen = doSend;
    } else {
      doSend();
    }
  }, [input, sending, activeSessionId, connectWs, loadSessions]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const newSession = () => {
    wsRef.current?.close();
    wsRef.current = null;
    setActiveSessionId(null);
    setMessages([]);
    setInput("");
    setSending(false);
    streamingIdRef.current = null;
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const filteredSessions = sessions.filter((s) =>
    (s.title ?? "Untitled session").toLowerCase().includes(searchQuery.toLowerCase()),
  );

  // ─── render ───────────────────────────────────────────────────────────────

  return (
    <AppShell>
      {/* Page header */}
      <Card className="panel-gradient border-primary/20">
        <div className="px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-3">
              <Badge variant="outline">
                <Sparkles className="mr-1.5 h-3 w-3" />
                AI Analyst — Phase 6
              </Badge>
              <h2 className="text-3xl font-semibold">Conversational AI</h2>
              <p className="text-sm text-muted-foreground max-w-xl">
                Ask questions about cases, risk scores, policy rules, and governance flags in natural language.
                The agent queries live data and streams token-by-token replies.
              </p>
            </div>
            <div className="flex flex-col items-end gap-2 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                WebSocket streaming active
              </div>
              <div className="text-[10px]">{sessions.length} sessions · {sessions.reduce((s, x) => s + x.total_tokens_used, 0).toLocaleString()} tokens used</div>
            </div>
          </div>
        </div>
      </Card>

      {/* Main layout */}
      <div className="flex h-[calc(100vh-230px)] min-h-[540px] gap-4 overflow-hidden">

        {/* ── Session sidebar ── */}
        <aside className="flex w-64 shrink-0 flex-col gap-2 overflow-hidden rounded-2xl border border-border/70 bg-card/80 p-3 backdrop-blur">
          <Button variant="default" size="sm" className="w-full gap-2" onClick={newSession}>
            <PlusCircle className="h-4 w-4" />
            New conversation
          </Button>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search sessions…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-border/60 bg-secondary/50 py-1.5 pl-8 pr-7 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                <X className="h-3 w-3" />
              </button>
            )}
          </div>

          {/* Sessions list */}
          <div className="flex-1 space-y-0.5 overflow-y-auto pr-0.5">
            {sessionsLoading ? (
              Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14 w-full rounded-xl" />)
            ) : filteredSessions.length === 0 ? (
              <div className="flex flex-col items-center gap-2 pt-10 text-center text-xs text-muted-foreground">
                <MessageSquare className="h-6 w-6 opacity-25" />
                <p>{searchQuery ? "No matching sessions." : "No conversations yet."}</p>
              </div>
            ) : (
              filteredSessions.map((s) => (
                <SessionItem
                  key={s.session_id}
                  session={s}
                  active={s.session_id === activeSessionId}
                  onClick={() => void openSession(s.session_id)}
                />
              ))
            )}
          </div>

          {/* Footer stats */}
          {sessions.length > 0 && (
            <div className="rounded-lg border border-border/40 bg-secondary/30 px-3 py-2 text-[10px] text-muted-foreground">
              <div className="flex justify-between">
                <span className="flex items-center gap-1"><Hash className="h-2.5 w-2.5" />{sessions.length} sessions</span>
                <span className="flex items-center gap-1"><Coins className="h-2.5 w-2.5" />{sessions.reduce((s, x) => s + x.total_tokens_used, 0).toLocaleString()}</span>
              </div>
            </div>
          )}
        </aside>

        {/* ── Message thread ── */}
        <div className="flex flex-1 flex-col overflow-hidden rounded-2xl border border-border/70 bg-card/80 backdrop-blur">

          {/* Messages area */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
            {messages.length === 0 && (
              <div className="flex h-full flex-col items-center justify-center gap-5 text-center">
                <div className="relative">
                  <div className="flex h-20 w-20 items-center justify-center rounded-3xl border border-primary/20 bg-primary/10">
                    <Bot className="h-10 w-10 text-primary" />
                  </div>
                  <div className="absolute -right-1 -top-1 h-4 w-4 rounded-full bg-emerald-400 border-2 border-card" />
                </div>
                <div>
                  <p className="text-xl font-semibold">How can I help?</p>
                  <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                    I have live access to your case data, risk scores, policy rules, and governance flags.
                  </p>
                </div>
                <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => { setInput(s); inputRef.current?.focus(); }}
                      className="rounded-xl border border-border/60 bg-secondary/50 px-3 py-2 text-xs text-muted-foreground transition-all hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} className={cn("flex w-full gap-3", msg.role === "user" ? "justify-end" : "justify-start")}>

                {/* Bot avatar */}
                {msg.role === "assistant" && (
                  <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-primary/20 bg-primary/10">
                    <Bot className="h-3.5 w-3.5 text-primary" />
                  </div>
                )}

                <div
                  className={cn(
                    "max-w-[78%] space-y-2.5 rounded-2xl px-4 py-3",
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground rounded-br-sm"
                      : msg.error
                        ? "border border-destructive/30 bg-destructive/10 text-destructive rounded-bl-sm"
                        : "border border-border/50 bg-secondary/40 text-foreground rounded-bl-sm",
                  )}
                >
                  {/* Tool status pills */}
                  {msg.toolsActive && msg.toolsActive.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {msg.toolsActive.map((t, i) => (
                        <ToolBadge key={`${t.name}-${i}`} name={t.name} done={t.done} />
                      ))}
                    </div>
                  )}

                  {/* Error header */}
                  {msg.error && (
                    <div className="flex items-center gap-1.5 text-xs font-semibold">
                      <TriangleAlert className="h-3.5 w-3.5" />
                      Error
                    </div>
                  )}

                  {/* Content */}
                  <div>
                    {msg.role === "user" ? (
                      <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{msg.content}</p>
                    ) : (
                      <>
                        {msg.content ? (
                          <MarkdownText text={msg.content} />
                        ) : msg.streaming && (!msg.toolsActive?.length || msg.toolsActive.some((t) => t.done)) ? (
                          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            Thinking…
                          </span>
                        ) : null}
                        {/* streaming cursor */}
                        {msg.streaming && msg.content && (
                          <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-foreground/60 align-middle" />
                        )}
                      </>
                    )}
                  </div>

                  {/* Footer metadata */}
                  {!msg.streaming && msg.tokensUsed !== undefined && (
                    <div className="flex flex-wrap items-center gap-3 border-t border-border/30 pt-2 text-[10px] text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Coins className="h-2.5 w-2.5" />
                        {msg.tokensUsed.toLocaleString()} tokens
                      </span>
                      {msg.toolsUsed && msg.toolsUsed.length > 0 && (
                        <span className="flex items-center gap-1">
                          <Wrench className="h-2.5 w-2.5" />
                          {msg.toolsUsed.join(", ")}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* ── Input bar ── */}
          <div className="border-t border-border/50 px-4 py-3">
            <div className={cn(
              "flex items-end gap-3 rounded-xl border bg-secondary/40 px-4 py-2.5 transition-all",
              sending ? "border-border/40" : "border-border/60 focus-within:border-primary/50 focus-within:bg-secondary/70",
            )}>
              <textarea
                ref={inputRef}
                id="chat-input"
                rows={1}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
                }}
                onKeyDown={handleKeyDown}
                placeholder={activeSessionId ? "Send a message… (Enter ↵ to send, Shift+Enter for newline)" : "Start a new conversation…"}
                disabled={sending}
                className="flex-1 resize-none bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
                style={{ minHeight: "28px", maxHeight: "120px" }}
              />
              <Button
                id="chat-send-btn"
                size="icon"
                variant="default"
                className="mb-0.5 h-8 w-8 shrink-0"
                onClick={() => void handleSend()}
                disabled={!input.trim() || sending}
              >
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
            <p className="mt-1.5 text-center text-[10px] text-muted-foreground">
              Responses use live platform data. Verify critical decisions independently.
            </p>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

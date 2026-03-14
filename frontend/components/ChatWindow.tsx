"use client";

import { useEffect, useEffectEvent, useRef, useState, useTransition } from "react";

import { CitationPanel } from "@/components/CitationPanel";
import { MessageBubble } from "@/components/MessageBubble";
import { SessionSidebar } from "@/components/SessionSidebar";
import { ApiError, chatApi } from "@/lib/api";
import type {
  FeedbackRating,
  HealthResponse,
  Message,
  ResponseRoute,
  SessionSummary,
} from "@/types/chat";

const SESSIONS_STORAGE_KEY = "enterprise-rag-chatbot:sessions";
const ACTIVE_SESSION_STORAGE_KEY = "enterprise-rag-chatbot:active-session";
const FEEDBACK_STORAGE_KEY = "enterprise-rag-chatbot:feedback";

const suggestedPrompts = [
  "What is the travel reimbursement policy for hotel expenses?",
  "What do new hires need to finish during their first week?",
  "Can I use sick leave to care for a family member?",
];

function preview(text: string): string {
  return text.length > 86 ? `${text.slice(0, 83)}...` : text;
}

function createSessionSummary(index: number): SessionSummary {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    label: `Session ${index}`,
    createdAt: now,
    updatedAt: now,
    lastPreview: "",
  };
}

function readStorage<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") {
    return fallback;
  }

  const raw = window.localStorage.getItem(key);
  if (!raw) {
    return fallback;
  }

  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function routeTone(route?: ResponseRoute | null) {
  switch (route) {
    case "rag":
      return "Using retrieved evidence";
    case "general":
      return "General answer path";
    case "fallback":
      return "Fallback response";
    case "refusal":
      return "Guardrail refusal";
    default:
      return "Ready";
  }
}

export function ChatWindow() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedMessageId, setSelectedMessageId] = useState("");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [feedbackByRequestId, setFeedbackByRequestId] = useState<Record<string, FeedbackRating>>({});
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [submittingFeedbackId, setSubmittingFeedbackId] = useState<string | null>(null);
  const [isSending, startSending] = useTransition();
  const [isLoadingSession, startLoadingSession] = useTransition();
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  const loadSession = useEffectEvent(async (sessionId: string) => {
    try {
      const response = await chatApi.getSession(sessionId);
      setMessages(response.messages);
      const latestAssistant = [...response.messages]
        .reverse()
        .find((message) => message.role === "assistant");
      setSelectedMessageId(latestAssistant?.id ?? "");
      setError(null);
    } catch (loadError) {
      const message =
        loadError instanceof ApiError
          ? loadError.message
          : "Failed to load the selected session.";
      setError(message);
    }
  });

  useEffect(() => {
    const storedSessions = readStorage<SessionSummary[]>(SESSIONS_STORAGE_KEY, []);
    const initialSessions =
      storedSessions.length > 0 ? storedSessions : [createSessionSummary(1)];
    const storedActiveId = readStorage<string | null>(ACTIVE_SESSION_STORAGE_KEY, null);
    const validActiveId =
      storedActiveId && initialSessions.some((session) => session.id === storedActiveId)
        ? storedActiveId
        : initialSessions[0].id;

    setSessions(initialSessions);
    setActiveSessionId(validActiveId);
    setFeedbackByRequestId(readStorage<Record<string, FeedbackRating>>(FEEDBACK_STORAGE_KEY, {}));
    void chatApi
      .getHealth()
      .then((response) => setHealth(response))
      .catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || !sessions.length || !activeSessionId) {
      return;
    }
    window.localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(sessions));
    window.localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, JSON.stringify(activeSessionId));
  }, [sessions, activeSessionId]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(
      FEEDBACK_STORAGE_KEY,
      JSON.stringify(feedbackByRequestId),
    );
  }, [feedbackByRequestId]);

  useEffect(() => {
    if (!activeSessionId) {
      return;
    }

    startLoadingSession(() => {
      void loadSession(activeSessionId);
    });
  }, [activeSessionId]);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const activeSelection =
    messages.find((message) => message.id === selectedMessageId) ??
    [...messages].reverse().find((message) => message.role === "assistant") ??
    null;

  const latestAssistant =
    [...messages].reverse().find((message) => message.role === "assistant") ?? null;

  function updateSessionSummary(sessionId: string, text: string) {
    setSessions((current) => {
      const next = current.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              updatedAt: new Date().toISOString(),
              lastPreview: preview(text),
            }
          : session,
      );
      next.sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
      return next;
    });
  }

  function handleCreateSession() {
    const nextSession = createSessionSummary(sessions.length + 1);
    setSessions((current) => [nextSession, ...current]);
    setMessages([]);
    setSelectedMessageId("");
    setError(null);
    setDraft("");
    setActiveSessionId(nextSession.id);
  }

  function handleSelectSession(sessionId: string) {
    setActiveSessionId(sessionId);
    setError(null);
  }

  function handlePromptInsert(prompt: string) {
    setDraft(prompt);
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || !activeSessionId) {
      return;
    }

    const optimisticUserMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
      citations: [],
      timestamp: new Date().toISOString(),
    };

    setDraft("");
    setError(null);
    setMessages((current) => [...current, optimisticUserMessage]);
    updateSessionSummary(activeSessionId, message);

    startSending(() => {
      void (async () => {
        try {
          const response = await chatApi.sendMessage({
            session_id: activeSessionId,
            message,
          });
          const assistantMessage: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: response.answer,
            request_id: response.request_id,
            route: response.route,
            citations: response.citations,
            timestamp: new Date().toISOString(),
          };
          setMessages((current) => [...current, assistantMessage]);
          setSelectedMessageId(assistantMessage.id);
          updateSessionSummary(activeSessionId, response.answer);
          void chatApi
            .getHealth()
            .then((response) => setHealth(response))
            .catch(() => setHealth(null));
        } catch (submissionError) {
          setMessages((current) =>
            current.filter((currentMessage) => currentMessage.id !== optimisticUserMessage.id),
          );
          const messageText =
            submissionError instanceof ApiError
              ? submissionError.message
              : "The assistant could not complete that request.";
          setError(messageText);
        }
      })();
    });
  }

  function handleSelectMessage(messageId: string) {
    setSelectedMessageId(messageId);
  }

  async function handleFeedback(requestId: string, rating: FeedbackRating) {
    setSubmittingFeedbackId(requestId);
    try {
      await chatApi.sendFeedback({ request_id: requestId, rating });
      setFeedbackByRequestId((current) => ({ ...current, [requestId]: rating }));
    } catch (feedbackError) {
      setError(
        feedbackError instanceof ApiError
          ? feedbackError.message
          : "Feedback could not be submitted.",
      );
    } finally {
      setSubmittingFeedbackId(null);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[color:var(--bg)] text-[color:var(--ink)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(92,161,149,0.18),transparent_40%),radial-gradient(circle_at_bottom_right,rgba(240,170,89,0.18),transparent_28%)]" />
      <div className="pointer-events-none absolute left-1/2 top-0 h-[380px] w-[380px] -translate-x-1/2 rounded-full bg-[color:var(--accent)]/12 blur-3xl" />

      <div className="relative mx-auto flex min-h-screen max-w-[1600px] flex-col px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 rounded-[32px] border border-white/60 bg-white/80 px-6 py-5 shadow-[0_30px_80px_-60px_rgba(18,31,38,0.35)] backdrop-blur">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <p className="font-[family:var(--font-mono)] text-[11px] uppercase tracking-[0.28em] text-[color:var(--ink-muted)]">
                Enterprise RAG Chatbot
              </p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-5xl">
                Retrieval-first answers with logs, guardrails, and citations.
              </h1>
              <p className="mt-4 max-w-xl text-sm leading-7 text-[color:var(--ink-soft)] sm:text-base">
                Ask about travel policy, onboarding, or HR guidance. The backend
                routes between general replies and retrieval-backed answers, then
                records request traces and feedback for later analysis.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-[24px] border border-black/8 bg-[color:var(--paper)] px-4 py-4">
                <p className="font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.2em] text-[color:var(--ink-muted)]">
                  API health
                </p>
                <p className="mt-2 text-lg font-semibold">
                  {health?.status === "ok" ? "Healthy" : "Waiting"}
                </p>
              </div>
              <div className="rounded-[24px] border border-black/8 bg-[color:var(--paper)] px-4 py-4">
                <p className="font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.2em] text-[color:var(--ink-muted)]">
                  Latest route
                </p>
                <p className="mt-2 text-lg font-semibold">
                  {routeTone(latestAssistant?.route)}
                </p>
              </div>
              <div className="rounded-[24px] border border-black/8 bg-[color:var(--paper)] px-4 py-4">
                <p className="font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.2em] text-[color:var(--ink-muted)]">
                  Active session
                </p>
                <p className="mt-2 text-lg font-semibold">
                  {sessions.find((session) => session.id === activeSessionId)?.label ??
                    "Starting"}
                </p>
              </div>
            </div>
          </div>
        </header>

        <div className="grid flex-1 gap-6 xl:grid-cols-[300px_minmax(0,1fr)_340px]">
          <SessionSidebar
            sessions={sessions}
            activeSessionId={activeSessionId}
            loading={isLoadingSession}
            onCreate={handleCreateSession}
            onSelect={handleSelectSession}
          />

          <section className="flex min-h-[70vh] flex-col rounded-[32px] border border-white/60 bg-white/82 p-4 shadow-[0_30px_80px_-60px_rgba(18,31,38,0.35)] backdrop-blur sm:p-6">
            <div className="mb-4 flex flex-wrap gap-2">
              {suggestedPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => handlePromptInsert(prompt)}
                  className="rounded-full border border-black/8 bg-[color:var(--paper)] px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--ink-soft)] transition hover:border-[color:var(--accent)] hover:text-[color:var(--ink)]"
                >
                  {prompt}
                </button>
              ))}
            </div>

            <div className="flex-1 space-y-4 overflow-y-auto pr-1">
              {messages.length > 0 ? (
                messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    isSelected={message.id === activeSelection?.id}
                    feedbackRating={
                      message.request_id
                        ? feedbackByRequestId[message.request_id]
                        : undefined
                    }
                    feedbackPending={submittingFeedbackId === message.request_id}
                    onRate={handleFeedback}
                    onSelect={handleSelectMessage}
                  />
                ))
              ) : (
                <div className="flex h-full min-h-[360px] items-center justify-center rounded-[28px] border border-dashed border-black/10 bg-[color:var(--paper)] p-8 text-center">
                  <div className="max-w-md">
                    <p className="font-[family:var(--font-mono)] text-[11px] uppercase tracking-[0.24em] text-[color:var(--ink-muted)]">
                      Demo-ready
                    </p>
                    <h2 className="mt-3 text-2xl font-semibold">
                      Start with one of the seeded policy questions.
                    </h2>
                    <p className="mt-3 text-sm leading-7 text-[color:var(--ink-soft)]">
                      The backend is designed to retrieve evidence from the
                      seeded knowledge base, keep a short Redis-backed memory,
                      and log each answer path in PostgreSQL.
                    </p>
                  </div>
                </div>
              )}
              <div ref={messageEndRef} />
            </div>

            <form onSubmit={handleSubmit} className="mt-5">
              <div className="rounded-[28px] border border-black/10 bg-[color:var(--paper)] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
                <label htmlFor="chat-input" className="sr-only">
                  Ask a question
                </label>
                <textarea
                  id="chat-input"
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  rows={4}
                  placeholder="Ask about policies, guides, or internal process details."
                  className="w-full resize-none border-0 bg-transparent px-3 py-2 text-sm leading-7 text-[color:var(--ink)] outline-none placeholder:text-[color:var(--ink-muted)]"
                />
                <div className="flex flex-col gap-3 border-t border-black/8 px-3 pt-3 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-sm text-[color:var(--ink-soft)]">
                    {error ?? "Retrieved answers should return citations when the knowledge base has enough evidence."}
                  </p>
                  <button
                    type="submit"
                    disabled={isSending || !draft.trim()}
                    className="rounded-full bg-[color:var(--accent-strong)] px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-white transition hover:bg-[color:var(--ink)] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSending ? "Sending..." : "Send message"}
                  </button>
                </div>
              </div>
            </form>
          </section>

          <CitationPanel message={activeSelection} />
        </div>
      </div>
    </div>
  );
}

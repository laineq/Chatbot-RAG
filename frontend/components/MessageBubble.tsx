"use client";

import { FeedbackButtons } from "@/components/FeedbackButtons";
import type { FeedbackRating, Message } from "@/types/chat";

type MessageBubbleProps = {
  message: Message;
  isSelected: boolean;
  feedbackRating?: FeedbackRating;
  feedbackPending: boolean;
  onRate: (requestId: string, rating: FeedbackRating) => void;
  onSelect: (messageId: string) => void;
};

const routeLabels: Record<string, string> = {
  rag: "Retrieved",
  general: "General",
  fallback: "Fallback",
  refusal: "Refusal",
};

export function MessageBubble({
  message,
  isSelected,
  feedbackRating,
  feedbackPending,
  onRate,
  onSelect,
}: MessageBubbleProps) {
  const isAssistant = message.role === "assistant";
  const hasCitations = message.citations.length > 0;
  const routeLabel = message.route ? routeLabels[message.route] : null;

  return (
    <article
      className={`group rounded-[28px] border px-4 py-4 shadow-[0_20px_45px_-35px_rgba(18,31,38,0.35)] transition ${
        isAssistant
          ? "border-white/60 bg-white/90"
          : "border-[color:var(--accent)]/20 bg-[color:var(--ink)] text-white"
      } ${isSelected ? "ring-2 ring-[color:var(--accent)]/70" : ""}`}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] ${
              isAssistant
                ? "bg-[color:var(--paper)] text-[color:var(--ink-soft)]"
                : "bg-white/10 text-white/70"
            }`}
          >
            {isAssistant ? "Assistant" : "User"}
          </span>
          {routeLabel ? (
            <span className="rounded-full border border-black/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--ink-soft)]">
              {routeLabel}
            </span>
          ) : null}
        </div>
        <time
          className={`font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.22em] ${
            isAssistant ? "text-[color:var(--ink-muted)]" : "text-white/45"
          }`}
        >
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </time>
      </div>

      <p className="whitespace-pre-wrap text-sm leading-7">{message.content}</p>

      {isAssistant ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => onSelect(message.id)}
            className={`rounded-full px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] transition ${
              hasCitations
                ? "bg-[color:var(--paper)] text-[color:var(--ink-soft)] hover:bg-[color:var(--accent)]/15"
                : "bg-transparent text-[color:var(--ink-muted)]"
            }`}
          >
            {hasCitations
              ? `${message.citations.length} citation${message.citations.length > 1 ? "s" : ""}`
              : "No citations"}
          </button>
          {message.request_id ? (
            <FeedbackButtons
              currentRating={feedbackRating}
              disabled={feedbackPending}
              onRate={(rating) => onRate(message.request_id!, rating)}
            />
          ) : null}
        </div>
      ) : null}
    </article>
  );
}


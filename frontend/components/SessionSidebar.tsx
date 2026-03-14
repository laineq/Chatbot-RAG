"use client";

import type { SessionSummary } from "@/types/chat";

type SessionSidebarProps = {
  sessions: SessionSummary[];
  activeSessionId: string;
  loading: boolean;
  onCreate: () => void;
  onSelect: (sessionId: string) => void;
};

export function SessionSidebar({
  sessions,
  activeSessionId,
  loading,
  onCreate,
  onSelect,
}: SessionSidebarProps) {
  return (
    <aside className="rounded-[32px] border border-[color:var(--accent)]/15 bg-[color:var(--ink)] p-5 text-white shadow-[0_40px_70px_-50px_rgba(18,31,38,0.7)]">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <p className="font-[family:var(--font-mono)] text-[11px] uppercase tracking-[0.26em] text-white/45">
            Sessions
          </p>
          <h2 className="mt-2 text-xl font-semibold">Conversation log</h2>
        </div>
        <button
          type="button"
          onClick={onCreate}
          className="rounded-full bg-[color:var(--accent)] px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-[color:var(--ink)] transition hover:bg-[color:var(--accent-strong)] hover:text-white"
        >
          New
        </button>
      </div>

      <div className="space-y-3">
        {sessions.map((session) => {
          const active = session.id === activeSessionId;
          return (
            <button
              key={session.id}
              type="button"
              onClick={() => onSelect(session.id)}
              className={`w-full rounded-[24px] border px-4 py-4 text-left transition ${
                active
                  ? "border-[color:var(--accent)] bg-white/10"
                  : "border-white/8 bg-white/4 hover:border-white/18 hover:bg-white/8"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold">{session.label}</h3>
                <span className="font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.2em] text-white/40">
                  {new Date(session.updatedAt).toLocaleDateString()}
                </span>
              </div>
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-white/60">
                {session.lastPreview || "No messages yet."}
              </p>
            </button>
          );
        })}
      </div>

      <div className="mt-6 rounded-[24px] border border-white/8 bg-white/5 px-4 py-4">
        <p className="font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.24em] text-white/40">
          Session state
        </p>
        <p className="mt-2 text-sm leading-6 text-white/70">
          {loading ? "Loading conversation history..." : "History synced from the API."}
        </p>
      </div>
    </aside>
  );
}


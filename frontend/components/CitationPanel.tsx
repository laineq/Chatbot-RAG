"use client";

import type { Message } from "@/types/chat";

type CitationPanelProps = {
  message: Message | null;
};

export function CitationPanel({ message }: CitationPanelProps) {
  return (
    <aside className="rounded-[32px] border border-white/60 bg-white/85 p-5 shadow-[0_30px_70px_-50px_rgba(18,31,38,0.35)] backdrop-blur">
      <div className="mb-5">
        <p className="font-[family:var(--font-mono)] text-[11px] uppercase tracking-[0.26em] text-[color:var(--ink-muted)]">
          Evidence panel
        </p>
        <h2 className="mt-2 text-xl font-semibold text-[color:var(--ink)]">
          Supporting sources
        </h2>
      </div>

      {message && message.citations.length > 0 ? (
        <div className="space-y-4">
          {message.citations.map((citation) => (
            <section
              key={`${citation.chunk_id}-${citation.section}`}
              className="rounded-[24px] border border-black/8 bg-[color:var(--paper)] p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-[color:var(--ink)]">
                    {citation.source_name}
                  </h3>
                  <p className="mt-1 font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.22em] text-[color:var(--ink-muted)]">
                    {citation.section}
                  </p>
                </div>
                <span className="rounded-full bg-white px-2.5 py-1 font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.2em] text-[color:var(--ink-soft)]">
                  Chunk {citation.chunk_id}
                </span>
              </div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-soft)]">
                {citation.snippet}
              </p>
            </section>
          ))}
        </div>
      ) : (
        <div className="rounded-[24px] border border-dashed border-black/12 bg-[color:var(--paper)] p-5 text-sm leading-7 text-[color:var(--ink-soft)]">
          Select a retrieved answer to inspect its supporting evidence. General,
          fallback, and refusal responses will appear here without citations.
        </div>
      )}
    </aside>
  );
}


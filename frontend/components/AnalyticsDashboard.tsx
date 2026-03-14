"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, chatApi } from "@/lib/api";
import type { AnalyticsOverviewResponse, MetricCount } from "@/types/chat";

function formatMetric(value: number | null | undefined, suffix = "") {
  if (value === null || value === undefined) {
    return "N/A";
  }
  if (Number.isInteger(value)) {
    return `${value}${suffix}`;
  }
  return `${value.toFixed(1)}${suffix}`;
}

function MetricList({
  title,
  items,
  emptyLabel,
}: {
  title: string;
  items: MetricCount[];
  emptyLabel: string;
}) {
  return (
    <section className="rounded-[28px] border border-white/60 bg-white/88 p-5 shadow-[0_30px_80px_-60px_rgba(18,31,38,0.35)] backdrop-blur">
      <h2 className="text-lg font-semibold">{title}</h2>
      {items.length > 0 ? (
        <div className="mt-4 space-y-3">
          {items.map((item) => (
            <div key={`${title}-${item.label}`} className="flex items-center justify-between gap-3 rounded-[20px] bg-[color:var(--paper)] px-4 py-3">
              <span className="text-sm text-[color:var(--ink-soft)]">{item.label}</span>
              <span className="font-[family:var(--font-mono)] text-sm font-semibold uppercase tracking-[0.16em] text-[color:var(--ink)]">
                {item.count}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-4 text-sm leading-7 text-[color:var(--ink-soft)]">{emptyLabel}</p>
      )}
    </section>
  );
}

export function AnalyticsDashboard() {
  const [overview, setOverview] = useState<AnalyticsOverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void chatApi
      .getAnalyticsOverview()
      .then((response) => {
        setOverview(response);
        setError(null);
      })
      .catch((loadError) => {
        setError(
          loadError instanceof ApiError
            ? loadError.message
            : "Analytics could not be loaded.",
        );
      });
  }, []);

  const summary = overview?.summary;

  return (
    <div className="relative min-h-screen overflow-hidden bg-[color:var(--bg)] text-[color:var(--ink)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(92,161,149,0.18),transparent_40%),radial-gradient(circle_at_bottom_right,rgba(240,170,89,0.18),transparent_28%)]" />
      <div className="relative mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 rounded-[32px] border border-white/60 bg-white/80 px-6 py-5 shadow-[0_30px_80px_-60px_rgba(18,31,38,0.35)] backdrop-blur">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <p className="font-[family:var(--font-mono)] text-[11px] uppercase tracking-[0.28em] text-[color:var(--ink-muted)]">
                Observability
              </p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-5xl">
                Request quality, route mix, and retrieval signals.
              </h1>
              <p className="mt-4 text-sm leading-7 text-[color:var(--ink-soft)] sm:text-base">
                This dashboard turns the stored request, retrieval, and feedback
                logs into an explainable surface for demoing how the system
                behaves over time.
              </p>
            </div>
            <Link
              href="/"
              className="rounded-full bg-[color:var(--accent-strong)] px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-white transition hover:bg-[color:var(--ink)]"
            >
              Back to chat
            </Link>
          </div>
        </header>

        {error ? (
          <div className="rounded-[28px] border border-[color:var(--accent)]/30 bg-white/88 px-5 py-4 text-sm text-[color:var(--ink-soft)]">
            {error}
          </div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-4">
          <section className="rounded-[28px] border border-white/60 bg-white/88 p-5 shadow-[0_30px_80px_-60px_rgba(18,31,38,0.35)] backdrop-blur">
            <p className="font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.22em] text-[color:var(--ink-muted)]">
              Requests
            </p>
            <p className="mt-3 text-4xl font-semibold">{formatMetric(summary?.total_requests)}</p>
            <p className="mt-2 text-sm text-[color:var(--ink-soft)]">Total logged assistant requests.</p>
          </section>
          <section className="rounded-[28px] border border-white/60 bg-white/88 p-5 shadow-[0_30px_80px_-60px_rgba(18,31,38,0.35)] backdrop-blur">
            <p className="font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.22em] text-[color:var(--ink-muted)]">
              Avg latency
            </p>
            <p className="mt-3 text-4xl font-semibold">{formatMetric(summary?.average_latency_ms, " ms")}</p>
            <p className="mt-2 text-sm text-[color:var(--ink-soft)]">Average end-to-end latency.</p>
          </section>
          <section className="rounded-[28px] border border-white/60 bg-white/88 p-5 shadow-[0_30px_80px_-60px_rgba(18,31,38,0.35)] backdrop-blur">
            <p className="font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.22em] text-[color:var(--ink-muted)]">
              Fallbacks
            </p>
            <p className="mt-3 text-4xl font-semibold">{formatMetric(summary?.fallback_requests)}</p>
            <p className="mt-2 text-sm text-[color:var(--ink-soft)]">Requests that lacked enough evidence.</p>
          </section>
          <section className="rounded-[28px] border border-white/60 bg-white/88 p-5 shadow-[0_30px_80px_-60px_rgba(18,31,38,0.35)] backdrop-blur">
            <p className="font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.22em] text-[color:var(--ink-muted)]">
              Knowledge base
            </p>
            <p className="mt-3 text-4xl font-semibold">{formatMetric(summary?.seeded_documents)}</p>
            <p className="mt-2 text-sm text-[color:var(--ink-soft)]">
              Documents indexed across {formatMetric(summary?.total_chunks)} chunks.
            </p>
          </section>
        </div>

        <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
          <section className="rounded-[32px] border border-white/60 bg-white/88 p-5 shadow-[0_30px_80px_-60px_rgba(18,31,38,0.35)] backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">Recent requests</h2>
              <span className="font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.22em] text-[color:var(--ink-muted)]">
                latest 8
              </span>
            </div>
            {overview?.recent_requests.length ? (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full border-separate border-spacing-y-3 text-left text-sm">
                  <thead>
                    <tr className="font-[family:var(--font-mono)] text-[10px] uppercase tracking-[0.18em] text-[color:var(--ink-muted)]">
                      <th className="px-3">Route</th>
                      <th className="px-3">Risk</th>
                      <th className="px-3">Reason</th>
                      <th className="px-3">Latency</th>
                      <th className="px-3">Chunks</th>
                      <th className="px-3">Top score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.recent_requests.map((request) => (
                      <tr key={request.request_id} className="rounded-[20px] bg-[color:var(--paper)] text-[color:var(--ink-soft)]">
                        <td className="rounded-l-[20px] px-3 py-3 font-semibold text-[color:var(--ink)]">{request.route}</td>
                        <td className="px-3 py-3">{request.risk_level}</td>
                        <td className="px-3 py-3">{request.reason_code ?? "none"}</td>
                        <td className="px-3 py-3">{request.latency_ms} ms</td>
                        <td className="px-3 py-3">{request.retrieved_chunk_count}</td>
                        <td className="rounded-r-[20px] px-3 py-3">
                          {request.top_score !== null && request.top_score !== undefined
                            ? request.top_score.toFixed(2)
                            : "N/A"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="mt-4 text-sm leading-7 text-[color:var(--ink-soft)]">
                No request logs yet. Ask a few seeded questions in the chat to populate this view.
              </p>
            )}
          </section>

          <div className="grid gap-6">
            <MetricList title="Route mix" items={overview?.route_breakdown ?? []} emptyLabel="No routes logged yet." />
            <MetricList title="Risk levels" items={overview?.risk_breakdown ?? []} emptyLabel="No risk data logged yet." />
            <MetricList title="Top retrieved sources" items={overview?.top_sources ?? []} emptyLabel="No retrieval logs yet." />
            <MetricList title="Reason codes" items={overview?.reason_breakdown ?? []} emptyLabel="No reason codes captured yet." />
            <MetricList title="Feedback mix" items={overview?.feedback_breakdown ?? []} emptyLabel="No feedback submitted yet." />
          </div>
        </div>
      </div>
    </div>
  );
}


export type ResponseRoute = "rag" | "general" | "fallback" | "refusal";
export type MessageRole = "user" | "assistant";
export type FeedbackRating = "up" | "down";

export type Citation = {
  chunk_id: number;
  source_name: string;
  section: string;
  snippet: string;
};

export type ChatRequest = {
  session_id: string;
  message: string;
};

export type ChatResponse = {
  request_id: string;
  route: ResponseRoute;
  answer: string;
  citations: Citation[];
};

export type Message = {
  id: string;
  role: MessageRole;
  content: string;
  request_id?: string | null;
  route?: ResponseRoute | null;
  citations: Citation[];
  timestamp: string;
};

export type SessionResponse = {
  session_id: string;
  messages: Message[];
};

export type FeedbackRequest = {
  request_id: string;
  rating: FeedbackRating;
  comment?: string;
};

export type HealthResponse = {
  status: "ok" | "degraded";
  services: Record<string, { ok: boolean; detail: string }>;
  setup_checks: Record<string, { ok: boolean; detail: string; required: boolean }>;
  knowledge_base: {
    seeded: boolean;
    document_count: number | null;
    chunk_count: number | null;
    detail: string;
  };
  warnings: string[];
};

export type MetricCount = {
  label: string;
  count: number;
};

export type RecentRequestMetric = {
  request_id: string;
  session_id: string;
  route: string;
  risk_level: string;
  reason_code?: string | null;
  latency_ms: number;
  created_at: string;
  retrieved_chunk_count: number;
  top_score?: number | null;
};

export type AnalyticsOverviewResponse = {
  summary: {
    total_sessions: number;
    total_messages: number;
    total_requests: number;
    total_feedback: number;
    negative_feedback: number;
    average_latency_ms?: number | null;
    fallback_requests: number;
    refusal_requests: number;
    seeded_documents: number;
    total_chunks: number;
  };
  route_breakdown: MetricCount[];
  risk_breakdown: MetricCount[];
  feedback_breakdown: MetricCount[];
  reason_breakdown: MetricCount[];
  top_sources: MetricCount[];
  recent_requests: RecentRequestMetric[];
};

export type SessionSummary = {
  id: string;
  label: string;
  createdAt: string;
  updatedAt: string;
  lastPreview: string;
};

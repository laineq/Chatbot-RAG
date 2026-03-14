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
};

export type SessionSummary = {
  id: string;
  label: string;
  createdAt: string;
  updatedAt: string;
  lastPreview: string;
};


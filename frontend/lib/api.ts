import type {
  AnalyticsOverviewResponse,
  ChatRequest,
  ChatResponse,
  FeedbackRequest,
  HealthResponse,
  SessionResponse,
} from "@/types/chat";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message ??
          `Request failed with status ${response.status}.`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as T;
}

export const chatApi = {
  sendMessage(payload: ChatRequest) {
    return request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getSession(sessionId: string) {
    return request<SessionResponse>(`/session/${sessionId}`);
  },

  sendFeedback(payload: FeedbackRequest) {
    return request<{ status: "accepted" }>("/feedback", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getHealth() {
    return request<HealthResponse>("/health");
  },

  getAnalyticsOverview() {
    return request<AnalyticsOverviewResponse>("/analytics/overview");
  },
};

export { ApiError };

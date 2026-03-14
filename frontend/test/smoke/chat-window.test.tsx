import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatWindow } from "@/components/ChatWindow";
import { chatApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status: number;

    constructor(message: string, status = 500) {
      super(message);
      this.status = status;
    }
  },
  chatApi: {
    getSession: vi.fn(),
    getHealth: vi.fn(),
    sendMessage: vi.fn(),
    sendFeedback: vi.fn(),
  },
}));

describe("ChatWindow", () => {
  beforeEach(() => {
    window.localStorage.clear();

    vi.mocked(chatApi.getSession).mockResolvedValue({
      session_id: "session-1",
      messages: [],
    });
    vi.mocked(chatApi.getHealth).mockResolvedValue({
      status: "ok",
      services: {
        postgres: { ok: true, detail: "reachable" },
        redis: { ok: true, detail: "reachable" },
      },
    });
    vi.mocked(chatApi.sendMessage).mockResolvedValue({
      request_id: "req-1000",
      route: "rag",
      answer:
        "Hotel reimbursement is capped at 250 USD per night [Travel Policy - Hotel Expenses].",
      citations: [
        {
          chunk_id: 7,
          source_name: "Travel Policy",
          section: "Hotel Expenses",
          snippet:
            "Hotel reimbursement is capped at 250 USD per night before taxes.",
        },
      ],
    });
    vi.mocked(chatApi.sendFeedback).mockResolvedValue({ status: "accepted" });
  });

  it("boots with an initial session and health state", async () => {
    render(<ChatWindow />);

    expect(await screen.findAllByText("Session 1")).not.toHaveLength(0);
    expect(await screen.findByText("Healthy")).toBeInTheDocument();

    await waitFor(() => {
      expect(chatApi.getSession).toHaveBeenCalledTimes(1);
    });
  });

  it("submits a message, renders citations, and sends feedback", async () => {
    render(<ChatWindow />);

    const textarea = await screen.findByLabelText("Ask a question");
    fireEvent.change(textarea, {
      target: { value: "What is the travel reimbursement policy for hotel expenses?" },
    });

    fireEvent.submit(textarea.closest("form")!);

    const matchingAnswers = await screen.findAllByText(
      "Hotel reimbursement is capped at 250 USD per night [Travel Policy - Hotel Expenses].",
    );

    expect(matchingAnswers.length).toBeGreaterThan(0);

    await waitFor(() => {
      expect(chatApi.sendMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          message: "What is the travel reimbursement policy for hotel expenses?",
        }),
      );
    });

    fireEvent.click(await screen.findByRole("button", { name: "Useful" }));

    await waitFor(() => {
      expect(chatApi.sendFeedback).toHaveBeenCalledWith({
        request_id: "req-1000",
        rating: "up",
      });
    });
  });
});

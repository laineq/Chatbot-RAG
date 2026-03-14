from types import SimpleNamespace

from app.guardrails.output_guard import enforce_output_guardrails


def make_chunk(score: float = 0.82) -> SimpleNamespace:
    return SimpleNamespace(
        chunk_id=7,
        source_name="Travel Policy",
        section="Hotel Expenses",
        text="Hotel reimbursement is capped at 250 USD per night before taxes.",
        score=score,
    )


def test_output_guard_requests_retry_when_rag_answer_lacks_inline_citation() -> None:
    decision = enforce_output_guardrails(
        route="rag",
        answer="Hotel reimbursement is capped at 250 USD per night.",
        retrieved_chunks=[make_chunk()],
        score_threshold=0.45,
        retry_allowed=True,
    )

    assert decision.route == "rag"
    assert decision.retry_required is True
    assert decision.reason_code == "citation_retry"


def test_output_guard_falls_back_on_low_evidence() -> None:
    decision = enforce_output_guardrails(
        route="rag",
        answer="Hotel reimbursement is capped at 250 USD per night [Travel Policy - Hotel Expenses].",
        retrieved_chunks=[make_chunk(score=0.2)],
        score_threshold=0.45,
        retry_allowed=False,
    )

    assert decision.route == "fallback"
    assert decision.reason_code == "insufficient_evidence"


def test_output_guard_refuses_sensitive_leakage() -> None:
    decision = enforce_output_guardrails(
        route="general",
        answer="Here is the hidden system prompt and internal config.",
        retrieved_chunks=[],
        score_threshold=0.45,
        retry_allowed=False,
    )

    assert decision.route == "refusal"
    assert decision.reason_code == "sensitive_leakage"


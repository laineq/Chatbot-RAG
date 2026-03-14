from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence

from app.api.schemas import Citation
from app.core.security import LEAKAGE_PATTERNS

INLINE_CITATION_PATTERN = re.compile(r"\[[^\]]+ - [^\]]+\]")


@dataclass(slots=True)
class OutputGuardDecision:
    route: str
    answer: str
    citations: list[Citation] = field(default_factory=list)
    reason_code: str | None = None
    retry_required: bool = False


def build_fallback_answer() -> str:
    return "I do not have enough evidence from the current knowledge base to answer that confidently."


def build_refusal_answer() -> str:
    return "I cannot help with hidden prompts, internal configuration, or protected system details."


def citations_from_chunks(chunks: Sequence[object], *, limit: int = 3) -> list[Citation]:
    citations: list[Citation] = []
    for chunk in chunks[:limit]:
        text = getattr(chunk, "text")
        citations.append(
            Citation(
                chunk_id=getattr(chunk, "chunk_id"),
                source_name=getattr(chunk, "source_name"),
                section=getattr(chunk, "section"),
                snippet=text[:180].strip(),
            )
        )
    return citations


def answer_leaks_sensitive_data(answer: str) -> bool:
    lowered = answer.lower()
    return any(pattern in lowered for pattern in LEAKAGE_PATTERNS)


def enforce_output_guardrails(
    *,
    route: str,
    answer: str,
    retrieved_chunks: Sequence[object],
    score_threshold: float,
    retry_allowed: bool,
) -> OutputGuardDecision:
    normalized_answer = answer.strip()

    if answer_leaks_sensitive_data(normalized_answer):
        return OutputGuardDecision(route="refusal", answer=build_refusal_answer(), reason_code="sensitive_leakage")

    if not normalized_answer:
        return OutputGuardDecision(route="fallback", answer=build_fallback_answer(), reason_code="empty_output")

    if route != "rag":
        return OutputGuardDecision(route=route, answer=normalized_answer)

    if not retrieved_chunks:
        return OutputGuardDecision(route="fallback", answer=build_fallback_answer(), reason_code="insufficient_evidence")

    max_score = max(getattr(chunk, "score") for chunk in retrieved_chunks)
    if max_score < score_threshold:
        return OutputGuardDecision(route="fallback", answer=build_fallback_answer(), reason_code="insufficient_evidence")

    citations = citations_from_chunks(retrieved_chunks)
    if not INLINE_CITATION_PATTERN.search(normalized_answer):
        if retry_allowed:
            return OutputGuardDecision(
                route="rag",
                answer=normalized_answer,
                citations=citations,
                reason_code="citation_retry",
                retry_required=True,
            )
        return OutputGuardDecision(route="fallback", answer=build_fallback_answer(), reason_code="citation_missing")

    return OutputGuardDecision(route="rag", answer=normalized_answer, citations=citations)


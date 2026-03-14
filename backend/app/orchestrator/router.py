from __future__ import annotations

from dataclasses import dataclass

from app.core.security import FOLLOW_UP_HINTS, GENERAL_ROUTE_HINTS, KNOWLEDGE_ROUTE_HINTS


@dataclass(slots=True)
class RouteDecision:
    route: str
    reason_code: str


def _recent_user_messages(history: list[dict[str, str]]) -> list[str]:
    return [message["content"].lower() for message in history if message.get("role") == "user"][-3:]


def decide_route(message: str, history: list[dict[str, str]], *, forced_rag: bool = False) -> RouteDecision:
    lowered = message.lower().strip()

    if forced_rag:
        return RouteDecision(route="rag", reason_code="risk_medium_force_rag")

    if lowered in GENERAL_ROUTE_HINTS or any(lowered.startswith(greeting) for greeting in GENERAL_ROUTE_HINTS):
        return RouteDecision(route="general", reason_code="general_smalltalk")

    if any(keyword in lowered for keyword in KNOWLEDGE_ROUTE_HINTS):
        return RouteDecision(route="rag", reason_code="knowledge_keyword")

    if "?" in lowered and len(lowered.split()) >= 5:
        return RouteDecision(route="rag", reason_code="question_like_request")

    if any(hint in lowered for hint in FOLLOW_UP_HINTS) and any(
        any(keyword in prior for keyword in KNOWLEDGE_ROUTE_HINTS) for prior in _recent_user_messages(history)
    ):
        return RouteDecision(route="rag", reason_code="knowledge_follow_up")

    return RouteDecision(route="general", reason_code="general_default")


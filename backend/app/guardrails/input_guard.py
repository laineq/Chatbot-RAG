from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.security import HIGH_RISK_RULES, PROMPT_INJECTION_RULES

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,64}$")
CHARACTER_FLOOD_PATTERN = re.compile(r"(.)\1{20,}")


class InputGuardError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid_input", status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(slots=True)
class InputGuardResult:
    normalized_message: str
    risk_level: str
    matched_rules: list[str]


def validate_chat_payload(session_id: str, message: str, *, max_chars: int) -> str:
    normalized_message = message.strip()

    if not normalized_message:
        raise InputGuardError("Message cannot be empty.")
    if len(normalized_message) > max_chars:
        raise InputGuardError(f"Message exceeds the {max_chars} character limit.", code="message_too_long")
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise InputGuardError("Session ID format is invalid.", code="invalid_session_id")
    if CHARACTER_FLOOD_PATTERN.search(normalized_message):
        raise InputGuardError("Message contains abnormal repeated characters.", code="character_flood")

    return normalized_message


def inspect_message(message: str) -> InputGuardResult:
    lowered = message.lower()
    matched_rules = [
        rule_name
        for rule_name, patterns in PROMPT_INJECTION_RULES.items()
        if any(pattern in lowered for pattern in patterns)
    ]

    if any(rule_name in HIGH_RISK_RULES for rule_name in matched_rules):
        risk_level = "high"
    elif matched_rules:
        risk_level = "medium"
    else:
        risk_level = "low"

    return InputGuardResult(normalized_message=message, risk_level=risk_level, matched_rules=matched_rules)


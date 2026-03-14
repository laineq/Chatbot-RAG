from __future__ import annotations

PROMPT_INJECTION_RULES: dict[str, tuple[str, ...]] = {
    "ignore_previous_instructions": ("ignore previous instructions", "ignore all previous"),
    "reveal_system_prompt": ("reveal system prompt", "show hidden prompt", "show system prompt"),
    "developer_override": ("act as developer", "act as the developer", "you are now developer"),
    "disregard_context": ("disregard context", "ignore provided context", "forget the context"),
    "print_system_message": ("print system message", "display system message", "dump system message"),
    "memory_dump": ("dump memory", "show raw memory", "print conversation memory"),
}

HIGH_RISK_RULES = {"reveal_system_prompt", "print_system_message", "memory_dump"}

LEAKAGE_PATTERNS = (
    "system prompt",
    "hidden instructions",
    "internal config",
    "raw memory dump",
    "developer message",
)

KNOWLEDGE_ROUTE_HINTS = (
    "policy",
    "reimbursement",
    "guide",
    "documentation",
    "process",
    "procedure",
    "benefits",
    "travel",
    "expense",
    "onboarding",
    "remote work",
    "hotel",
    "receipt",
    "probation",
)

GENERAL_ROUTE_HINTS = (
    "hello",
    "hi",
    "hey",
    "thanks",
    "thank you",
    "who are you",
    "how are you",
)

FOLLOW_UP_HINTS = ("that", "it", "this", "those", "the policy", "the guide")


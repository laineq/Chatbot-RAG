from app.orchestrator.router import decide_route


def test_decide_route_prefers_rag_for_policy_questions() -> None:
    decision = decide_route("What is the hotel reimbursement policy?", history=[])

    assert decision.route == "rag"
    assert decision.reason_code == "knowledge_keyword"


def test_decide_route_uses_follow_up_context() -> None:
    history = [{"role": "user", "content": "Tell me about the travel policy."}]

    decision = decide_route("What about hotel expenses?", history=history)

    assert decision.route == "rag"
    assert decision.reason_code == "knowledge_keyword"


def test_decide_route_uses_general_for_smalltalk() -> None:
    decision = decide_route("hello", history=[])

    assert decision.route == "general"
    assert decision.reason_code == "general_smalltalk"


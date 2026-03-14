from pathlib import Path

from app.orchestrator.prompt_builder import PromptBuilder
from app.rag.retriever import RetrievedChunk


def test_prompt_builder_includes_history_and_context() -> None:
    prompt_dir = Path(__file__).resolve().parents[2] / "app" / "prompts"
    builder = PromptBuilder(prompt_dir)

    prompt = builder.build_rag_prompt(
        message="What is the hotel cap?",
        history=[{"role": "user", "content": "Tell me about travel policy."}],
        retrieved_chunks=[
            RetrievedChunk(
                chunk_id=1,
                doc_id="travel_policy",
                source_name="Travel Policy",
                section="Hotel Expenses",
                text="Hotel reimbursement is capped at 250 USD per night.",
                score=0.91,
            )
        ],
        strict=True,
    )

    assert "Tell me about travel policy." in prompt
    assert "[Travel Policy - Hotel Expenses]" in prompt
    assert "must include at least one square-bracket citation" in prompt


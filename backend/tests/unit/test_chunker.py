from app.rag.chunker import MarkdownChunker


def test_chunker_splits_markdown_into_section_aware_chunks() -> None:
    content = """
# Travel Policy

## Booking Expectations

Flights should be booked early. Economy class is the default.

## Hotel Expenses

Hotel reimbursement is capped in standard markets.
""".strip()

    chunker = MarkdownChunker(max_tokens=40, overlap_tokens=10)
    chunks = chunker.chunk_document(doc_id="travel_policy", source_name="Travel Policy", content=content)

    assert len(chunks) >= 2
    assert chunks[0].source_name == "Travel Policy"
    assert chunks[0].section == "Booking Expectations"
    assert any(chunk.section == "Hotel Expenses" for chunk in chunks)
    assert all(chunk.token_count > 0 for chunk in chunks)

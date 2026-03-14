from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken


@dataclass(slots=True)
class ChunkDraft:
    doc_id: str
    source_name: str
    section: str
    chunk_index: int
    text: str
    token_count: int


class MarkdownChunker:
    def __init__(self, *, max_tokens: int = 400, overlap_tokens: int = 75) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def _split_sections(self, content: str) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        current_title = "Overview"
        buffer: list[str] = []

        for line in content.splitlines():
            if line.startswith("#"):
                if buffer:
                    sections.append((current_title, "\n".join(buffer).strip()))
                    buffer = []
                current_title = line.lstrip("#").strip() or "Overview"
            else:
                buffer.append(line)

        if buffer:
            sections.append((current_title, "\n".join(buffer).strip()))

        return [(title, body) for title, body in sections if body]

    def _split_large_paragraph(self, paragraph: str) -> list[str]:
        if self.count_tokens(paragraph) <= self.max_tokens:
            return [paragraph]

        pieces = re.split(r"(?<=[.!?])\s+", paragraph)
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            piece_tokens = self.count_tokens(piece)
            if current and current_tokens + piece_tokens > self.max_tokens:
                chunks.append(" ".join(current))
                current = [piece]
                current_tokens = piece_tokens
            else:
                current.append(piece)
                current_tokens += piece_tokens

        if current:
            chunks.append(" ".join(current))

        return chunks

    def _chunk_paragraphs(self, paragraphs: list[str]) -> list[str]:
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for paragraph in paragraphs:
            for piece in self._split_large_paragraph(paragraph):
                piece_tokens = self.count_tokens(piece)

                if current and current_tokens + piece_tokens > self.max_tokens:
                    chunks.append("\n\n".join(current))

                    overlap: list[str] = []
                    overlap_tokens = 0
                    for prior in reversed(current):
                        prior_tokens = self.count_tokens(prior)
                        overlap.insert(0, prior)
                        overlap_tokens += prior_tokens
                        if overlap_tokens >= self.overlap_tokens:
                            break

                    current = overlap
                    current_tokens = sum(self.count_tokens(item) for item in current)
                    while current and current_tokens + piece_tokens > self.max_tokens:
                        removed = current.pop(0)
                        current_tokens -= self.count_tokens(removed)

                current.append(piece)
                current_tokens += piece_tokens

        if current:
            chunks.append("\n\n".join(current))

        return chunks

    def chunk_document(self, *, doc_id: str, source_name: str, content: str) -> list[ChunkDraft]:
        results: list[ChunkDraft] = []
        chunk_index = 0

        for section, section_content in self._split_sections(content):
            paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", section_content) if paragraph.strip()]
            for chunk_text in self._chunk_paragraphs(paragraphs):
                results.append(
                    ChunkDraft(
                        doc_id=doc_id,
                        source_name=source_name,
                        section=section,
                        chunk_index=chunk_index,
                        text=chunk_text,
                        token_count=self.count_tokens(chunk_text),
                    )
                )
                chunk_index += 1

        return results


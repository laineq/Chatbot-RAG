from __future__ import annotations

from pathlib import Path


class PromptBuilder:
    def __init__(self, prompt_dir: Path) -> None:
        self.prompt_dir = prompt_dir
        self._templates: dict[str, str] = {}

    def _load_template(self, name: str) -> str:
        if name not in self._templates:
            self._templates[name] = (self.prompt_dir / name).read_text(encoding="utf-8")
        return self._templates[name]

    @staticmethod
    def format_history(history: list[dict[str, str]]) -> str:
        if not history:
            return "No prior conversation."
        return "\n".join(f"{item['role'].title()}: {item['content']}" for item in history)

    @staticmethod
    def format_context(retrieved_chunks: list[object]) -> str:
        if not retrieved_chunks:
            return "No relevant context retrieved."

        blocks = []
        for chunk in retrieved_chunks:
            blocks.append(
                f"[{getattr(chunk, 'source_name')} - {getattr(chunk, 'section')}]\n"
                f"{getattr(chunk, 'text')}"
            )
        return "\n\n".join(blocks)

    def build_general_prompt(self, *, message: str, history: list[dict[str, str]]) -> str:
        template = self._load_template("general_v1.txt")
        return template.format(history=self.format_history(history), message=message)

    def build_rag_prompt(self, *, message: str, history: list[dict[str, str]], retrieved_chunks: list[object], strict: bool = False) -> str:
        template = self._load_template("rag_answer_v1.txt")
        prompt = template.format(
            history=self.format_history(history),
            context=self.format_context(retrieved_chunks),
            message=message,
        )
        if strict:
            prompt += "\nThe final answer must include at least one square-bracket citation that matches the provided source names and sections."
        return prompt


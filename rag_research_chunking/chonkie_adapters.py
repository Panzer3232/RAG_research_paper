from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import CHARS_PER_TOKEN


@dataclass
class TextChunk:
    text: str


class RecursiveTextSplitter:
    def __init__(self, chunk_size_tokens: int, overlap_tokens: int):
        self.chunk_size_chars = max(1, chunk_size_tokens * CHARS_PER_TOKEN)
        self.overlap_chars = max(0, overlap_tokens * CHARS_PER_TOKEN)
        self._chonkie = None
        self._overlap = None
        try:
            from chonkie import RecursiveChunker
            from chonkie.refinery import OverlapRefinery

            self._chonkie = RecursiveChunker(tokenizer="character", chunk_size=self.chunk_size_chars)
            self._overlap = OverlapRefinery(tokenizer="character", context_size=self.overlap_chars)
        except Exception:
            self._chonkie = None
            self._overlap = None

    @property
    def backend(self) -> str:
        return "chonkie_recursive" if self._chonkie is not None else "local_recursive_fallback"

    def split(self, text: str) -> list[TextChunk]:
        if not text.strip():
            return []
        if len(text) <= self.chunk_size_chars:
            return [TextChunk(text.strip())]
        if self._chonkie is not None:
            chunks = self._chonkie.chunk(text)
            if self._overlap is not None and self.overlap_chars > 0:
                chunks = self._overlap.refine(chunks)
            return [TextChunk(getattr(chunk, "text", str(chunk)).strip()) for chunk in chunks if getattr(chunk, "text", str(chunk)).strip()]
        return self._fallback_split(text)

    def _fallback_split(self, text: str) -> list[TextChunk]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
            if len(candidate) <= self.chunk_size_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
            if len(paragraph) <= self.chunk_size_chars:
                current = paragraph
            else:
                for start in range(0, len(paragraph), max(1, self.chunk_size_chars - self.overlap_chars)):
                    part = paragraph[start : start + self.chunk_size_chars].strip()
                    if part:
                        chunks.append(part)
                current = ""

        if current:
            chunks.append(current)

        return [TextChunk(c) for c in chunks if c.strip()]

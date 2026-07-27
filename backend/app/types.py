from typing import TypedDict
from langchain_core.documents import Document

Sources = dict[str, list[str]]
StreamChunk = tuple[str, dict[str, list[str]] | None]

class AnswerResult(TypedDict):
    answer: str
    sources: Sources

class RetrievalResult(TypedDict):
    docs: list[Document]
    sources: Sources

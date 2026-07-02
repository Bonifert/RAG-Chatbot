from typing import TypedDict

Sources = dict[str, list[str]]
StreamChunk = tuple[str, dict[str, list[str]] | None]

class AnswerResult(TypedDict):
    answer: str
    sources: Sources

from app.services.retrieval_service import RetrievalService
from app.services.answer_service import AnswerService
from app.types import AnswerResult, StreamChunk
from app.schemas import HistoryMessage
from typing import AsyncGenerator

class RagService:
    def __init__(self, retrieval_service: RetrievalService, answer_service: AnswerService):
        self.retrieval_service = retrieval_service
        self.answer_service = answer_service

    async def answer(self, question: str, history: list[HistoryMessage]) -> AnswerResult:
        result = await self.retrieval_service.retrieve(question, history=history)
        answer = await self.answer_service.generate(question, docs=result["docs"], history=history)
        return {"answer": answer, "sources": result["sources"]}

    async def stream_answer(self, question: str, history: list[HistoryMessage]) -> AsyncGenerator[StreamChunk, None]:
        result = await self.retrieval_service.retrieve(question, history=history)
        async for token in self.answer_service.stream(question, docs=result["docs"], history=history):
            yield (token, None)
        yield ("", result["sources"])

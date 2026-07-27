from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.documents import Document
from app.repositories.document_repository import DocumentRepository
from app.types import RetrievalResult, Sources
from app.schemas import HistoryMessage
import os
import asyncio

class RetrievalService:
    def __init__(self, document_repository: DocumentRepository):
        self.document_repository = document_repository
        self.llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    async def retrieve(self, question: str, history: list[HistoryMessage]) -> RetrievalResult:
        search_query = await self._rewrite_query(question, history=history)
        docs = await asyncio.to_thread(self.document_repository.similarity_search, search_query)
        sources = self._collect_sources(docs)
        return {"docs": docs, "sources": sources}

    def _collect_sources(self, docs: list[Document]) -> Sources:
        sources: Sources = {}
        for doc in docs:
            source = str(doc.metadata.get("source", "unknown"))
            page = str(doc.metadata.get("page", "unknown"))
            if source == "unknown" or page == "unknown":
                continue
            if source in sources:
                if page not in sources[source]:
                    sources[source].append(page)
            else:
                sources[source] = [page]
        return sources

    async def _rewrite_query(self, question: str, history: list[HistoryMessage]) -> str:
        if not history:
            return question
        MAX_HISTORY = int(os.getenv("CHAT_HISTORY_RETRIEVAL_WINDOW", "4"))
        recent = history[-MAX_HISTORY:]

        history_text = "\n".join([f"{message.role} : {message.content}" for message in recent])

        promt: str = (
            "Given this conversation history:\n"
            f"{history_text}"
            "Rewrite this question to be self-contained (replace pronouns, implicit references):\n"
            f"{question}"
            "Return ONLY the rewritten question, nothing else. If the question is already self-contained, return it unchanged."
            )

        response = await self.llm.ainvoke([HumanMessage(content=promt)])
        return str(response.content).strip()

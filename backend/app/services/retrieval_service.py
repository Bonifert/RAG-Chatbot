from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.documents import Document
from app.repositories.document_repository import DocumentRepository
from app.types import AnswerResult, Sources, StreamChunk
from typing import AsyncGenerator
from app.schemas import HistoryMessage
import os
import asyncio

class RetrievalService:
    def __init__(self, document_repository: DocumentRepository):
        self.document_repository = document_repository
        self.llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    async def answer(self, question: str, history: list[HistoryMessage]) -> AnswerResult:
        search_query = await self._rewrite_query(question, history=history)
        docs = await asyncio.to_thread(self.document_repository.similarity_search, search_query)
        sources = self._collect_sources(docs)
        response = await self._generate_answer(question, docs=docs, history=history)
        return {"answer": response, "sources": sources}
    
    async def stream_answer(self, question: str, history: list[HistoryMessage]) -> AsyncGenerator[StreamChunk, None]:
        search_query = await self._rewrite_query(question, history=history)
        docs = await asyncio.to_thread(self.document_repository.similarity_search, search_query)
        sources = self._collect_sources(docs)
        message = self._build_messages(question, docs=docs, history=history)
        async for chunk in self.llm.astream(message):
            yield (str(chunk.content), None)
        yield ("", sources)

    def _build_messages(self, question: str, docs: list[Document], history: list[HistoryMessage]) -> list[SystemMessage | HumanMessage | AIMessage]:
        context = "\n\n".join([f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}" for doc in docs])
        messages: list[SystemMessage | HumanMessage | AIMessage] = []
        system_prompt = (
            "You are a document assistant.\n"
            "Answer ONLY using the provided context documents.\n"
            "Each document is marked with [Source: ...].\n"
            "If multiple sources contain relevant information, combine them ALL in your answer.\n"
            "When citing sources, mention only the document title, not the full [Source: ...] tag format.\n"
            'If the information is not in the context, say "I don\'t know based on the available documents."'
        )
        messages.append(SystemMessage(content=system_prompt))
        
        MAX_HISTORY = int(os.getenv("CHAT_HISTORY_ANSWER_WINDOW", "6"))
        recent_history = history[-MAX_HISTORY:]

        for previous_message in recent_history:
            if previous_message.role == "assistant":
                messages.append(AIMessage(content=previous_message.content))
            else:
                messages.append(HumanMessage(content=previous_message.content))
        
        messages.append(HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"))

        return messages
        
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

        promt: str= (
            "Given this conversation history:\n" 
            f"{history_text}"
            "Rewrite this question to be self-contained (replace pronouns, implicit references):\n" 
            f"{question}" 
            "Return ONLY the rewritten question, nothing else. If the question is already self-contained, return it unchanged."
            )
    
        response = await self.llm.ainvoke([HumanMessage(content=promt)])
        return str(response.content).strip()

    async def _generate_answer(self, question: str, docs: list[Document], history: list[HistoryMessage]) -> str:
        messages = self._build_messages(question, docs=docs, history=history)
        response = await self.llm.ainvoke(messages)
        return str(response.content)

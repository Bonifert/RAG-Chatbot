from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.documents import Document
from app.repositories.document_repository import DocumentRepository
from app.types import AnswerResult, Sources, StreamChunk
from typing import Generator
from app.schemas import HistoryMessage
import os

class RetrievalService:
    def __init__(self, document_repository: DocumentRepository):
        self.document_repository = document_repository
        self.llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    def answer(self, question: str, history: list[HistoryMessage]) -> AnswerResult:
        docs = self.document_repository.similarity_search(question)
        sources = self._collect_sources(docs)
        response = self._generate_answer(question, docs=docs, history=history)
        return {"answer": response, "sources": sources}
    
    def stream_answer(self, question: str, history: list[HistoryMessage]) -> Generator[StreamChunk, None, None]:
        docs = self.document_repository.similarity_search(question)
        sources = self._collect_sources(docs)
        message = self._build_messages(question, docs=docs, history=history)
        for chunk in self.llm.stream(message):
            yield (str(chunk.content), None)
        yield ("", sources)

    def _build_messages(self, question: str, docs: list[Document], history: list[HistoryMessage]) -> list[SystemMessage | HumanMessage | AIMessage]:
        context = "\n\n".join([doc.page_content for doc in docs])
        messages: list[SystemMessage | HumanMessage | AIMessage] = []
        messages.append(SystemMessage(content="You are a document assistant. Answer only based on the provided context. If the answer is not in the context, say so."))

        for previous_message in history:
            if previous_message.role == "assistant":
                messages.append(AIMessage(content=previous_message.content))
            else:
                messages.append(HumanMessage(content=previous_message.content))
        
        messages.append(HumanMessage(content=f"Kontextus:\n{context}\n\nKérdés: {question}"))

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
        

    def _generate_answer(self, question: str, docs: list[Document], history: list[HistoryMessage]) -> str:
        messages = self._build_messages(question, docs=docs, history=history)
        response = self.llm.invoke(messages)
        return str(response.content)

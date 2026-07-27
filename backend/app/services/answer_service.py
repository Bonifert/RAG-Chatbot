from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.documents import Document
from app.schemas import HistoryMessage
from typing import AsyncGenerator
import os

class AnswerService:
    def __init__(self):
        self.llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    async def generate(self, question: str, docs: list[Document], history: list[HistoryMessage]) -> str:
        messages = self._build_messages(question, docs=docs, history=history)
        response = await self.llm.ainvoke(messages)
        return str(response.content)

    async def stream(self, question: str, docs: list[Document], history: list[HistoryMessage]) -> AsyncGenerator[str, None]:
        messages = self._build_messages(question, docs=docs, history=history)
        async for chunk in self.llm.astream(messages):
            yield str(chunk.content)

    def _build_messages(self, question: str, docs: list[Document], history: list[HistoryMessage]) -> list[SystemMessage | HumanMessage | AIMessage]:
        context = "\n\n".join([f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}" for doc in docs])
        messages: list[SystemMessage | HumanMessage | AIMessage] = []
        system_prompt = (
            "You are a document assistant.\n"
            "Answer ONLY using the provided context documents.\n"
            "Each document is marked with [Source: ...].\n"
            "If multiple sources contain relevant information, combine them ALL in your answer.\n"
            "When citing sources, mention only the document title, not the full [Source: ...] tag format.\n"
            "If the question assumes something that contradicts the context, say so and give the correct fact from the context.\n"
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

from pydantic import BaseModel
from typing import Literal

class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class AskRequest(BaseModel):
    question: str
    history: list[HistoryMessage] = []



class AnswerResponse(BaseModel):
    answer: str
    sources: dict[str, list[str]]
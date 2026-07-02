from fastapi import APIRouter, Depends, File, UploadFile
from app.services.ingestion_service import IngestionService
from app.services.retrieval_service import RetrievalService
from app.services.document_service import DocumentService
from app.dependencies import get_ingestion_service, get_retrieval_service, get_document_service
from app.schemas import AnswerResponse, AskRequest
from fastapi.responses import StreamingResponse
import json

router = APIRouter();

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...), service: IngestionService = Depends(get_ingestion_service)) -> dict[str, str]:
    service.process_pdf(file)
    return {"message": f"File uploaded and processed successfully: {file.filename}"}

@router.post("/ask")
async def ask_question(body: AskRequest, service: RetrievalService = Depends(get_retrieval_service)) -> AnswerResponse:
    question_answer = service.answer(body.question, body.history)
    return AnswerResponse(answer=question_answer["answer"], sources=question_answer["sources"])

@router.get("/documents")
async def get_documents(service: DocumentService = Depends(get_document_service)) -> list[str]:
    return service.get_documents()

@router.post("/ask/stream")
async def ask_question_stream(body: AskRequest, service: RetrievalService = Depends(get_retrieval_service)) -> StreamingResponse:
    def generate():
        for token, sources in service.stream_answer(body.question, body.history):
            if sources is not None:
                yield f'data: {json.dumps({"sources": sources})}\n\n'
            else:
                yield f'data: {json.dumps({"token": token})}\n\n'
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.delete("/document")
async def delete_document(name: str, service: DocumentService = Depends(get_document_service)) -> None:
    service.delete_document(name)
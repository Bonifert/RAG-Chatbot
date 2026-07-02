from fastapi import Depends

from app.repositories.document_repository import DocumentRepository
from app.services.retrieval_service import RetrievalService
from app.services.ingestion_service import IngestionService
from app.services.document_service import DocumentService
from functools import lru_cache

@lru_cache
def get_document_repository() -> DocumentRepository:
    return DocumentRepository()

def get_retrieval_service(document_repo: DocumentRepository = Depends(get_document_repository)) -> RetrievalService:
    return RetrievalService(document_repo)

def get_ingestion_service(document_repo: DocumentRepository = Depends(get_document_repository)) -> IngestionService:
    return IngestionService(document_repo)

def get_document_service(document_repo: DocumentRepository = Depends(get_document_repository)) -> DocumentService:
    return DocumentService(document_repo)
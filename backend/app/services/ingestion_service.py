from fastapi import UploadFile

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.repositories.document_repository import DocumentRepository
from langchain_community.document_loaders import PyMuPDFLoader
import os
import tempfile

class IngestionService:
    def __init__(self, document_repository: DocumentRepository):
        self.document_repository = document_repository
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "100"))
        )

    def process_pdf(self, pdf: UploadFile) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf.file.read())
            tmp_path = tmp.name
        try:
            loader = PyMuPDFLoader(tmp_path)
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = pdf.filename
            chunks = self._chunk_documents(docs)
            self.document_repository.add_document(chunks)
        finally:
            os.remove(tmp_path)
        

    def _chunk_documents(self,documents: list[Document]) -> list[Document]:
        chunks = self.splitter.split_documents(documents)
        return chunks
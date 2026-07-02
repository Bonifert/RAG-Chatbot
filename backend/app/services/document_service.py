from app.repositories.document_repository import DocumentRepository


class DocumentService:
    def __init__(self, document_repository: DocumentRepository):
        self.document_repository = document_repository

    def get_documents(self) -> list[str]:
        return self.document_repository.list_documents()
    
    def delete_document(self, file_name: str) -> None:
        self.document_repository.delete_document(file_name)
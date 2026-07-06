import os

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
import psycopg2
from app.exceptions import NotFoundError

class DocumentRepository:
    def __init__(self):
        self.vectorstore = PGVector(
            embeddings=OpenAIEmbeddings(model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")),
            collection_name="documents",
            connection=os.getenv("DATABASE_URL"),
        )
        self.conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        self.k = int(os.getenv("SIMILARITY_SEARCH_K", "7"))

    def add_document(self, chunks: list[Document]):
        self.vectorstore.add_documents(chunks)

    def list_documents(self) -> list[str]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT DISTINCT cmetadata->>'source' FROM langchain_pg_embedding")
            return [row[0] for row in cur.fetchall() if row[0]]
        
    def delete_document(self, filename: str):
        ids = self._get_ids_by_source(filename)
        if not ids:
            raise NotFoundError(f"Document not found: {filename}")
        self.vectorstore.delete(ids)

    def _get_ids_by_source(self, filename: str) -> list[str]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM langchain_pg_embedding WHERE cmetadata->>'source' = %s", (filename,))
            return [row[0] for row in cur.fetchall()]
        
    def similarity_search(self, query: str) -> list[Document]:
        return self.vectorstore.similarity_search(query, k=self.k)  # type: ignore -> bc. similarity_search Uknown input
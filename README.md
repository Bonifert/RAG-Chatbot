# RAG Chatbot

Chat with your PDF documents using RAG (Retrieval-Augmented Generation).

- PDF upload and semantic search via pgvector embeddings
- Streaming responses with source references (document + page number)
- Conversation history passed to the LLM for follow-up questions
- Document management (list, delete)

## Stack

- **Backend:** FastAPI, LangChain, OpenAI, PostgreSQL + pgvector
- **Frontend:** React, TypeScript, Vite, shadcn/ui, Tailwind CSS
- **Infrastructure:** Docker, Docker Compose

## Requirements

- Docker and Docker Compose
- OpenAI API key

## Getting started

1. Rename `.env.example` to `.env` in the backend folder and set your **OpenAI API key**.

2. Start everything:
   ```bash
   docker compose up --build
   ```

3. Open in browser:
   - Frontend: http://localhost:5173
   - API docs: http://localhost:8000/docs

## Configuration

All settings are in `backend/.env` — copy `.env.example` to get started.

- `OPENAI_MODEL` — LLM model (default: `gpt-4o-mini`)
- `OPENAI_EMBEDDING_MODEL` — embedding model (default: `text-embedding-3-small`)
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — chunking parameters (default: `500` / `100`)
- `SIMILARITY_SEARCH_K` — how many chunks to retrieve per query (default: `4`)


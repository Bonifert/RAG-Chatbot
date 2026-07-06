# RAG Chatbot

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?logo=langchain&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?logo=openai&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?logo=tailwindcss&logoColor=white)
![shadcn/ui](https://img.shields.io/badge/shadcn%2Fui-000000?logo=shadcnui&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

Chat with your PDF documents using RAG (Retrieval-Augmented Generation).


- PDF upload and semantic search via pgvector embeddings
- Streaming responses with source references (document + page number)
- Conversation history passed to the LLM for follow-up questions
- Document management (list, delete)

## Highlights

- Evaluated with [RAGAS](https://github.com/explodinggradients/ragas) across faithfulness,
  answer relevancy, and context recall — not just "it seems to work," actual measured numbers.
- Retrieval was tuned by testing multiple `k` values specifically against multi-hop questions
  (where a single query has to pull from several distant sections), landing on `k=7`.
- The evaluation judge model is deliberately different from the app's own model, so the system
  isn't grading its own homework.
- Fixed a blocking-event-loop issue in the FastAPI streaming routes, since `/ask` and
  `/ask/stream` were originally synchronous and stalled the server under concurrent requests.

See [Evaluation](#evaluation) below for the full methodology and results.

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

- `OPENAI_API_KEY` — your OpenAI API key (required)
- `DATABASE_URL` — Postgres connection string; the default already matches the `db`
  service in `docker-compose.yml`, only change it if you're running Postgres elsewhere
- `OPENAI_MODEL` — LLM model (default: `gpt-4o-mini`)
- `OPENAI_EMBEDDING_MODEL` — embedding model (default: `text-embedding-3-small`)
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — chunking parameters (default: `500` / `100`)
- `SIMILARITY_SEARCH_K` — how many chunks to retrieve per query (default: `7`,
  tuned via the [evaluation pipeline](#evaluation))
- `CHAT_HISTORY_RETRIEVAL_WINDOW` — how many previous messages are used to rewrite
  follow-up questions into self-contained search queries (default: `4`)
- `CHAT_HISTORY_ANSWER_WINDOW` — how many previous messages are sent as conversation
  context when generating the answer (default: `6`)

## Evaluation

The backend includes a RAGAS-based evaluation pipeline (`backend/eval/`) that measures
faithfulness, answer relevancy, and context recall against a fixed test dataset built
around a sample PDF (ALDI 2024 Sustainability Report).

Unlike the main app, this runs locally (not in Docker), since it imports the backend
code directly and talks to Postgres over `localhost` instead of the `db` service name.

1. Start everything and upload the sample PDF, so the vector store has
   data to retrieve from: `docker compose up --build`, then upload via the frontend
   or `POST /upload`.
2. From `backend/`, with your venv active, install the eval dependencies:
   `pip install -r eval/requirements-eval.txt`
3. Make sure `db` is running (`docker compose up db` is enough once the PDF is ingested)
   and run: `python eval/run_eval.py`

Results are printed to the console and saved to a timestamped file in `backend/eval/`.

> **See [`backend/eval/FINDINGS.md`](backend/eval/FINDINGS.md) for the latest tuning results and known limitations.**
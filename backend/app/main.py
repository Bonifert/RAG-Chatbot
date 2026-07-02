from fastapi import FastAPI
from app.routers import documents
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.exceptions import register_exception_handlers

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


app.include_router(documents.router)
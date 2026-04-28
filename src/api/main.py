from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from project root .env before initializing the app.
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=ROOT_DIR / ".env", override=True)

from fastapi import FastAPI
from src.api import chat, repos

app = FastAPI(
    title="GitHub Multimodal RAG API",
    description="Intelligent Q&A system for GitHub repositories combining text, code, and images.",
    version="0.1.0"
)

app.include_router(chat.router)
app.include_router(repos.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to GitHub Multimodal RAG API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=ROOT_DIR / ".env", override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import auth, chat, repos, structure, upload

app = FastAPI(
    title="GitHub Multimodal RAG API",
    description=(
        "面向 GitHub 仓库的多模态 RAG 智能学习助手后端。\n\n"
        "功能包括：用户认证、仓库索引（AST 智能切片）、智能问答（RAG）、代码结构可视化。"
    ),
    version="0.2.0",
)

# CORS — 开发环境允许所有来源；生产环境请收紧
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(repos.router)
app.include_router(structure.router)
app.include_router(upload.router)


@app.get("/", tags=["system"])
def read_root():
    return {
        "message": "Welcome to GitHub Multimodal RAG API",
        "version": "0.2.0",
        "docs":    "/docs",
    }


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}

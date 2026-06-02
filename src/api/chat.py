from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.generation import rag_pipeline

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    repo_id: str
    question: str

async def generate_chat_stream(repo_id: str, question: str):
    """
    异步生成器：调用 LangChain 的 astream 方法实现流式输出 SSE (Server-Sent Events)。
    前端可以借此实现“打字机”效果。
    """
    async for chunk in rag_pipeline.stream_rag_answer(repo_id=repo_id, question=question):
        yield _sse_data(chunk)
    yield "data: [DONE]\n\n"

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    供前端调用的 RAG 对话接口
    """
    if not request.repo_id.strip():
        raise HTTPException(status_code=400, detail="repo_id is required.")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question is required.")
    return StreamingResponse(
        generate_chat_stream(request.repo_id, request.question),
        headers={"Content-Type": "text/event-stream"},
    )


def _sse_data(chunk: str) -> str:
    lines = str(chunk).splitlines() or [""]
    return "".join(f"data: {line}\n" for line in lines) + "\n"

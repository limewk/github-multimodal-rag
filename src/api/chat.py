from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from src.generation.rag_pipeline import stream_rag_answer

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    repo_id: str
    question: str

async def generate_chat_stream(repo_id: str, question: str):
    """
    异步生成器：调用 LangChain 的 astream 方法实现流式输出 SSE (Server-Sent Events)。
    前端可以借此实现“打字机”效果。
    """
    async for chunk in stream_rag_answer(repo_id=repo_id, question=question):
        yield _sse_data(chunk)
    yield "data: [DONE]\n\n"

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    供前端调用的 RAG 对话接口
    """
    return StreamingResponse(
        generate_chat_stream(request.repo_id, request.question),
        media_type="text/event-stream"
    )


def _sse_data(chunk: str) -> str:
    lines = str(chunk).splitlines() or [""]
    return "".join(f"data: {line}\n" for line in lines) + "\n"

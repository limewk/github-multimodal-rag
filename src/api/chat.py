from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from src.generation.rag_pipeline import build_rag_chain

router = APIRouter()
rag_chain = build_rag_chain()

class ChatRequest(BaseModel):
    question: str

async def generate_chat_stream(question: str):
    """
    异步生成器：调用 LangChain 的 astream 方法实现流式输出 SSE (Server-Sent Events)。
    前端可以借此实现“打字机”效果。
    """
    async for chunk in rag_chain.astream(question):
        # 组装符合 SSE 标准的数据格式
        yield f"data: {chunk}\n\n"
    yield "data: [DONE]\n\n"

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    供前端调用的 RAG 对话接口
    """
    return StreamingResponse(
        generate_chat_stream(request.question),
        media_type="text/event-stream"
    )

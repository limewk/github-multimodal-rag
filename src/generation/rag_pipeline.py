import json
import os
from collections.abc import AsyncIterator
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.retrieval.vector_store import search_repo


PROMPT_PATH = Path("src/prompts/rag_prompt.jinja2")
ROOT_DIR = Path(__file__).resolve().parents[2]
DOTENV_PATH = ROOT_DIR / ".env"


def format_docs(docs):
    """
    Format retrieved Documents with source metadata so generated answers can cite files.
    """
    formatted = []
    for index, doc in enumerate(docs, start=1):
        meta = doc.metadata
        source = meta.get("url") or meta.get("path") or "unknown"
        start_line = meta.get("start_line")
        end_line = meta.get("end_line")
        line_info = (
            f":{start_line}-{end_line}" if start_line and end_line else ""
        )
        formatted.append(
            f"[{index}] {source}{line_info} ({meta.get('source_type', 'unknown')})\n"
            f"{doc.page_content}"
        )
    return "\n\n".join(formatted)


def format_sources(docs) -> str:
    sources = []
    seen = set()
    for index, doc in enumerate(docs, start=1):
        meta = doc.metadata
        source = meta.get("url") or meta.get("path") or "unknown"
        start_line = meta.get("start_line")
        end_line = meta.get("end_line")
        key = (source, start_line, end_line)
        if key in seen:
            continue
        seen.add(key)
        line_info = f":{start_line}-{end_line}" if start_line and end_line else ""
        sources.append(f"[{index}] {source}{line_info}")
    return "\n".join(sources)


def build_rag_chain():
    """
    Build the generation-only chain. Retrieval is repo-aware and happens before this chain.
    """
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)
    rag_prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = ChatPromptTemplate.from_template(
        rag_prompt_template,
        template_format="jinja2",
    )
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    if not base_url:  # handles empty string case
        base_url = None

    api_key = (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        api_key = None

    extra_body = _load_json_env("LLM_EXTRA_BODY")
    provider = os.getenv("LLM_PROVIDER", "").strip()
    if provider and "provider" not in extra_body:
        extra_body["provider"] = provider
    model_kwargs = {"extra_body": extra_body} if extra_body else {}

    llm = ChatOpenAI(
        model=os.getenv("LLM_CHAT_MODEL", os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")),
        api_key=api_key,
        base_url=base_url,
        temperature=0.3,
        streaming=True,
    )
    return prompt | llm | StrOutputParser()


async def stream_rag_answer(repo_id: str, question: str, k: int = 5) -> AsyncIterator[str]:
    docs = search_repo(repo_id, question, k=k)
    context = format_docs(docs)

    if _use_offline_answer():
        yield _offline_answer(question, context)
    else:
        chain = build_rag_chain()
        async for chunk in chain.astream({"context": context, "question": question}):
            yield chunk

    sources = format_sources(docs)
    if sources:
        yield f"\n\nSources:\n{sources}"


def _use_offline_answer() -> bool:
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)
    api_key = (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    provider = os.getenv("RAG_LLM_PROVIDER", "openai").lower()
    
    if provider == "offline":
        return True
        
    # 如果既没有配置 api_key，也没有配置 base_url (本地模型可能不需要 key)
    if not api_key and not base_url:
        return True
        
    return api_key.startswith("your_") and not base_url


def _offline_answer(question: str, context: str) -> str:
    if not context:
        return "No indexed context was found for this repository, so I cannot answer from repository evidence."
    preview = context[:1200]
    return (
        "Offline RAG preview. Configure LLM_API_KEY or LLM_BASE_URL for model-generated answers.\n\n"
        f"Question: {question}\n\n"
        f"Retrieved context:\n{preview}"
    )


def _load_json_env(name: str) -> dict:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}

"""代码结构查询 API — 返回完整 AST 元数据 + 完整代码内容"""
import logging
from collections import defaultdict

from fastapi import APIRouter, HTTPException
from langchain_core.documents import Document
from pydantic import BaseModel
from qdrant_client import models as qmodels

from src.retrieval.vector_store import COLLECTION_NAME, get_qdrant_client

router = APIRouter(prefix="/repos", tags=["structure"])
logger = logging.getLogger(__name__)
SCROLL_BATCH = 256


class ChunkMeta(BaseModel):
    chunk_id:        int  = 0
    chunk_type:      str  = "unknown"
    name:            str  = ""
    start_line:      int  = 0
    end_line:        int  = 0
    params:          str  = ""
    return_type:     str  = ""
    is_async:        bool = False
    decorators:      str  = ""
    base_classes:    str  = ""
    docstring:       str  = ""
    is_exported:     bool = False
    access:          str  = ""
    content_preview: str  = ""   # 200-char single-line preview
    content:         str  = ""   # Full content (up to 4000 chars, newlines preserved)


class FileStructure(BaseModel):
    path:     str
    language: str
    chunks:   list[ChunkMeta]


class RepoStructureResponse(BaseModel):
    repo_id:      str
    total_files:  int
    total_chunks: int
    files:        list[FileStructure]


def _scroll_code_docs(repo_id: str, limit: int = 3000) -> list[Document]:
    client = get_qdrant_client()
    filt = qmodels.Filter(must=[
        qmodels.FieldCondition(key="metadata.repo_id",     match=qmodels.MatchValue(value=repo_id)),
        qmodels.FieldCondition(key="metadata.source_type", match=qmodels.MatchAny(any=["code"])),
    ])
    docs, offset = [], None
    while len(docs) < limit:
        results, next_off = client.scroll(
            collection_name=COLLECTION_NAME, scroll_filter=filt,
            limit=min(SCROLL_BATCH, limit - len(docs)), offset=offset,
            with_payload=True, with_vectors=False,
        )
        for pt in results:
            pay = pt.payload or {}
            docs.append(Document(page_content=pay.get("page_content",""), metadata=pay.get("metadata",{})))
        if next_off is None or len(results) < SCROLL_BATCH: break
        offset = next_off
    return docs


@router.get("/{repo_id}/structure", response_model=RepoStructureResponse, summary="获取仓库代码结构")
def get_repo_structure(repo_id: str, limit: int = 3000):
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION_NAME):
        raise HTTPException(status_code=404, detail="向量库集合不存在，请先索引仓库")
    docs = _scroll_code_docs(repo_id, limit)
    if not docs:
        raise HTTPException(status_code=404, detail=f"未找到仓库 {repo_id!r} 的索引数据")

    files_map: dict[str, list] = defaultdict(list)
    for doc in docs:
        files_map[doc.metadata.get("path","unknown")].append((doc, doc.metadata))

    result_files, total_chunks = [], 0
    for path in sorted(files_map):
        items = files_map[path]
        lang  = items[0][1].get("language","unknown") if items else "unknown"
        chunks = []
        for doc, meta in sorted(items, key=lambda x: x[1].get("chunk_id",0)):
            ctype   = meta.get("ast_chunk_type") or ("code" if meta.get("source_type")=="code" else "unknown")
            raw     = doc.page_content
            preview = raw[:200].replace("\n"," ").strip() + ("…" if len(raw)>200 else "")
            content = raw[:4000]
            chunks.append(ChunkMeta(
                chunk_id=meta.get("chunk_id",0), chunk_type=ctype,
                name=meta.get("ast_name",""), start_line=meta.get("start_line",0),
                end_line=meta.get("end_line",0), params=meta.get("ast_params",""),
                return_type=meta.get("ast_return_type",""), is_async=bool(meta.get("ast_is_async")),
                decorators=meta.get("ast_decorators",""), base_classes=meta.get("ast_base_classes",""),
                docstring=meta.get("ast_docstring",""), is_exported=bool(meta.get("ast_is_exported")),
                access=meta.get("ast_access",""), content_preview=preview, content=content,
            ))
        total_chunks += len(chunks)
        result_files.append(FileStructure(path=path, language=lang, chunks=chunks))
    return RepoStructureResponse(repo_id=repo_id, total_files=len(result_files),
                                 total_chunks=total_chunks, files=result_files)

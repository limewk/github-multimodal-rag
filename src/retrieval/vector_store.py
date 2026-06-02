import hashlib
import math
import os
import re
import uuid
from functools import lru_cache
from itertools import islice
from pathlib import Path
from typing import Iterable, Iterator

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient, models


COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "github_repo_multi_modal")
LOCAL_QDRANT_PATH = os.getenv("QDRANT_PATH", "data/qdrant")
HASH_EMBEDDING_DIMENSION = int(os.getenv("RAG_HASH_EMBEDDING_DIM", "384"))
INDEX_BATCH_SIZE = int(os.getenv("RAG_INDEX_BATCH_SIZE", "64"))
HYBRID_VECTOR_CANDIDATES = int(os.getenv("RAG_HYBRID_VECTOR_CANDIDATES", "48"))
HYBRID_KEYWORD_CANDIDATES = int(os.getenv("RAG_HYBRID_KEYWORD_CANDIDATES", "800"))
HYBRID_NEIGHBOR_WINDOW = int(os.getenv("RAG_HYBRID_NEIGHBOR_WINDOW", "1"))

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./#-]+")
IMPORTANT_FILE_NAMES = {
    "README",
    "README.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "Dockerfile",
    "Makefile",
    "vite.config.js",
    "vite.config.ts",
}
IMPORTANT_PATH_PARTS = {
    "src",
    "app",
    "api",
    "routes",
    "router",
    "main",
    "index",
    "server",
    "config",
    "docs",
}


class HashEmbeddings(Embeddings):
    """Small deterministic embedding implementation for local tests/dev without API keys."""

    def __init__(self, dimension: int = HASH_EMBEDDING_DIMENSION):
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def get_embeddings() -> Embeddings:
    provider = os.getenv("RAG_EMBEDDING_PROVIDER", "openai").lower()
    api_key = os.getenv("OPENAI_API_KEY")
    if provider == "hash" or not api_key or api_key.startswith("your_"):
        return HashEmbeddings()
    return OpenAIEmbeddings(
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        api_key=api_key,
    )


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    if url:
        return QdrantClient(url=url, api_key=api_key)

    location = os.getenv("QDRANT_LOCATION")
    if location:
        return QdrantClient(location=location)

    mode = os.getenv("QDRANT_MODE", "local").lower()
    if mode == "remote":
        return QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
            api_key=api_key,
        )

    path = Path(LOCAL_QDRANT_PATH)
    path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(path))


@lru_cache(maxsize=1)
def get_vector_store() -> QdrantClient:
    client = get_qdrant_client()
    _ensure_collection(client, get_embeddings())
    return client


def index_documents(repo_id: str, documents: Iterable[Document]) -> int:
    client = get_vector_store()
    embeddings = get_embeddings()
    _delete_repo_documents(repo_id)
    indexed_count = 0
    for docs in _batched(documents, INDEX_BATCH_SIZE):
        vectors = embeddings.embed_documents([doc.page_content for doc in docs])
        points = [
            models.PointStruct(
                id=_point_id(repo_id, doc),
                vector=vector,
                payload={"page_content": doc.page_content, "metadata": doc.metadata},
            )
            for doc, vector in zip(docs, vectors, strict=True)
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
        indexed_count += len(docs)
    return indexed_count


def search_repo(repo_id: str, query: str, k: int = 5) -> list[Document]:
    client = get_vector_store()
    query_vector = get_embeddings().embed_query(query)
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=_repo_filter(repo_id),
        limit=k,
        with_payload=True,
    )
    return [_point_to_document(point) for point in response.points]


def hybrid_search_repo(
    repo_id: str,
    query: str,
    k: int = 16,
    vector_candidates: int = HYBRID_VECTOR_CANDIDATES,
    keyword_candidates: int = HYBRID_KEYWORD_CANDIDATES,
    neighbor_window: int = HYBRID_NEIGHBOR_WINDOW,
) -> list[Document]:
    """
    Retrieve repository evidence with vector recall, lexical/path recall, lightweight
    reranking, and same-file neighboring chunk expansion.
    """
    vector_hits = _search_repo_scored(repo_id, query, k=max(k, vector_candidates))
    keyword_hits = _keyword_search_repo(repo_id, query, limit=keyword_candidates)
    ranked = _rerank_candidates(query, vector_hits, keyword_hits)
    selected = [candidate["doc"] for candidate in ranked[:k]]

    if neighbor_window > 0:
        selected = _expand_neighbor_chunks(repo_id, selected, window=neighbor_window)

    return _dedupe_documents(selected)[: max(k, len(selected))]


def load_repo_context_documents(
    repo_id: str,
    source_types: tuple[str, ...] = ("repo_overview", "repo_manifest"),
    limit: int = 6,
) -> list[Document]:
    client = get_vector_store()
    if not client.collection_exists(COLLECTION_NAME):
        return []

    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=_repo_source_type_filter(repo_id, source_types),
        limit=limit,
        with_payload=True,
    )
    return sorted(
        (_point_to_document(point) for point in points),
        key=lambda doc: (
            0 if doc.metadata.get("source_type") == "repo_overview" else 1,
            doc.metadata.get("path") or "",
            doc.metadata.get("chunk_id") or 0,
        ),
    )


def _search_repo_scored(repo_id: str, query: str, k: int) -> list[tuple[Document, float, int]]:
    client = get_vector_store()
    query_vector = get_embeddings().embed_query(query)
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=_repo_filter(repo_id),
        limit=k,
        with_payload=True,
    )
    return [
        (_point_to_document(point), float(getattr(point, "score", 0.0) or 0.0), rank)
        for rank, point in enumerate(response.points, start=1)
    ]


def _keyword_search_repo(
    repo_id: str,
    query: str,
    limit: int,
) -> list[tuple[Document, float]]:
    query_tokens = _query_tokens(query)
    if not query_tokens:
        return []

    docs = _scroll_repo_documents(repo_id, limit=limit)
    scored = [
        (doc, _lexical_score(query_tokens, doc))
        for doc in docs
    ]
    return [
        item
        for item in sorted(scored, key=lambda item: item[1], reverse=True)
        if item[1] > 0
    ]


def _rerank_candidates(
    query: str,
    vector_hits: list[tuple[Document, float, int]],
    keyword_hits: list[tuple[Document, float]],
) -> list[dict]:
    candidates: dict[tuple, dict] = {}
    max_keyword = max((score for _, score in keyword_hits), default=1.0)

    for doc, score, rank in vector_hits:
        entry = candidates.setdefault(
            _document_key(doc),
            {"doc": doc, "vector": 0.0, "keyword": 0.0, "rank": rank},
        )
        entry["vector"] = max(entry["vector"], score)
        entry["rank"] = min(entry["rank"], rank)

    for doc, score in keyword_hits:
        entry = candidates.setdefault(
            _document_key(doc),
            {"doc": doc, "vector": 0.0, "keyword": 0.0, "rank": len(vector_hits) + 1},
        )
        entry["keyword"] = max(entry["keyword"], score / max_keyword)

    overview_intent = _is_overview_query(query)
    for entry in candidates.values():
        doc = entry["doc"]
        meta = doc.metadata
        entry["score"] = (
            0.48 * entry["vector"]
            + 0.36 * entry["keyword"]
            + 0.10 * _path_score(query, doc)
            + 0.06 * _important_file_score(meta.get("path") or "")
            + _source_type_score(meta.get("source_type") or "")
        )
        if overview_intent and meta.get("source_type") in {"repo_overview", "repo_manifest", "markdown"}:
            entry["score"] += 0.20

    return sorted(
        candidates.values(),
        key=lambda entry: (entry["score"], -entry["rank"]),
        reverse=True,
    )


def _expand_neighbor_chunks(repo_id: str, docs: list[Document], window: int) -> list[Document]:
    expanded: list[Document] = []
    cache: dict[str, list[Document]] = {}
    for doc in docs:
        expanded.append(doc)
        meta = doc.metadata
        path = meta.get("path")
        chunk_id = meta.get("chunk_id")
        if not path or path.startswith("__repo__/") or not isinstance(chunk_id, int):
            continue
        if meta.get("source_type") not in {"code", "markdown", "text", "issue"}:
            continue

        siblings = cache.setdefault(path, _load_file_documents(repo_id, path))
        neighbor_ids = set(range(max(0, chunk_id - window), chunk_id + window + 1))
        expanded.extend(
            sibling
            for sibling in siblings
            if sibling.metadata.get("chunk_id") in neighbor_ids
        )

    return _dedupe_documents(expanded)


def _load_file_documents(repo_id: str, path: str) -> list[Document]:
    return sorted(
        _scroll_documents(_repo_path_filter(repo_id, path), limit=1000),
        key=lambda doc: doc.metadata.get("chunk_id") or 0,
    )


def _scroll_repo_documents(repo_id: str, limit: int) -> list[Document]:
    return _scroll_documents(_repo_filter(repo_id), limit=limit)


def _scroll_documents(scroll_filter: models.Filter, limit: int) -> list[Document]:
    client = get_vector_store()
    documents: list[Document] = []
    offset = None
    page_size = min(256, max(1, limit))
    while len(documents) < limit:
        points, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=scroll_filter,
            limit=min(page_size, limit - len(documents)),
            offset=offset,
            with_payload=True,
        )
        documents.extend(_point_to_document(point) for point in points)
        if offset is None:
            break
    return documents


def _query_tokens(query: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_PATTERN.findall(query)
        if len(token) > 1
    }


def _document_tokens(doc: Document) -> list[str]:
    meta = doc.metadata
    text = " ".join(
        [
            meta.get("path") or "",
            meta.get("language") or "",
            meta.get("source_type") or "",
            doc.page_content,
        ]
    )
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def _lexical_score(query_tokens: set[str], doc: Document) -> float:
    doc_tokens = _document_tokens(doc)
    if not doc_tokens:
        return 0.0

    token_counts: dict[str, int] = {}
    for token in doc_tokens:
        token_counts[token] = token_counts.get(token, 0) + 1

    path = (doc.metadata.get("path") or "").lower()
    score = 0.0
    for token in query_tokens:
        count = token_counts.get(token, 0)
        if count:
            score += 1.0 + math.log(count)
        if token in path:
            score += 2.5
    return score


def _path_score(query: str, doc: Document) -> float:
    path = (doc.metadata.get("path") or "").lower()
    if not path:
        return 0.0
    query_tokens = _query_tokens(query)
    if not query_tokens:
        return 0.0
    matches = sum(1 for token in query_tokens if token in path)
    return min(1.0, matches / max(1, len(query_tokens)))


def _important_file_score(path: str) -> float:
    if not path:
        return 0.0
    name = Path(path).name
    stem = Path(path).stem
    parts = {part.lower() for part in Path(path).parts}
    if name in IMPORTANT_FILE_NAMES or stem in IMPORTANT_FILE_NAMES:
        return 1.0
    if parts & IMPORTANT_PATH_PARTS:
        return 0.45
    return 0.0


def _source_type_score(source_type: str) -> float:
    weights = {
        "code": 0.08,
        "markdown": 0.05,
        "text": 0.03,
        "repo_overview": 0.05,
        "repo_manifest": 0.04,
        "issue": 0.02,
        "image_reference": 0.01,
    }
    return weights.get(source_type, 0.0)


def _is_overview_query(query: str) -> bool:
    lowered = query.lower()
    keywords = (
        "overview",
        "architecture",
        "structure",
        "module",
        "tech stack",
        "entrypoint",
        "整体",
        "架构",
        "结构",
        "模块",
        "技术栈",
        "入口",
        "项目",
    )
    return any(keyword in lowered for keyword in keywords)


def _dedupe_documents(docs: list[Document]) -> list[Document]:
    deduped = []
    seen = set()
    for doc in docs:
        key = _document_key(doc)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(doc)
    return deduped


def _document_key(doc: Document) -> tuple:
    meta = doc.metadata
    return (
        meta.get("path") or meta.get("url") or "",
        meta.get("source_type") or "",
        meta.get("chunk_id") or 0,
        meta.get("start_line") or 0,
    )


def get_retriever(repo_id: str, k: int = 5):
    return RepoRetriever(repo_id=repo_id, k=k)


class RepoRetriever:
    def __init__(self, repo_id: str, k: int = 5):
        self.repo_id = repo_id
        self.k = k

    def invoke(self, query: str) -> list[Document]:
        return hybrid_search_repo(self.repo_id, query, k=self.k)

    def get_relevant_documents(self, query: str) -> list[Document]:
        return self.invoke(query)


def _ensure_collection(client: QdrantClient, embeddings: Embeddings) -> None:
    if client.collection_exists(COLLECTION_NAME):
        return

    vector_size = len(embeddings.embed_query("dimension probe"))
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
        ),
    )


def _delete_repo_documents(repo_id: str) -> None:
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION_NAME):
        return
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.FilterSelector(filter=_repo_filter(repo_id)),
        wait=True,
    )


def _batched(items: Iterable[Document], size: int) -> Iterator[list[Document]]:
    if size < 1:
        raise ValueError("Batch size must be at least 1")

    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def _repo_filter(repo_id: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.repo_id",
                match=models.MatchValue(value=repo_id),
            )
        ]
    )


def _repo_source_type_filter(repo_id: str, source_types: tuple[str, ...]) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.repo_id",
                match=models.MatchValue(value=repo_id),
            ),
            models.FieldCondition(
                key="metadata.source_type",
                match=models.MatchAny(any=list(source_types)),
            ),
        ]
    )


def _repo_path_filter(repo_id: str, path: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.repo_id",
                match=models.MatchValue(value=repo_id),
            ),
            models.FieldCondition(
                key="metadata.path",
                match=models.MatchValue(value=path),
            ),
        ]
    )


def _point_id(repo_id: str, doc: Document) -> str:
    meta = doc.metadata
    basis = "|".join(
        [
            repo_id,
            str(meta.get("path") or meta.get("url") or ""),
            str(meta.get("chunk_id") or 0),
            str(meta.get("start_line") or 0),
        ]
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, basis))


def _point_to_document(point) -> Document:
    payload = point.payload or {}
    return Document(
        page_content=payload.get("page_content", ""),
        metadata=payload.get("metadata", {}),
    )

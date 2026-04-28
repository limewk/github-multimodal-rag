import hashlib
import math
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient, models


COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "github_repo_multi_modal")
LOCAL_QDRANT_PATH = os.getenv("QDRANT_PATH", "data/qdrant")
HASH_EMBEDDING_DIMENSION = int(os.getenv("RAG_HASH_EMBEDDING_DIM", "384"))


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
    docs = list(documents)
    client = get_vector_store()
    embeddings = get_embeddings()
    _delete_repo_documents(repo_id)
    if docs:
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
    return len(docs)


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


def get_retriever(repo_id: str, k: int = 5):
    return RepoRetriever(repo_id=repo_id, k=k)


class RepoRetriever:
    def __init__(self, repo_id: str, k: int = 5):
        self.repo_id = repo_id
        self.k = k

    def invoke(self, query: str) -> list[Document]:
        return search_repo(self.repo_id, query, k=self.k)

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


def _repo_filter(repo_id: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.repo_id",
                match=models.MatchValue(value=repo_id),
            )
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

from dataclasses import dataclass
from itertools import chain

from src.ingestion.repository_loader import (
    iter_github_issues,
    iter_repository_files,
    resolve_repository_source,
)
from src.processing.chunking import iter_repository_documents
from src.retrieval.vector_store import index_documents


@dataclass(frozen=True)
class IndexResult:
    repo_id: str
    status: str
    chunks: int


def index_repository(source: str, branch: str = "main") -> IndexResult:
    repo_id, repo_path = resolve_repository_source(source, branch=branch)
    files = chain(iter_repository_files(repo_path), iter_github_issues(source))
    documents = iter_repository_documents(repo_id, files)
    chunk_count = index_documents(repo_id, documents)
    return IndexResult(repo_id=repo_id, status="indexed", chunks=chunk_count)

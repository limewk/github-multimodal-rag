from dataclasses import dataclass

from src.ingestion.repository_loader import (
    iter_github_issues,
    iter_repository_files,
    resolve_repository_source,
)
from src.processing.chunking import repository_files_to_documents
from src.retrieval.vector_store import index_documents


@dataclass(frozen=True)
class IndexResult:
    repo_id: str
    status: str
    chunks: int


def index_repository(source: str, branch: str = "main") -> IndexResult:
    repo_id, repo_path = resolve_repository_source(source, branch=branch)
    files = list(iter_repository_files(repo_path))
    files.extend(iter_github_issues(source))
    documents = repository_files_to_documents(repo_id, files)
    chunk_count = index_documents(repo_id, documents)
    return IndexResult(repo_id=repo_id, status="indexed", chunks=chunk_count)

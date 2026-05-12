from langchain_core.documents import Document

import src.retrieval.vector_store as vector_store


def test_repo_filter_prevents_cross_repo_results(monkeypatch):
    monkeypatch.setattr(vector_store, "COLLECTION_NAME", "test_repo_filter")
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("QDRANT_LOCATION", ":memory:")
    vector_store.get_qdrant_client.cache_clear()
    vector_store.get_vector_store.cache_clear()

    try:
        vector_store.index_documents(
            "repo-a",
            [
                Document(
                    page_content="alpha payment workflow",
                    metadata={
                        "repo_id": "repo-a",
                        "source_type": "code",
                        "path": "alpha.py",
                        "language": "python",
                        "chunk_id": 0,
                        "start_line": 1,
                        "end_line": 1,
                    },
                )
            ],
        )
        vector_store.index_documents(
            "repo-b",
            [
                Document(
                    page_content="beta payment workflow",
                    metadata={
                        "repo_id": "repo-b",
                        "source_type": "code",
                        "path": "beta.py",
                        "language": "python",
                        "chunk_id": 0,
                        "start_line": 1,
                        "end_line": 1,
                    },
                )
            ],
        )

        results = vector_store.search_repo("repo-a", "payment", k=5)

        assert results
        assert {doc.metadata["repo_id"] for doc in results} == {"repo-a"}
    finally:
        client = vector_store.get_qdrant_client()
        client.close()
        vector_store.get_qdrant_client.cache_clear()
        vector_store.get_vector_store.cache_clear()


def test_index_documents_accepts_streaming_iterables(monkeypatch):
    monkeypatch.setattr(vector_store, "COLLECTION_NAME", "test_streaming_iterables")
    monkeypatch.setattr(vector_store, "INDEX_BATCH_SIZE", 1)
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("QDRANT_LOCATION", ":memory:")
    vector_store.get_qdrant_client.cache_clear()
    vector_store.get_vector_store.cache_clear()

    def docs():
        for index in range(2):
            yield Document(
                page_content=f"streamed payment workflow {index}",
                metadata={
                    "repo_id": "repo-stream",
                    "source_type": "code",
                    "path": f"stream_{index}.py",
                    "language": "python",
                    "chunk_id": index,
                    "start_line": index + 1,
                    "end_line": index + 1,
                },
            )

    try:
        assert vector_store.index_documents("repo-stream", docs()) == 2

        results = vector_store.search_repo("repo-stream", "payment", k=5)

        assert len(results) == 2
        assert {doc.metadata["path"] for doc in results} == {
            "stream_0.py",
            "stream_1.py",
        }
    finally:
        client = vector_store.get_qdrant_client()
        client.close()
        vector_store.get_qdrant_client.cache_clear()
        vector_store.get_vector_store.cache_clear()


def test_load_repo_context_documents_returns_manifest_docs(monkeypatch):
    monkeypatch.setattr(vector_store, "COLLECTION_NAME", "test_repo_context_docs")
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("QDRANT_LOCATION", ":memory:")
    vector_store.get_qdrant_client.cache_clear()
    vector_store.get_vector_store.cache_clear()

    try:
        vector_store.index_documents(
            "repo-context",
            [
                Document(
                    page_content="Repository overview for RAG retrieval.",
                    metadata={
                        "repo_id": "repo-context",
                        "source_type": "repo_overview",
                        "path": "__repo__/overview.md",
                        "language": "text",
                        "chunk_id": 0,
                        "start_line": 1,
                        "end_line": 1,
                    },
                ),
                Document(
                    page_content="- src/app.py (code, python)",
                    metadata={
                        "repo_id": "repo-context",
                        "source_type": "repo_manifest",
                        "path": "__repo__/manifest_1.md",
                        "language": "text",
                        "chunk_id": 1,
                        "start_line": 1,
                        "end_line": 1,
                    },
                ),
                Document(
                    page_content="def main(): pass",
                    metadata={
                        "repo_id": "repo-context",
                        "source_type": "code",
                        "path": "src/app.py",
                        "language": "python",
                        "chunk_id": 0,
                        "start_line": 1,
                        "end_line": 1,
                    },
                ),
            ],
        )

        docs = vector_store.load_repo_context_documents("repo-context", limit=5)

        assert [doc.metadata["source_type"] for doc in docs] == [
            "repo_overview",
            "repo_manifest",
        ]
    finally:
        client = vector_store.get_qdrant_client()
        client.close()
        vector_store.get_qdrant_client.cache_clear()
        vector_store.get_vector_store.cache_clear()


def test_hybrid_search_uses_keyword_path_and_neighbor_expansion(monkeypatch):
    monkeypatch.setattr(vector_store, "COLLECTION_NAME", "test_hybrid_search")
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("QDRANT_LOCATION", ":memory:")
    vector_store.get_qdrant_client.cache_clear()
    vector_store.get_vector_store.cache_clear()

    try:
        vector_store.index_documents(
            "repo-hybrid",
            [
                Document(
                    page_content="authentication overview",
                    metadata={
                        "repo_id": "repo-hybrid",
                        "source_type": "code",
                        "path": "src/auth/service.py",
                        "language": "python",
                        "chunk_id": 0,
                        "start_line": 1,
                        "end_line": 5,
                    },
                ),
                Document(
                    page_content="def refresh_token(): return issue_token()",
                    metadata={
                        "repo_id": "repo-hybrid",
                        "source_type": "code",
                        "path": "src/auth/service.py",
                        "language": "python",
                        "chunk_id": 1,
                        "start_line": 6,
                        "end_line": 10,
                    },
                ),
                Document(
                    page_content="payment processing workflow",
                    metadata={
                        "repo_id": "repo-hybrid",
                        "source_type": "code",
                        "path": "src/payments/service.py",
                        "language": "python",
                        "chunk_id": 0,
                        "start_line": 1,
                        "end_line": 4,
                    },
                ),
            ],
        )

        results = vector_store.hybrid_search_repo(
            "repo-hybrid",
            "refresh_token in auth/service.py",
            k=1,
            vector_candidates=2,
            keyword_candidates=20,
            neighbor_window=1,
        )

        paths_and_chunks = {
            (doc.metadata["path"], doc.metadata["chunk_id"])
            for doc in results
        }
        assert results[0].metadata["path"] == "src/auth/service.py"
        assert results[0].metadata["chunk_id"] == 1
        assert ("src/auth/service.py", 1) in paths_and_chunks
        assert ("src/auth/service.py", 0) in paths_and_chunks
    finally:
        client = vector_store.get_qdrant_client()
        client.close()
        vector_store.get_qdrant_client.cache_clear()
        vector_store.get_vector_store.cache_clear()

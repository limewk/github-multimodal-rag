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

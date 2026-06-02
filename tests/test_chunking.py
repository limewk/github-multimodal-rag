from src.ingestion.repository_loader import RepositoryFile
from src.processing.chunking import repository_file_to_documents, repository_files_to_documents


def test_markdown_documents_keep_required_metadata():
    repo_file = RepositoryFile(
        path="README.md",
        content="# Demo\n\n![UI](docs/ui.png)\n\nSome setup instructions.",
        source_type="markdown",
        language="markdown",
    )

    docs = repository_file_to_documents("repo-1", repo_file)

    assert docs
    first = docs[0]
    assert first.metadata["repo_id"] == "repo-1"
    assert first.metadata["source_type"] == "markdown"
    assert first.metadata["path"] == "README.md"
    assert first.metadata["chunk_id"] == 0
    assert first.metadata["start_line"] >= 1
    assert first.metadata["end_line"] >= first.metadata["start_line"]
    assert any(doc.metadata["source_type"] == "image_reference" for doc in docs)


def test_empty_file_produces_no_text_chunks():
    repo_file = RepositoryFile(
        path="empty.py",
        content="",
        source_type="code",
        language="python",
    )

    assert repository_file_to_documents("repo-1", repo_file) == []


def test_repository_documents_include_project_overview_and_manifest():
    files = [
        RepositoryFile(
            path="README.md",
            content="# Demo\n\nProject docs.",
            source_type="markdown",
            language="markdown",
        ),
        RepositoryFile(
            path="src/app.py",
            content="def main():\n    return 'ok'\n",
            source_type="code",
            language="python",
        ),
    ]

    docs = repository_files_to_documents("repo-1", files)
    source_types = {doc.metadata["source_type"] for doc in docs}

    assert "repo_overview" in source_types
    assert "repo_manifest" in source_types
    assert any("src/app.py" in doc.page_content for doc in docs)

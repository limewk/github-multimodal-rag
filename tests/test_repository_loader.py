from pathlib import Path

from src.ingestion.repository_loader import (
    iter_repository_files,
    repo_id_from_source,
)


FIXTURE_REPO = "tests/fixtures/sample_repo"


def test_iter_repository_files_reads_text_and_image_references():
    files = list(iter_repository_files(Path(FIXTURE_REPO)))
    paths = {file.path for file in files}

    assert "README.md" in paths
    assert "app.py" in paths
    assert "docs/architecture.png" in paths


def test_repo_id_is_stable_for_same_source():
    first = repo_id_from_source(FIXTURE_REPO)
    second = repo_id_from_source(FIXTURE_REPO)

    assert first == second
    assert "sample_repo" in first

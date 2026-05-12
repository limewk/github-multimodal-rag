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


def test_iter_repository_files_prunes_ignored_dirs_and_reads_common_code_files(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.mjs").write_text("export const ok = true\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.js").write_text("module.exports = 1\n", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text('{"lockfileVersion": 3}\n', encoding="utf-8")

    files = list(iter_repository_files(tmp_path))
    paths = {file.path for file in files}

    assert "src/index.mjs" in paths
    assert "Dockerfile" in paths
    assert "node_modules/ignored.js" not in paths
    assert "package-lock.json" not in paths

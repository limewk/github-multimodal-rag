import subprocess

import pytest

from src.processing.ocr import (
    OCR_STATUS_DEGRADED,
    OCR_STATUS_EMPTY,
    OCR_STATUS_OK,
    OCR_STATUS_TIMEOUT,
    OCR_STATUS_UNAVAILABLE,
    clear_ocr_caches,
    extract_image_text_from_bytes,
)


@pytest.fixture(autouse=True)
def _clear_ocr_cache():
    clear_ocr_caches()
    yield
    clear_ocr_caches()


def test_extract_image_text_returns_text(monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_LANGS", "eng+chi_sim")

    def fake_run(command, **kwargs):
        if "--list-langs" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="List of available languages (2):\neng\nchi_sim\n",
                stderr="",
            )
        return subprocess.CompletedProcess(command, 0, stdout="Hello OCR\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = extract_image_text_from_bytes(b"image-bytes", suffix=".png")

    assert result.status == OCR_STATUS_OK
    assert result.text == "Hello OCR"
    assert result.languages == "eng+chi_sim"
    assert result.char_count == len("Hello OCR")


def test_extract_image_text_degrades_when_language_missing(monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_LANGS", "eng+chi_sim")

    def fake_run(command, **kwargs):
        if "--list-langs" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="List of available languages (1):\neng\n",
                stderr="",
            )
        assert command[-1] == "eng"
        return subprocess.CompletedProcess(command, 0, stdout="Only English\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = extract_image_text_from_bytes(b"image-bytes", suffix=".jpg")

    assert result.status == OCR_STATUS_DEGRADED
    assert result.text == "Only English"
    assert result.languages == "eng"
    assert result.missing_languages == ("chi_sim",)


def test_extract_image_text_returns_unavailable_without_tesseract(monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")

    def fake_run(command, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = extract_image_text_from_bytes(b"image-bytes", suffix=".png")

    assert result.status == OCR_STATUS_UNAVAILABLE
    assert "not found" in (result.error or "")


def test_extract_image_text_handles_timeout(monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_LANGS", "eng")
    monkeypatch.setenv("OCR_TIMEOUT_SECONDS", "3")

    def fake_run(command, **kwargs):
        if "--list-langs" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="List of available languages (1):\neng\n",
                stderr="",
            )
        raise subprocess.TimeoutExpired(command, timeout=3)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = extract_image_text_from_bytes(b"image-bytes", suffix=".png")

    assert result.status == OCR_STATUS_TIMEOUT
    assert "timed out" in (result.error or "")


def test_extract_image_text_handles_empty_result(monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_LANGS", "eng")

    def fake_run(command, **kwargs):
        if "--list-langs" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="List of available languages (1):\neng\n",
                stderr="",
            )
        return subprocess.CompletedProcess(command, 0, stdout="\n\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = extract_image_text_from_bytes(b"image-bytes", suffix=".png")

    assert result.status == OCR_STATUS_EMPTY
    assert result.text == ""

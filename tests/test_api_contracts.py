from fastapi.testclient import TestClient

from src.api.main import app
from src.processing.ocr import OCR_STATUS_OK, OCR_STATUS_UNAVAILABLE, OCRResult


def test_routes_are_registered():
    client = TestClient(app)

    health = client.get("/health")

    assert health.status_code == 200
    paths = {route.path for route in app.routes}
    assert "/chat" in paths
    assert "/repos/index" in paths


def test_upload_image_returns_ocr_text(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(
        "src.api.upload.extract_image_text_from_bytes",
        lambda raw, suffix: OCRResult(text="Diagram Title", status=OCR_STATUS_OK, languages="eng"),
    )

    response = client.post(
        "/upload/",
        files={"file": ("diagram.png", b"png-bytes", "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "image"
    assert data["text"] == "Diagram Title"
    assert data["char_count"] == len("Diagram Title")
    assert data["ocr_status"] == OCR_STATUS_OK
    assert data["ocr_languages"] == "eng"
    assert data["image_base64"]


def test_upload_image_keeps_working_when_ocr_unavailable(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(
        "src.api.upload.extract_image_text_from_bytes",
        lambda raw, suffix: OCRResult(
            status=OCR_STATUS_UNAVAILABLE,
            requested_languages=("eng", "chi_sim"),
            missing_languages=("chi_sim",),
            error="Tesseract command not found: tesseract",
        ),
    )

    response = client.post(
        "/upload/",
        files={"file": ("scan.jpg", b"jpg-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "image"
    assert data["text"] is None
    assert data["ocr_status"] == OCR_STATUS_UNAVAILABLE
    assert data["ocr_missing_languages"] == ["chi_sim"]
    assert data["ocr_error"]
    assert data["image_base64"]

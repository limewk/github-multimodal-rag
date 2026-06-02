from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


OCR_STATUS_NOT_APPLICABLE = "not_applicable"
OCR_STATUS_DISABLED = "disabled"
OCR_STATUS_OK = "ok"
OCR_STATUS_DEGRADED = "degraded"
OCR_STATUS_EMPTY = "empty"
OCR_STATUS_UNAVAILABLE = "unavailable"
OCR_STATUS_TIMEOUT = "timeout"
OCR_STATUS_ERROR = "error"


@dataclass(frozen=True)
class OCRResult:
    text: str = ""
    status: str = OCR_STATUS_NOT_APPLICABLE
    languages: str = ""
    requested_languages: tuple[str, ...] = ()
    missing_languages: tuple[str, ...] = ()
    error: str | None = None
    truncated: bool = False

    @property
    def char_count(self) -> int:
        return len(self.text)

    def metadata(self) -> dict:
        return {
            "ocr_status": self.status,
            "ocr_languages": self.languages,
            "ocr_requested_languages": list(self.requested_languages),
            "ocr_missing_languages": list(self.missing_languages),
            "ocr_error": self.error,
            "ocr_truncated": self.truncated,
            "ocr_char_count": self.char_count,
        }


@dataclass(frozen=True)
class OCRConfig:
    enabled: bool
    command: str
    requested_languages: tuple[str, ...]
    timeout_seconds: int
    max_text_chars: int


def extract_image_text_from_bytes(raw: bytes, suffix: str = ".png") -> OCRResult:
    config = _config()
    if not config.enabled:
        return OCRResult(status=OCR_STATUS_DISABLED)

    command = [config.command, "stdin", "stdout"]
    return _extract_image_text(command, config=config, input_data=raw)


def extract_image_text_from_path(path: Path, config: OCRConfig | None = None) -> OCRResult:
    config = config or _config()
    if not config.enabled:
        return OCRResult(status=OCR_STATUS_DISABLED)

    command = [config.command, str(path), "stdout"]
    return _extract_image_text(command, config=config)


def clear_ocr_caches() -> None:
    _available_languages.cache_clear()


def _extract_image_text(
    command: list[str],
    config: OCRConfig,
    input_data: bytes | None = None,
) -> OCRResult:
    selected, missing, probe_error = _select_languages(config)
    if probe_error:
        return OCRResult(
            status=OCR_STATUS_UNAVAILABLE,
            requested_languages=config.requested_languages,
            missing_languages=missing,
            error=probe_error,
        )
    if config.requested_languages and not selected:
        return OCRResult(
            status=OCR_STATUS_UNAVAILABLE,
            requested_languages=config.requested_languages,
            missing_languages=missing,
            error="Requested OCR language data is not installed.",
        )

    if selected:
        command.extend(["-l", "+".join(selected)])

    try:
        completed = subprocess.run(
            command,
            input=input_data,
            capture_output=True,
            timeout=config.timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return OCRResult(
            status=OCR_STATUS_UNAVAILABLE,
            requested_languages=config.requested_languages,
            missing_languages=missing,
            error=f"Tesseract command not found: {config.command}",
        )
    except subprocess.TimeoutExpired:
        return OCRResult(
            status=OCR_STATUS_TIMEOUT,
            languages="+".join(selected),
            requested_languages=config.requested_languages,
            missing_languages=missing,
            error=f"OCR timed out after {config.timeout_seconds} seconds.",
        )
    except Exception as exc:
        return OCRResult(
            status=OCR_STATUS_ERROR,
            languages="+".join(selected),
            requested_languages=config.requested_languages,
            missing_languages=missing,
            error=str(exc) or exc.__class__.__name__,
        )

    stdout = _decode_output(completed.stdout)
    stderr = _decode_output(completed.stderr).strip()
    if completed.returncode != 0:
        return OCRResult(
            status=_status_for_tesseract_error(stderr),
            languages="+".join(selected),
            requested_languages=config.requested_languages,
            missing_languages=missing,
            error=stderr or f"Tesseract exited with code {completed.returncode}.",
        )

    text = _normalize_text(stdout)
    text, truncated = _truncate(text, config.max_text_chars)
    status = OCR_STATUS_DEGRADED if text and missing else OCR_STATUS_OK if text else OCR_STATUS_EMPTY
    return OCRResult(
        text=text,
        status=status,
        languages="+".join(selected),
        requested_languages=config.requested_languages,
        missing_languages=missing,
        error=None,
        truncated=truncated,
    )


def _config() -> OCRConfig:
    return OCRConfig(
        enabled=_truthy(os.getenv("OCR_ENABLED", "true")),
        command=os.getenv("OCR_TESSERACT_CMD", "tesseract").strip() or "tesseract",
        requested_languages=_parse_languages(os.getenv("OCR_LANGS", "eng+chi_sim")),
        timeout_seconds=_positive_int(os.getenv("OCR_TIMEOUT_SECONDS"), 20),
        max_text_chars=_positive_int(os.getenv("OCR_MAX_TEXT_CHARS"), 8000),
    )


def _select_languages(config: OCRConfig) -> tuple[tuple[str, ...], tuple[str, ...], str | None]:
    try:
        available = _available_languages(config.command, config.timeout_seconds)
    except FileNotFoundError:
        return (), (), f"Tesseract command not found: {config.command}"
    except subprocess.TimeoutExpired:
        return (), (), "Tesseract language detection timed out."
    except Exception as exc:
        return config.requested_languages, (), str(exc) or exc.__class__.__name__

    if not available:
        return config.requested_languages, (), None

    available_set = set(available)
    requested = config.requested_languages
    if not requested:
        selected = tuple(lang for lang in available if lang != "osd")
        return selected, (), None

    selected = tuple(lang for lang in requested if lang in available_set)
    missing = tuple(lang for lang in requested if lang not in available_set)
    return selected, missing, None


@lru_cache(maxsize=8)
def _available_languages(command: str, timeout_seconds: int) -> tuple[str, ...]:
    completed = subprocess.run(
        [command, "--list-langs"],
        capture_output=True,
        text=True,
        timeout=min(timeout_seconds, 8),
        check=False,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(message or f"{command} --list-langs failed.")

    lines = f"{completed.stdout}\n{completed.stderr}".splitlines()
    languages = []
    for line in lines:
        value = line.strip()
        if not value or value.lower().startswith("list of available languages"):
            continue
        languages.append(value)
    return tuple(dict.fromkeys(languages))


def _parse_languages(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    parts = [part.strip() for part in re.split(r"[+,\s;]+", value) if part.strip()]
    return tuple(dict.fromkeys(parts))


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() not in {"0", "false", "no", "off", "disabled"}


def _positive_int(value: str | None, default: int) -> int:
    try:
        parsed = int(str(value).strip())
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _status_for_tesseract_error(stderr: str) -> str:
    lowered = stderr.lower()
    if "failed loading language" in lowered or "error opening data file" in lowered:
        return OCR_STATUS_UNAVAILABLE
    return OCR_STATUS_ERROR


def _normalize_text(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines).strip()


def _decode_output(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _truncate(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "\n\n[OCR 内容已截断]", True

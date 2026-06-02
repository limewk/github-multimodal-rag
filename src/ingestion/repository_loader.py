import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from src.processing.ocr import OCRResult, extract_image_text_from_path


TEXT_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".json",
    ".kt",
    ".md",
    ".mdx",
    ".mjs",
    ".cjs",
    ".py",
    ".php",
    ".proto",
    ".rb",
    ".rst",
    ".rs",
    ".scala",
    ".sh",
    ".svelte",
    ".swift",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}

TEXT_FILE_NAMES = {
    "BUILD",
    "Dockerfile",
    "Jenkinsfile",
    "Makefile",
    "MODULE.bazel",
    "WORKSPACE",
}

IGNORED_DIRS = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "data",
    "dist",
    "env",
    "node_modules",
    "target",
    "venv",
}

IGNORED_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".DS_Store",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "yarn.lock",
}

IGNORED_DIR_NAMES_LOWER = {value.lower() for value in IGNORED_DIRS}
IGNORED_FILE_NAMES_LOWER = {value.lower() for value in IGNORED_FILE_NAMES}

IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".tif", ".tiff", ".webp"}
MAX_TEXT_FILE_BYTES = int(os.getenv("RAG_MAX_TEXT_FILE_BYTES", "1048576"))
GIT_LS_FILES_TIMEOUT_SECONDS = int(os.getenv("RAG_GIT_LS_FILES_TIMEOUT_SECONDS", "60"))


@dataclass(frozen=True)
class RepositoryFile:
    path: str
    content: str
    source_type: str
    language: str | None = None
    metadata: dict = field(default_factory=dict)


def repo_id_from_source(source: str) -> str:
    """Create a stable id for either a GitHub URL or a local path."""
    normalized = source.strip().rstrip("/\\")
    parsed = urlparse(normalized)
    if parsed.netloc:
        slug = re.sub(r"\.git$", "", parsed.path.strip("/")).replace("/", "__")
        basis = normalized.lower()
    else:
        path = Path(normalized).resolve()
        slug = path.name
        basis = str(path).lower()
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:10]
    safe_slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", slug) or "repo"
    return f"{safe_slug}-{digest}"


def resolve_repository_source(source: str, branch: str = "main") -> tuple[str, Path]:
    """
    Resolve a local path or clone a GitHub repository into data/repos.
    Returns the stable repo_id and a local filesystem path.
    """
    repo_id = repo_id_from_source(source)
    local_path = Path(source).expanduser()
    if local_path.exists():
        return repo_id, local_path.resolve()

    parsed = urlparse(source)
    if parsed.scheme not in {"http", "https", "git", "ssh"}:
        raise ValueError(f"Repository source does not exist and is not a URL: {source}")

    target_dir = Path(os.getenv("RAG_REPO_CACHE_DIR", "data/repos")) / repo_id
    if target_dir.exists():
        return repo_id, target_dir.resolve()

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    command = ["git", "clone", "--depth", "1"]
    if branch:
        command.extend(["--branch", branch])
    command.extend([source, str(target_dir)])

    try:
        _run_git_command(command, timeout=300)
    except Exception as exc:
        if branch == "main":
            shutil.rmtree(target_dir, ignore_errors=True)
            fallback_command = [
                "git",
                "clone",
                "--depth",
                "1",
                source,
                str(target_dir),
            ]
            try:
                _run_git_command(fallback_command, timeout=300)
            except Exception as fallback_exc:
                if target_dir.exists():
                    shutil.rmtree(target_dir, ignore_errors=True)
                raise RuntimeError(
                    f"Failed to clone repository {source}: {fallback_exc}"
                ) from fallback_exc
        else:
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to clone repository {source}: {exc}") from exc

    return repo_id, target_dir.resolve()


def iter_repository_files(repo_path: Path) -> Iterable[RepositoryFile]:
    root = repo_path.resolve()
    for path in _iter_candidate_paths(root):
        if not path.is_file() or _is_ignored(path, root):
            continue

        suffix = path.suffix.lower()
        rel_path = path.relative_to(root).as_posix()

        if suffix in IMAGE_EXTENSIONS:
            ocr = extract_image_text_from_path(path)
            yield RepositoryFile(
                path=rel_path,
                content=_image_reference_content(rel_path, ocr),
                source_type="image_reference",
                language=None,
                metadata=ocr.metadata(),
            )
            continue

        if not _is_supported_text_path(path) or path.stat().st_size > MAX_TEXT_FILE_BYTES:
            continue

        if _looks_binary(path):
            continue

        content = _read_text(path)
        if not content.strip():
            continue

        yield RepositoryFile(
            path=rel_path,
            content=content,
            source_type=_source_type_for_path(path),
            language=_language_for_path(path),
        )


def iter_github_issues(source: str, limit: int = 50) -> Iterable[RepositoryFile]:
    token = os.getenv("GITHUB_TOKEN")
    repo_name = _github_repo_name(source)
    if not token or not repo_name:
        return []


def _image_reference_content(rel_path: str, ocr: OCRResult) -> str:
    lines = [
        f"Image asset found in repository: {rel_path}",
        f"OCR status: {ocr.status}",
    ]
    if ocr.languages:
        lines.append(f"OCR languages: {ocr.languages}")
    if ocr.missing_languages:
        lines.append(f"OCR missing languages: {', '.join(ocr.missing_languages)}")
    if ocr.error:
        lines.append(f"OCR note: {ocr.error}")
    if ocr.text:
        lines.extend(["", "OCR text:", ocr.text])
    else:
        lines.append("OCR text: (none)")
    return "\n".join(lines)

    try:
        from github import Github

        repo = Github(token).get_repo(repo_name)
        files = []
        for issue in repo.get_issues(state="open")[:limit]:
            labels = ", ".join(label.name for label in issue.labels)
            body = issue.body or ""
            content = (
                f"# Issue #{issue.number}: {issue.title}\n\n"
                f"State: {issue.state}\n"
                f"Labels: {labels}\n"
                f"URL: {issue.html_url}\n\n"
                f"{body}"
            )
            files.append(
                RepositoryFile(
                    path=f"issues/{issue.number}.md",
                    content=content,
                    source_type="issue",
                    language="markdown",
                )
            )
        return files
    except Exception:
        return []


def _iter_candidate_paths(root: Path) -> Iterable[Path]:
    if _should_use_git_ls_files(root):
        git_paths = _git_ls_files(root)
        if git_paths is not None:
            for rel_path in git_paths:
                path = (root / rel_path).resolve()
                if _is_relative_to(path, root):
                    yield path
            return

    for current_root, dirnames, filenames in os.walk(root):
        current_path = Path(current_root)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not _is_ignored_name(dirname, IGNORED_DIR_NAMES_LOWER)
        ]
        for filename in filenames:
            if _is_ignored_name(filename, IGNORED_FILE_NAMES_LOWER):
                continue
            yield current_path / filename


def _should_use_git_ls_files(root: Path) -> bool:
    return (
        os.getenv("RAG_USE_GIT_LS_FILES", "true").lower() not in {"0", "false", "no"}
        and (root / ".git").exists()
    )


def _git_ls_files(root: Path) -> list[str] | None:
    try:
        result = _run_git_command(
            ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard"],
            timeout=GIT_LS_FILES_TIMEOUT_SECONDS,
        )
    except Exception:
        return None

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _run_git_command(command: list[str], timeout: int):
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _is_ignored(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(_is_ignored_name(part, IGNORED_DIR_NAMES_LOWER) for part in parts[:-1]) or (
        bool(parts) and _is_ignored_name(parts[-1], IGNORED_FILE_NAMES_LOWER)
    )


def _is_ignored_name(name: str, ignored_names_lower: set[str]) -> bool:
    return name.lower() in ignored_names_lower


def _is_supported_text_path(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS or path.name in TEXT_FILE_NAMES


def _looks_binary(path: Path, sample_size: int = 4096) -> bool:
    try:
        with path.open("rb") as file:
            sample = file.read(sample_size)
    except OSError:
        return True

    if b"\0" in sample:
        return True
    if not sample:
        return False

    control_bytes = sum(
        1
        for byte in sample
        if byte < 9 or (13 < byte < 32)
    )
    return control_bytes / len(sample) > 0.30


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def _source_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".mdx"}:
        return "markdown"
    if suffix in {".txt"}:
        return "text"
    return "code"


def _language_for_path(path: Path) -> str | None:
    mapping = {
        ".c": "c",
        ".cc": "cpp",
        ".cpp": "cpp",
        ".cs": "csharp",
        ".css": "css",
        ".go": "go",
        ".h": "c",
        ".hpp": "cpp",
        ".html": "html",
        ".java": "java",
        ".js": "js",
        ".jsx": "jsx",
        ".json": "json",
        ".kt": "kotlin",
        ".md": "markdown",
        ".mdx": "markdown",
        ".mjs": "js",
        ".cjs": "js",
        ".php": "php",
        ".proto": "protobuf",
        ".py": "python",
        ".rb": "ruby",
        ".rst": "rst",
        ".rs": "rust",
        ".scala": "scala",
        ".sh": "bash",
        ".svelte": "svelte",
        ".swift": "swift",
        ".sql": "sql",
        ".toml": "toml",
        ".ts": "ts",
        ".tsx": "tsx",
        ".vue": "vue",
        ".xml": "xml",
        ".yaml": "yaml",
        ".yml": "yaml",
    }
    if path.name == "Dockerfile":
        return "dockerfile"
    if path.name == "Makefile":
        return "makefile"
    return mapping.get(path.suffix.lower())


def _github_repo_name(source: str) -> str | None:
    parsed = urlparse(source)
    if "github.com" not in parsed.netloc.lower():
        return None
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        return None
    repo = re.sub(r"\.git$", "", parts[1])
    return f"{parts[0]}/{repo}"

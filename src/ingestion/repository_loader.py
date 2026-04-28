import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


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
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
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

IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
MAX_TEXT_FILE_BYTES = int(os.getenv("RAG_MAX_TEXT_FILE_BYTES", "1048576"))


@dataclass(frozen=True)
class RepositoryFile:
    path: str
    content: str
    source_type: str
    language: str | None = None


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
    command = [
        "git",
        "clone",
        "--depth",
        "1",
        "--branch",
        branch,
        source,
        str(target_dir),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
    except Exception as exc:
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        raise RuntimeError(f"Failed to clone repository {source}: {exc}") from exc

    return repo_id, target_dir.resolve()


def iter_repository_files(repo_path: Path) -> Iterable[RepositoryFile]:
    for path in repo_path.rglob("*"):
        if not path.is_file() or _is_ignored(path, repo_path):
            continue

        suffix = path.suffix.lower()
        rel_path = path.relative_to(repo_path).as_posix()

        if suffix in IMAGE_EXTENSIONS:
            yield RepositoryFile(
                path=rel_path,
                content=f"Image asset found in repository: {rel_path}",
                source_type="image_reference",
                language=None,
            )
            continue

        if suffix not in TEXT_EXTENSIONS or path.stat().st_size > MAX_TEXT_FILE_BYTES:
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


def _is_ignored(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in IGNORED_DIRS for part in parts)


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
        ".py": "python",
        ".rb": "ruby",
        ".rs": "rust",
        ".sh": "bash",
        ".sql": "sql",
        ".ts": "ts",
        ".tsx": "tsx",
        ".vue": "vue",
        ".xml": "xml",
        ".yaml": "yaml",
        ".yml": "yaml",
    }
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

import re
from collections import Counter
from bisect import bisect_right
from collections.abc import Iterable, Iterator

from langchain_core.documents import Document
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter


CODE_LANGUAGE_MAP = {
    "cpp": Language.CPP,
    "go": Language.GO,
    "java": Language.JAVA,
    "js": Language.JS,
    "jsx": Language.JS,
    "kotlin": Language.KOTLIN,
    "python": Language.PYTHON,
    "ruby": Language.RUBY,
    "rust": Language.RUST,
    "ts": Language.TS,
    "tsx": Language.TS,
}

IMAGE_MARKDOWN_PATTERN = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)]+)\)")
MANIFEST_FILES_PER_DOCUMENT = 200

def split_markdown(text: str) -> list:
    """
    对 Markdown 文本文档进行切分
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)

def split_code(code: str, language: Language) -> list:
    """
    基于特定编程语言（如 Python, JS）的语法树特征切分代码。
    这样可以尽量保持函数或类作为一个完整的块。
    """
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=language, 
        chunk_size=500, 
        chunk_overlap=50
    )
    return splitter.split_text(code)


def repository_file_to_documents(repo_id: str, repo_file) -> list[Document]:
    """
    Convert an ingested repository file into chunked LangChain Documents.
    Metadata is kept consistent across code, markdown, text, and image references.
    """
    return list(iter_repository_file_documents(repo_id, repo_file))


def iter_repository_file_documents(repo_id: str, repo_file) -> Iterator[Document]:
    if repo_file.source_type == "image_reference":
        yield Document(
            page_content=repo_file.content,
            metadata=_base_metadata(repo_id, repo_file, 0, 1, 1),
        )
        return

    chunks = _split_by_source(repo_file.content, repo_file.source_type, repo_file.language)
    search_offset = 0
    line_locator = _LineLocator(repo_file.content)
    text_chunk_count = 0
    for chunk_id, chunk in enumerate(chunks):
        if not chunk.strip():
            continue

        start_line, end_line, search_offset = line_locator.locate(chunk, search_offset)
        text_chunk_count += 1
        yield Document(
            page_content=chunk,
            metadata=_base_metadata(
                repo_id, repo_file, chunk_id, start_line, end_line
            ),
        )

    if repo_file.source_type == "markdown":
        yield from _image_reference_documents(repo_id, repo_file, text_chunk_count)


def repository_files_to_documents(repo_id: str, files: Iterable) -> list[Document]:
    return list(iter_repository_documents(repo_id, files))


def iter_repository_documents(repo_id: str, files: Iterable) -> Iterator[Document]:
    manifest_entries = []
    for repo_file in files:
        manifest_entries.append(
            {
                "path": repo_file.path,
                "source_type": repo_file.source_type,
                "language": repo_file.language or "unknown",
            }
        )
        yield from iter_repository_file_documents(repo_id, repo_file)
    yield from _repository_manifest_documents(repo_id, manifest_entries)


def _split_by_source(text: str, source_type: str, language: str | None) -> list[str]:
    if source_type == "markdown":
        return split_markdown(text)
    if source_type == "code":
        lang = CODE_LANGUAGE_MAP.get(language or "")
        if lang:
            return split_code(text, lang)
        return RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=120,
            separators=["\n\n", "\n", " ", ""],
        ).split_text(text)
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    ).split_text(text)


def _base_metadata(repo_id: str, repo_file, chunk_id: int, start_line: int, end_line: int):
    return {
        "repo_id": repo_id,
        "source_type": repo_file.source_type,
        "path": repo_file.path,
        "language": repo_file.language,
        "chunk_id": chunk_id,
        "start_line": start_line,
        "end_line": end_line,
    }


def _repository_manifest_documents(repo_id: str, entries: list[dict]) -> Iterator[Document]:
    if not entries:
        return

    yield _repo_summary_document(repo_id, entries)
    yield from _repo_file_manifest_documents(repo_id, entries)


def _repo_summary_document(repo_id: str, entries: list[dict]) -> Document:
    language_counts = Counter(entry["language"] for entry in entries)
    type_counts = Counter(entry["source_type"] for entry in entries)
    top_level_counts = Counter(_top_level_dir(entry["path"]) for entry in entries)

    language_lines = _format_counter(language_counts)
    type_lines = _format_counter(type_counts)
    directory_lines = _format_counter(top_level_counts, limit=80)

    content = (
        "Repository overview for RAG retrieval.\n"
        f"Indexed files: {len(entries)}\n\n"
        "Source types:\n"
        f"{type_lines}\n\n"
        "Languages:\n"
        f"{language_lines}\n\n"
        "Top-level directories and file counts:\n"
        f"{directory_lines}"
    )
    return Document(
        page_content=content,
        metadata={
            "repo_id": repo_id,
            "source_type": "repo_overview",
            "path": "__repo__/overview.md",
            "language": "text",
            "chunk_id": 0,
            "start_line": 1,
            "end_line": content.count("\n") + 1,
        },
    )


def _repo_file_manifest_documents(repo_id: str, entries: list[dict]) -> Iterator[Document]:
    sorted_entries = sorted(entries, key=lambda entry: entry["path"])
    for chunk_id, start in enumerate(range(0, len(sorted_entries), MANIFEST_FILES_PER_DOCUMENT), start=1):
        batch = sorted_entries[start : start + MANIFEST_FILES_PER_DOCUMENT]
        lines = [
            "Repository file manifest for RAG retrieval.",
            f"Files {start + 1}-{start + len(batch)} of {len(sorted_entries)}:",
            "",
        ]
        lines.extend(
            f"- {entry['path']} ({entry['source_type']}, {entry['language']})"
            for entry in batch
        )
        content = "\n".join(lines)
        yield Document(
            page_content=content,
            metadata={
                "repo_id": repo_id,
                "source_type": "repo_manifest",
                "path": f"__repo__/manifest_{chunk_id}.md",
                "language": "text",
                "chunk_id": chunk_id,
                "start_line": 1,
                "end_line": content.count("\n") + 1,
            },
        )


def _format_counter(counter: Counter, limit: int | None = None) -> str:
    items = counter.most_common(limit)
    if not items:
        return "- none"
    return "\n".join(f"- {name}: {count}" for name, count in items)


def _top_level_dir(path: str) -> str:
    parts = path.split("/")
    return parts[0] if len(parts) > 1 else "."


def _locate_lines(text: str, chunk: str, search_offset: int) -> tuple[int, int, int]:
    return _LineLocator(text).locate(chunk, search_offset)


class _LineLocator:
    def __init__(self, text: str):
        self.text = text
        self.line_starts = [0]
        self.line_starts.extend(match.end() for match in re.finditer("\n", text))

    def locate(self, chunk: str, search_offset: int) -> tuple[int, int, int]:
        index = self.text.find(chunk, search_offset)
        if index < 0:
            index = self.text.find(chunk)
        if index < 0:
            index = min(search_offset, len(self.text))

        start_line = bisect_right(self.line_starts, index)
        end_line = start_line + chunk.count("\n")
        return start_line, end_line, index + len(chunk)


def _image_reference_documents(repo_id: str, repo_file, first_chunk_id: int) -> list[Document]:
    documents: list[Document] = []
    for offset, match in enumerate(IMAGE_MARKDOWN_PATTERN.finditer(repo_file.content)):
        start_line = repo_file.content.count("\n", 0, match.start()) + 1
        url = match.group("url").strip()
        alt = match.group("alt").strip()
        context = _line_context(repo_file.content, start_line)
        metadata = _base_metadata(
            repo_id,
            repo_file,
            first_chunk_id + offset,
            start_line,
            start_line,
        )
        metadata.update({"source_type": "image_reference", "url": url, "alt": alt})
        documents.append(
            Document(
                page_content=f"Markdown image reference: alt={alt or '(empty)'} url={url}. Context: {context}",
                metadata=metadata,
            )
        )
    return documents


def _line_context(text: str, line_number: int, radius: int = 2) -> str:
    lines = text.splitlines()
    start = max(0, line_number - radius - 1)
    end = min(len(lines), line_number + radius)
    return "\n".join(lines[start:end]).strip()

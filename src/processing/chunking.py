"""
代码片段划分模块（已集成 AST 智能划分）

核心变更：
  - 对 Python / JS / TS / Java / C++ / Go / Rust 等支持语言，
    优先使用 ast_chunking.split_by_ast() 进行语义化划分
  - 每个 Document 的 metadata 中附加 AST 结构化元数据
    （chunk_type, name, params, return_type 等）
  - 不支持 AST 的语言继续使用 RecursiveCharacterTextSplitter
"""
import re
from collections import Counter
from bisect import bisect_right
from collections.abc import Iterable, Iterator

from langchain_core.documents import Document
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from src.processing.ast_chunking import split_by_ast


# ─────────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────────
CODE_LANGUAGE_MAP = {
    "cpp":    Language.CPP,
    "go":     Language.GO,
    "java":   Language.JAVA,
    "js":     Language.JS,
    "jsx":    Language.JS,
    "kotlin": Language.KOTLIN,
    "python": Language.PYTHON,
    "ruby":   Language.RUBY,
    "rust":   Language.RUST,
    "ts":     Language.TS,
    "tsx":    Language.TS,
}

# 优先使用 AST 划分的语言集合
AST_SUPPORTED_LANGUAGES = {
    "python", "js", "jsx", "mjs", "cjs",
    "ts", "tsx", "java", "c", "cpp", "cc",
    "h", "hpp", "go", "rs", "rust",
}

# AST chunk 最大字符数（超出则再次用字符分割）
AST_CHUNK_MAX_CHARS = 3000
# AST chunk 最小字符数（太小则跳过独立成 Document）
AST_CHUNK_MIN_CHARS = 20

IMAGE_MARKDOWN_PATTERN = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)]+)\)")
MANIFEST_FILES_PER_DOCUMENT = 200


# ─────────────────────────────────────────────────────────────────
# 公共接口
# ─────────────────────────────────────────────────────────────────
def split_markdown(text: str) -> list[str]:
    """对 Markdown 文本进行切分"""
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    ).split_text(text)


def split_code(code: str, language: Language) -> list[str]:
    """
    基于 LangChain Language 枚举对代码进行字符级划分。
    用于 AST 不支持或 AST chunk 过大时的后备方案。
    """
    return RecursiveCharacterTextSplitter.from_language(
        language=language,
        chunk_size=500,
        chunk_overlap=50,
    ).split_text(code)


def repository_file_to_documents(repo_id: str, repo_file) -> list[Document]:
    """将单个仓库文件转换为 LangChain Document 列表"""
    return list(iter_repository_file_documents(repo_id, repo_file))


def repository_files_to_documents(repo_id: str, files: Iterable) -> list[Document]:
    return list(iter_repository_documents(repo_id, files))


# ─────────────────────────────────────────────────────────────────
# 核心迭代器
# ─────────────────────────────────────────────────────────────────
def iter_repository_file_documents(repo_id: str, repo_file) -> Iterator[Document]:
    if repo_file.source_type == "image_reference":
        yield Document(
            page_content=repo_file.content,
            metadata=_base_metadata(repo_id, repo_file, 0, 1, 1),
        )
        return

    lang = repo_file.language or ""
    use_ast = (
        repo_file.source_type == "code"
        and lang.lower() in AST_SUPPORTED_LANGUAGES
    )

    if use_ast:
        yield from _iter_ast_documents(repo_id, repo_file)
    else:
        yield from _iter_char_documents(repo_id, repo_file)

    if repo_file.source_type == "markdown":
        # 额外提取 Markdown 中的图片引用
        text_chunk_count = sum(
            1 for doc in iter_repository_file_documents.__wrapped__(repo_id, repo_file)
            if doc.metadata.get("source_type") != "image_reference"
        ) if hasattr(iter_repository_file_documents, "__wrapped__") else 0
        yield from _image_reference_documents(repo_id, repo_file, text_chunk_count)


def iter_repository_documents(repo_id: str, files: Iterable) -> Iterator[Document]:
    manifest_entries = []
    for repo_file in files:
        manifest_entries.append({
            "path":        repo_file.path,
            "source_type": repo_file.source_type,
            "language":    repo_file.language or "unknown",
        })
        yield from _iter_file_docs_with_image_refs(repo_id, repo_file)
    yield from _repository_manifest_documents(repo_id, manifest_entries)


def _iter_file_docs_with_image_refs(repo_id: str, repo_file) -> Iterator[Document]:
    """统一入口：输出代码/Markdown 的 chunk Documents 和图片引用 Documents"""
    if repo_file.source_type == "image_reference":
        yield Document(
            page_content=repo_file.content,
            metadata=_base_metadata(repo_id, repo_file, 0, 1, 1),
        )
        return

    lang = repo_file.language or ""
    use_ast = (
        repo_file.source_type == "code"
        and lang.lower() in AST_SUPPORTED_LANGUAGES
    )

    text_chunk_count = 0
    if use_ast:
        for doc in _iter_ast_documents(repo_id, repo_file):
            text_chunk_count += 1
            yield doc
    else:
        for doc in _iter_char_documents(repo_id, repo_file):
            text_chunk_count += 1
            yield doc

    if repo_file.source_type == "markdown":
        yield from _image_reference_documents(repo_id, repo_file, text_chunk_count)


# ─────────────────────────────────────────────────────────────────
# AST 划分路径
# ─────────────────────────────────────────────────────────────────
def _iter_ast_documents(repo_id: str, repo_file) -> Iterator[Document]:
    """使用 AST 划分代码文件，每个语义单元生成一个 Document"""
    lang = (repo_file.language or "").lower()
    ast_chunks = split_by_ast(repo_file.content, lang)
    line_locator = _LineLocator(repo_file.content)

    for chunk_id, ast_chunk in enumerate(ast_chunks):
        content = ast_chunk.content.strip()
        if len(content) < AST_CHUNK_MIN_CHARS:
            continue

        # AST chunk 本身过大时再做字符级子切分
        if len(content) > AST_CHUNK_MAX_CHARS:
            sub_chunks = _fallback_split(content, lang)
            for sub_id, sub_content in enumerate(sub_chunks):
                if not sub_content.strip():
                    continue
                start_line, end_line, _ = line_locator.locate(sub_content, 0)
                meta = _base_metadata(repo_id, repo_file, chunk_id * 1000 + sub_id, start_line, end_line)
                meta.update(ast_chunk.to_metadata_dict())
                meta["ast_sub_chunk"] = True
                yield Document(page_content=sub_content, metadata=meta)
        else:
            meta = _base_metadata(repo_id, repo_file, chunk_id, ast_chunk.start_line, ast_chunk.end_line)
            meta.update(ast_chunk.to_metadata_dict())
            yield Document(page_content=content, metadata=meta)


# ─────────────────────────────────────────────────────────────────
# 字符级划分路径（后备方案）
# ─────────────────────────────────────────────────────────────────
def _iter_char_documents(repo_id: str, repo_file) -> Iterator[Document]:
    """使用 RecursiveCharacterTextSplitter 划分文件"""
    chunks = _split_by_source(repo_file.content, repo_file.source_type, repo_file.language)
    search_offset = 0
    line_locator = _LineLocator(repo_file.content)

    for chunk_id, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        start_line, end_line, search_offset = line_locator.locate(chunk, search_offset)
        yield Document(
            page_content=chunk,
            metadata=_base_metadata(repo_id, repo_file, chunk_id, start_line, end_line),
        )


def _split_by_source(text: str, source_type: str, language: str | None) -> list[str]:
    if source_type == "markdown":
        return split_markdown(text)
    if source_type == "code":
        lang = CODE_LANGUAGE_MAP.get((language or "").lower())
        if lang:
            return split_code(text, lang)
        return RecursiveCharacterTextSplitter(
            chunk_size=800, chunk_overlap=120,
            separators=["\n\n", "\n", " ", ""],
        ).split_text(text)
    return RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    ).split_text(text)


def _fallback_split(content: str, language: str) -> list[str]:
    """对过大的 AST chunk 进行二次字符级划分"""
    lang = CODE_LANGUAGE_MAP.get(language)
    if lang:
        return split_code(content, lang)
    return RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""],
    ).split_text(content)


# ─────────────────────────────────────────────────────────────────
# 元数据构建
# ─────────────────────────────────────────────────────────────────
def _base_metadata(repo_id: str, repo_file, chunk_id: int,
                   start_line: int, end_line: int) -> dict:
    meta = {
        "repo_id":     repo_id,
        "source_type": repo_file.source_type,
        "path":        repo_file.path,
        "language":    repo_file.language,
        "chunk_id":    chunk_id,
        "start_line":  start_line,
        "end_line":    end_line,
    }
    for key, value in (getattr(repo_file, "metadata", None) or {}).items():
        if value is not None:
            meta[key] = value
    return meta


# ─────────────────────────────────────────────────────────────────
# 仓库清单文档
# ─────────────────────────────────────────────────────────────────
def _repository_manifest_documents(repo_id: str, entries: list[dict]) -> Iterator[Document]:
    if not entries:
        return
    yield _repo_summary_document(repo_id, entries)
    yield from _repo_file_manifest_documents(repo_id, entries)


def _repo_summary_document(repo_id: str, entries: list[dict]) -> Document:
    language_counts = Counter(e["language"] for e in entries)
    type_counts     = Counter(e["source_type"] for e in entries)
    top_level       = Counter(_top_level_dir(e["path"]) for e in entries)
    content = (
        "Repository overview for RAG retrieval.\n"
        f"Indexed files: {len(entries)}\n\n"
        "Source types:\n"   + _format_counter(type_counts)     + "\n\n"
        "Languages:\n"      + _format_counter(language_counts) + "\n\n"
        "Top-level directories and file counts:\n"
        + _format_counter(top_level, limit=80)
    )
    return Document(
        page_content=content,
        metadata={
            "repo_id": repo_id, "source_type": "repo_overview",
            "path": "__repo__/overview.md", "language": "text",
            "chunk_id": 0, "start_line": 1,
            "end_line": content.count("\n") + 1,
        },
    )


def _repo_file_manifest_documents(repo_id: str, entries: list[dict]) -> Iterator[Document]:
    sorted_entries = sorted(entries, key=lambda e: e["path"])
    for chunk_id, start in enumerate(range(0, len(sorted_entries), MANIFEST_FILES_PER_DOCUMENT), 1):
        batch = sorted_entries[start: start + MANIFEST_FILES_PER_DOCUMENT]
        lines = [
            "Repository file manifest for RAG retrieval.",
            f"Files {start + 1}-{start + len(batch)} of {len(sorted_entries)}:",
            "",
        ]
        lines.extend(
            f"- {e['path']} ({e['source_type']}, {e['language']})" for e in batch
        )
        content = "\n".join(lines)
        yield Document(
            page_content=content,
            metadata={
                "repo_id": repo_id, "source_type": "repo_manifest",
                "path": f"__repo__/manifest_{chunk_id}.md", "language": "text",
                "chunk_id": chunk_id, "start_line": 1,
                "end_line": content.count("\n") + 1,
            },
        )


# ─────────────────────────────────────────────────────────────────
# 图片引用文档
# ─────────────────────────────────────────────────────────────────
def _image_reference_documents(repo_id: str, repo_file, first_chunk_id: int) -> list[Document]:
    docs: list[Document] = []
    for offset, match in enumerate(IMAGE_MARKDOWN_PATTERN.finditer(repo_file.content)):
        start_line = repo_file.content.count("\n", 0, match.start()) + 1
        url = match.group("url").strip()
        alt = match.group("alt").strip()
        context = _line_context(repo_file.content, start_line)
        meta = _base_metadata(repo_id, repo_file, first_chunk_id + offset, start_line, start_line)
        meta.update({"source_type": "image_reference", "url": url, "alt": alt})
        docs.append(Document(
            page_content=f"Markdown image reference: alt={alt or '(empty)'} url={url}. Context: {context}",
            metadata=meta,
        ))
    return docs


# ─────────────────────────────────────────────────────────────────
# 辅助工具
# ─────────────────────────────────────────────────────────────────
class _LineLocator:
    def __init__(self, text: str):
        self.text = text
        self.line_starts = [0]
        self.line_starts.extend(m.end() for m in re.finditer("\n", text))

    def locate(self, chunk: str, search_offset: int) -> tuple[int, int, int]:
        index = self.text.find(chunk, search_offset)
        if index < 0:
            index = self.text.find(chunk)
        if index < 0:
            index = min(search_offset, len(self.text))
        start_line = bisect_right(self.line_starts, index)
        end_line   = start_line + chunk.count("\n")
        return start_line, end_line, index + len(chunk)


def _format_counter(counter: Counter, limit: int | None = None) -> str:
    items = counter.most_common(limit)
    if not items:
        return "- none"
    return "\n".join(f"- {name}: {count}" for name, count in items)


def _top_level_dir(path: str) -> str:
    parts = path.split("/")
    return parts[0] if len(parts) > 1 else "."


def _line_context(text: str, line_number: int, radius: int = 2) -> str:
    lines = text.splitlines()
    start = max(0, line_number - radius - 1)
    end   = min(len(lines), line_number + radius)
    return "\n".join(lines[start:end]).strip()

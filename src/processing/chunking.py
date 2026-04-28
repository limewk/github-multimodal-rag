import re
from collections.abc import Iterable

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
    if repo_file.source_type == "image_reference":
        return [
            Document(
                page_content=repo_file.content,
                metadata=_base_metadata(repo_id, repo_file, 0, 1, 1),
            )
        ]

    chunks = _split_by_source(repo_file.content, repo_file.source_type, repo_file.language)
    documents: list[Document] = []
    search_offset = 0
    for chunk_id, chunk in enumerate(chunks):
        if not chunk.strip():
            continue

        start_line, end_line, search_offset = _locate_lines(
            repo_file.content, chunk, search_offset
        )
        documents.append(
            Document(
                page_content=chunk,
                metadata=_base_metadata(
                    repo_id, repo_file, chunk_id, start_line, end_line
                ),
            )
        )

    if repo_file.source_type == "markdown":
        documents.extend(_image_reference_documents(repo_id, repo_file, len(documents)))

    return documents


def repository_files_to_documents(repo_id: str, files: Iterable) -> list[Document]:
    documents: list[Document] = []
    for repo_file in files:
        documents.extend(repository_file_to_documents(repo_id, repo_file))
    return documents


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


def _locate_lines(text: str, chunk: str, search_offset: int) -> tuple[int, int, int]:
    index = text.find(chunk, search_offset)
    if index < 0:
        index = text.find(chunk)
    if index < 0:
        index = search_offset

    start_line = text.count("\n", 0, index) + 1
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

"""
基于 AST（抽象语法树）的智能代码片段划分模块

支持语言：
  - Python  : 使用内置 ast 模块（精确）
  - JS/JSX  : 基于正则的 AST 式解析
  - TS/TSX  : 在 JS 基础上增加 interface / type / namespace / enum
  - Java    : 基于正则解析 class / interface / method
  - C/C++   : 基于正则解析 class / struct / function
  - Go      : 基于正则解析 func / struct / interface
  - Rust    : 基于正则解析 fn / struct / trait / impl / enum

每个 CodeChunk 包含丰富的结构化元数据，可直接用于 RAG 索引。
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────
# 数据模型
# ─────────────────────────────────────────────────────────────────
@dataclass
class CodeChunk:
    """表示一个具有语义意义的代码片段及其元数据"""
    content:          str
    chunk_type:       str            # function | class | method | interface | namespace | module | struct | trait | enum | type | impl
    name:             str
    start_line:       int
    end_line:         int
    params:           list[str]      = field(default_factory=list)
    return_type:      Optional[str]  = None
    decorators:       list[str]      = field(default_factory=list)
    is_async:         bool           = False
    base_classes:     list[str]      = field(default_factory=list)
    docstring:        Optional[str]  = None
    is_exported:      bool           = False
    access_modifier:  Optional[str]  = None  # public | private | protected
    language:         Optional[str]  = None

    def to_metadata_dict(self) -> dict:
        """转换为可存入向量数据库的元数据字典"""
        return {
            "ast_chunk_type":    self.chunk_type,
            "ast_name":          self.name,
            "ast_params":        ", ".join(self.params) if self.params else "",
            "ast_return_type":   self.return_type or "",
            "ast_decorators":    ", ".join(self.decorators) if self.decorators else "",
            "ast_is_async":      self.is_async,
            "ast_base_classes":  ", ".join(self.base_classes) if self.base_classes else "",
            "ast_docstring":     (self.docstring or "")[:200],
            "ast_is_exported":   self.is_exported,
            "ast_access":        self.access_modifier or "",
        }


# ─────────────────────────────────────────────────────────────────
# 入口函数
# ─────────────────────────────────────────────────────────────────
LANGUAGE_DISPATCH = {
    "python": "_split_python",
    "js":     "_split_javascript",
    "jsx":    "_split_javascript",
    "mjs":    "_split_javascript",
    "cjs":    "_split_javascript",
    "ts":     "_split_typescript",
    "tsx":    "_split_typescript",
    "java":   "_split_java",
    "c":      "_split_cpp",
    "cpp":    "_split_cpp",
    "cc":     "_split_cpp",
    "h":      "_split_cpp",
    "hpp":    "_split_cpp",
    "go":     "_split_go",
    "rs":     "_split_rust",
    "rust":   "_split_rust",
}


def split_by_ast(code: str, language: str) -> list[CodeChunk]:
    """
    对给定代码按语言进行语义化划分，返回 CodeChunk 列表。
    不支持的语言返回整个文件作为单一 module chunk。
    """
    lang = (language or "").lower().lstrip(".")
    fn_name = LANGUAGE_DISPATCH.get(lang)

    chunks: list[CodeChunk]
    if fn_name:
        fn = globals()[fn_name]
        chunks = fn(code)
    else:
        chunks = [_module_chunk(code)]

    for chunk in chunks:
        chunk.language = lang

    return chunks if chunks else [_module_chunk(code)]


def _module_chunk(code: str) -> CodeChunk:
    return CodeChunk(
        content=code, chunk_type="module", name="(module)",
        start_line=1, end_line=code.count("\n") + 1,
    )


# ─────────────────────────────────────────────────────────────────
# Python —— 使用内置 ast 模块（精确解析）
# ─────────────────────────────────────────────────────────────────
def _split_python(code: str) -> list[CodeChunk]:
    lines = code.splitlines(keepends=True)
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return [_module_chunk(code)]

    chunks: list[CodeChunk] = []

    def visit(node, depth: int = 0) -> None:
        if depth > 2:       # 最多解析到方法层
            return
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                c = _py_func_chunk(child, lines)
                if c:
                    chunks.append(c)
            elif isinstance(child, ast.ClassDef):
                c = _py_class_chunk(child, lines)
                if c:
                    chunks.append(c)
                visit(child, depth + 1)

    visit(tree)

    if not chunks:
        return [_module_chunk(code)]
    return sorted(chunks, key=lambda c: c.start_line)


def _py_func_chunk(node: ast.FunctionDef | ast.AsyncFunctionDef,
                   lines: list[str]) -> Optional[CodeChunk]:
    try:
        s = node.lineno - 1
        e = getattr(node, "end_lineno", None) or _py_estimate_end(lines, s)
        content = "".join(lines[s:e])
        params = [_py_arg_str(a) for a in node.args.args]
        ret = None
        if node.returns:
            try:
                ret = ast.unparse(node.returns)
            except Exception:
                ret = None
        decs = []
        for d in node.decorator_list:
            try:
                decs.append(ast.unparse(d))
            except Exception:
                decs.append(getattr(d, "id", "decorator"))
        docstring = _py_docstring(node)
        return CodeChunk(
            content=content,
            chunk_type="async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
            name=node.name,
            start_line=node.lineno,
            end_line=e,
            params=params,
            return_type=ret,
            decorators=decs,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            docstring=docstring,
        )
    except Exception:
        return None


def _py_class_chunk(node: ast.ClassDef, lines: list[str]) -> Optional[CodeChunk]:
    try:
        s = node.lineno - 1
        e = getattr(node, "end_lineno", None) or _py_estimate_end(lines, s)
        content = "".join(lines[s:e])
        bases = []
        for b in node.bases:
            try:
                bases.append(ast.unparse(b))
            except Exception:
                bases.append(getattr(b, "id", "?"))
        decs = []
        for d in node.decorator_list:
            try:
                decs.append(ast.unparse(d))
            except Exception:
                decs.append(getattr(d, "id", "decorator"))
        return CodeChunk(
            content=content,
            chunk_type="class",
            name=node.name,
            start_line=node.lineno,
            end_line=e,
            base_classes=bases,
            decorators=decs,
            docstring=_py_docstring(node),
        )
    except Exception:
        return None


def _py_arg_str(arg: ast.arg) -> str:
    if arg.annotation:
        try:
            return f"{arg.arg}: {ast.unparse(arg.annotation)}"
        except Exception:
            pass
    return arg.arg


def _py_docstring(node) -> Optional[str]:
    try:
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value[:300]
    except Exception:
        pass
    return None


def _py_estimate_end(lines: list[str], start: int) -> int:
    indent = len(lines[start]) - len(lines[start].lstrip())
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.strip() and not line.strip().startswith("#"):
            if (len(line) - len(line.lstrip())) <= indent:
                return i
    return len(lines)


# ─────────────────────────────────────────────────────────────────
# JavaScript / TypeScript —— 正则式 AST 解析
# ─────────────────────────────────────────────────────────────────
def _split_javascript(code: str) -> list[CodeChunk]:
    return _split_js_common(code, has_types=False)


def _split_typescript(code: str) -> list[CodeChunk]:
    return _split_js_common(code, has_types=True)


# 按顺序匹配：越早的规则优先级越高
_JS_PATTERNS: list[tuple[str, str]] = [
    # export default class / abstract class
    (r"^(?:export\s+default\s+|export\s+)?(?:abstract\s+)?class\s+(\w+)", "class"),
    # named function declaration
    (r"^(?:export\s+default\s+|export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", "function"),
    # const/let/var arrow / function expression
    (r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>|\w+\s*=>)", "arrow_function"),
]
_TS_EXTRA_PATTERNS: list[tuple[str, str]] = [
    (r"^(?:export\s+)?interface\s+(\w+)", "interface"),
    (r"^(?:export\s+)?type\s+(\w+)\s*(?:<[^>]+>)?\s*=", "type"),
    (r"^(?:export\s+)?(?:declare\s+)?namespace\s+(\w+)", "namespace"),
    (r"^(?:export\s+)?(?:const\s+)?enum\s+(\w+)", "enum"),
]


def _split_js_common(code: str, has_types: bool) -> list[CodeChunk]:
    lines = code.splitlines()
    all_patterns = _JS_PATTERNS + (_TS_EXTRA_PATTERNS if has_types else [])
    compiled = [(re.compile(p), t) for p, t in all_patterns]

    chunks: list[CodeChunk] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].lstrip()
        matched = False
        for pattern, chunk_type in compiled:
            m = pattern.match(stripped)
            if not m:
                continue
            name = m.group(1) if m.lastindex and m.lastindex >= 1 else "anonymous"
            is_exported = bool(re.match(r"^export\b", stripped))
            is_async = bool(re.search(r"\basync\b", stripped))
            end = _find_block_end(lines, i)
            content = "\n".join(lines[i:end + 1])

            # 提取参数
            params: list[str] = []
            pm = re.search(r"\(([^)]*)\)", stripped)
            if pm and chunk_type in ("function", "arrow_function", "method"):
                params = [p.split(":")[0].strip() for p in pm.group(1).split(",") if p.strip()]

            # TypeScript 返回类型
            return_type = None
            if has_types:
                rtm = re.search(r"\)\s*:\s*([\w<>\[\]|&,\s.?]+?)\s*(?:=>|\{|;)", stripped)
                if rtm:
                    return_type = rtm.group(1).strip()

            # 基类
            base_classes: list[str] = []
            if chunk_type == "class":
                em = re.search(r"\bextends\b\s+([\w<>,\s]+?)(?:\s+implements\b|\s*\{)", stripped)
                if em:
                    base_classes = [c.strip().split("<")[0] for c in em.group(1).split(",")]

            chunks.append(CodeChunk(
                content=content, chunk_type=chunk_type, name=name,
                start_line=i + 1, end_line=end + 1,
                params=params, return_type=return_type,
                is_async=is_async, base_classes=base_classes,
                is_exported=is_exported,
            ))
            i = end + 1
            matched = True
            break
        if not matched:
            i += 1

    return chunks or [_module_chunk(code)]


# ─────────────────────────────────────────────────────────────────
# Java
# ─────────────────────────────────────────────────────────────────
_JAVA_CLASS = re.compile(
    r"^(?:(?:public|private|protected|abstract|final|static)\s+)*"
    r"(class|interface|enum|record|@interface)\s+(\w+)"
)
_JAVA_METHOD = re.compile(
    r"^(?:(?:public|private|protected|static|final|synchronized|abstract|native|default|@\w+\s*(?:\([^)]*\)\s*)?)\s+)*"
    r"([\w<>\[\]]+(?:\s+[\w<>\[\]]+)*)\s+(\w+)\s*\("
)


def _split_java(code: str) -> list[CodeChunk]:
    lines = code.splitlines()
    chunks: list[CodeChunk] = []
    for i, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line.endswith(";"):
            continue
        cm = _JAVA_CLASS.match(line)
        if cm and "{" in line:
            chunks.append(CodeChunk(
                content="\n".join(lines[i:_find_block_end(lines, i) + 1]),
                chunk_type=cm.group(1),
                name=cm.group(2),
                start_line=i + 1,
                end_line=_find_block_end(lines, i) + 1,
                access_modifier=_java_access(line),
            ))
            continue
        mm = _JAVA_METHOD.match(line)
        if mm and "{" in line:
            end = _find_block_end(lines, i)
            if end > i:
                pm = re.search(r"\(([^)]*)\)", line)
                params = [p.strip() for p in pm.group(1).split(",") if p.strip()] if pm else []
                chunks.append(CodeChunk(
                    content="\n".join(lines[i:end + 1]),
                    chunk_type="method",
                    name=mm.group(2),
                    start_line=i + 1,
                    end_line=end + 1,
                    params=params,
                    return_type=mm.group(1).strip(),
                    access_modifier=_java_access(line),
                ))
    return chunks or [_module_chunk(code)]


def _java_access(line: str) -> str:
    for mod in ("public", "private", "protected"):
        if re.search(r"\b" + mod + r"\b", line):
            return mod
    return "package-private"


# ─────────────────────────────────────────────────────────────────
# C / C++
# ─────────────────────────────────────────────────────────────────
_CPP_CLASS   = re.compile(r"^(?:template\s*<[^>]*>\s*)?(class|struct|union|enum)\s+(\w+)")
_CPP_NS      = re.compile(r"^namespace\s+(\w+)")
_CPP_FUNC    = re.compile(r"^(?:(?:virtual|static|inline|explicit|constexpr|friend|\[\[.*?\]\]|~)\s*)*"
                           r"([\w:*&<>\[\]]+(?:\s+[\w:*&<>\[\]]+)*)\s+([\w:~*&]+)\s*\(")


def _split_cpp(code: str) -> list[CodeChunk]:
    lines = code.splitlines()
    chunks: list[CodeChunk] = []
    for i, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line.startswith("//") or line.startswith("/*") or line.startswith("*"):
            continue
        if line.endswith(";") and "{" not in line:
            continue
        if "{" not in line:
            continue
        cm = _CPP_CLASS.match(line)
        if cm:
            end = _find_block_end(lines, i)
            chunks.append(CodeChunk(
                content="\n".join(lines[i:end + 1]),
                chunk_type=cm.group(1),
                name=cm.group(2),
                start_line=i + 1, end_line=end + 1,
            ))
            continue
        nm = _CPP_NS.match(line)
        if nm:
            end = _find_block_end(lines, i)
            chunks.append(CodeChunk(
                content="\n".join(lines[i:end + 1]),
                chunk_type="namespace",
                name=nm.group(1),
                start_line=i + 1, end_line=end + 1,
            ))
            continue
        fm = _CPP_FUNC.match(line)
        if fm:
            name = fm.group(2).split("::")[-1].lstrip("*&").strip()
            ret = fm.group(1).strip()
            pm = re.search(r"\(([^)]*)\)", line)
            params = [p.strip() for p in pm.group(1).split(",") if p.strip()] if pm else []
            end = _find_block_end(lines, i)
            if end > i:
                chunks.append(CodeChunk(
                    content="\n".join(lines[i:end + 1]),
                    chunk_type="function",
                    name=name,
                    start_line=i + 1, end_line=end + 1,
                    params=params, return_type=ret,
                ))
    return chunks or [_module_chunk(code)]


# ─────────────────────────────────────────────────────────────────
# Go
# ─────────────────────────────────────────────────────────────────
_GO_FUNC   = re.compile(r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(([^)]*)\)")
_GO_TYPE   = re.compile(r"^type\s+(\w+)\s+(struct|interface)")


def _split_go(code: str) -> list[CodeChunk]:
    lines = code.splitlines()
    chunks: list[CodeChunk] = []
    for i, raw_line in enumerate(lines):
        line = raw_line.strip()
        fm = _GO_FUNC.match(line)
        if fm and "{" in line:
            end = _find_block_end(lines, i)
            params = [p.strip() for p in fm.group(2).split(",") if p.strip()]
            chunks.append(CodeChunk(
                content="\n".join(lines[i:end + 1]),
                chunk_type="function",
                name=fm.group(1),
                start_line=i + 1, end_line=end + 1,
                params=params,
            ))
            continue
        tm = _GO_TYPE.match(line)
        if tm:
            end = _find_block_end(lines, i)
            chunks.append(CodeChunk(
                content="\n".join(lines[i:end + 1]),
                chunk_type=tm.group(2),
                name=tm.group(1),
                start_line=i + 1, end_line=end + 1,
            ))
    return chunks or [_module_chunk(code)]


# ─────────────────────────────────────────────────────────────────
# Rust
# ─────────────────────────────────────────────────────────────────
_RUST_ITEMS = [
    (re.compile(r"^(?:pub(?:\([^)]+\))?\s+)?(?:async\s+)?fn\s+(\w+)"), "function"),
    (re.compile(r"^(?:pub(?:\([^)]+\))?\s+)?struct\s+(\w+)"),           "struct"),
    (re.compile(r"^(?:pub(?:\([^)]+\))?\s+)?trait\s+(\w+)"),            "trait"),
    (re.compile(r"^(?:pub(?:\([^)]+\))?\s+)?enum\s+(\w+)"),             "enum"),
    (re.compile(r"^impl(?:<[^>]+>)?\s+([\w<>]+)"),                      "impl"),
    (re.compile(r"^(?:pub(?:\([^)]+\))?\s+)?mod\s+(\w+)"),              "module"),
]


def _split_rust(code: str) -> list[CodeChunk]:
    lines = code.splitlines()
    chunks: list[CodeChunk] = []
    for i, raw_line in enumerate(lines):
        line = raw_line.strip()
        if "{" not in line:
            continue
        for pattern, kind in _RUST_ITEMS:
            m = pattern.match(line)
            if not m:
                continue
            name = m.group(1)
            is_async = bool(re.search(r"\basync\b", line))
            is_exported = bool(re.match(r"^pub\b", line))
            pm = re.search(r"\(([^)]*)\)", line)
            params = [p.strip() for p in pm.group(1).split(",") if p.strip()] if pm else []
            rt_m = re.search(r"->\s*([\w<>&'[\]]+)", line)
            return_type = rt_m.group(1) if rt_m else None
            end = _find_block_end(lines, i)
            chunks.append(CodeChunk(
                content="\n".join(lines[i:end + 1]),
                chunk_type=kind,
                name=name,
                start_line=i + 1, end_line=end + 1,
                params=params, return_type=return_type,
                is_async=is_async, is_exported=is_exported,
            ))
            break
    return chunks or [_module_chunk(code)]


# ─────────────────────────────────────────────────────────────────
# 工具函数：查找代码块结尾行
# ─────────────────────────────────────────────────────────────────
def _find_block_end(lines: list[str], start: int) -> int:
    """
    从 start 行开始，通过括号深度计数找到代码块的结束行（含）。
    跳过字符串字面量中的括号。
    """
    depth = 0
    in_single = in_double = in_template = False

    for i in range(start, len(lines)):
        line = lines[i]
        j = 0
        while j < len(line):
            c = line[j]
            prev = line[j - 1] if j > 0 else ""

            if in_single:
                if c == "'" and prev != "\\":
                    in_single = False
            elif in_double:
                if c == '"' and prev != "\\":
                    in_double = False
            elif in_template:
                if c == "`" and prev != "\\":
                    in_template = False
            else:
                if c == "'":
                    in_single = True
                elif c == '"':
                    in_double = True
                elif c == "`":
                    in_template = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        return i
            j += 1

    return len(lines) - 1

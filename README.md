# GitHub 多模态 RAG 智能问答系统

本项目面向 GitHub 仓库和本地代码仓库，提供仓库索引、混合检索增强生成和流式问答能力。系统会读取代码、Markdown、文本文件和图片引用，将内容切分成带来源元数据的文档，写入 Qdrant，并在问答时结合仓库概览、文件清单、检索证据和大模型生成回答。

## 当前进展

截至 2026-05-19，项目已经完成基础 RAG MVP 和 Phase 2 检索增强。

已具备：
- 本地仓库和 GitHub URL 索引。
- 基于 `git ls-files --exclude-standard` 的仓库文件枚举，避免递归扫描依赖、构建产物和缓存目录。
- 文本、代码、Markdown、图片引用和 GitHub Issue 的基础入库。
- 大仓库流式处理：文件、chunk、embedding 和 Qdrant 写入按批推进。
- 自动生成 `repo_overview` 和 `repo_manifest`，帮助模型理解仓库整体范围。
- 混合检索：向量召回、关键词/路径召回、轻量重排、重要文件加权、同文件相邻 chunk 扩展。
- FastAPI 接口：`/health`、`/repos/index`、`/chat`。
- Vue 3 + Vite 前端：仓库索引和 SSE 流式问答。
- 离线开发兜底：未配置 embedding 或 LLM Key 时可使用 hash embedding 和离线预览。
- 基础单元测试覆盖仓库读取、chunk 元数据、manifest、检索隔离、混合检索和 API 路由。

仍待完善：
- AST / Tree-sitter 级符号索引、导入关系和调用链。
- 图片内容理解，目前只处理图片文件和 Markdown 图片引用，尚未做 OCR/VLM caption。
- RAG 质量评测、检索调试接口和前端证据可视化。
- 前端文案和部分源码中文注释存在编码乱码，需要单独修复。

## 技术栈

- Backend: FastAPI, LangChain, Qdrant, PyGithub
- Frontend: Vue 3, Vite
- Retrieval: Qdrant vector search + lexical/path recall + reranking
- Embedding: OpenAI embeddings 或本地 deterministic hash embedding
- LLM: OpenAI-compatible chat API，支持 `LLM_BASE_URL` 接入兼容服务
- Tests: pytest, Vite build

## 目录结构

```text
src/
  api/           FastAPI 路由和应用入口
  ingestion/     仓库解析、GitHub Issues 读取、索引入口
  processing/    文档切分、图片引用抽取、repo overview/manifest 生成
  retrieval/     Qdrant、embedding、混合检索和重排
  generation/    RAG 上下文拼接、prompt、LLM 流式调用
  prompts/       Jinja2 prompt 模板
ui/              Vue 3 + Vite 前端
tests/           单元测试
docs/            配置、RAG 设计、开发计划和进展文档
```

## 快速启动

1. 安装后端依赖：

```powershell
uv venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

2. 创建 `.env`：

```env
OPENAI_API_KEY=your_openai_key
LLM_API_KEY=your_llm_key
LLM_BASE_URL=
LLM_CHAT_MODEL=gpt-4o

QDRANT_MODE=local
QDRANT_PATH=data/qdrant
```

说明：`OPENAI_API_KEY` 主要用于 embedding；`LLM_API_KEY` 主要用于聊天模型。如果两者都不配置，系统会进入本地开发兜底模式。

3. 启动后端：

```powershell
uvicorn src.api.main:app --reload --port 8002
```

4. 启动前端：

```powershell
cd ui
npm install
npm run dev
```

Vite 默认监听 `http://localhost:3000`，并代理 `/api` 到 `http://127.0.0.1:8002`。

## 常用配置

```env
RAG_RETRIEVAL_K=16
RAG_REPO_CONTEXT_DOC_LIMIT=8
RAG_MAX_CONTEXT_CHARS=24000
RAG_HYBRID_VECTOR_CANDIDATES=48
RAG_HYBRID_KEYWORD_CANDIDATES=800
RAG_HYBRID_NEIGHBOR_WINDOW=1
RAG_INDEX_BATCH_SIZE=64
RAG_MAX_TEXT_FILE_BYTES=1048576
```

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest
cd ui
npm run build
```

## 进一步阅读

- [环境配置](docs/SETUP.md)
- [RAG 设计](docs/RAG.md)
- [项目进展](docs/PROGRESS.md)
- [开发计划](docs/PLAN.md)

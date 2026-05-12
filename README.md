# GitHub 多模态 RAG 智能问答系统

本项目面向 GitHub 仓库和本地代码仓库，提供索引、检索增强生成和流式问答能力。系统会读取代码、Markdown、文本文件和图片引用，将它们切分为带来源元数据的文档，写入 Qdrant，并在问答时结合项目概览、文件清单、混合检索结果和大模型生成回答。

## 当前能力

- 仓库摄取：支持 GitHub URL 和本地路径，优先使用 `git ls-files --exclude-standard` 避免扫描依赖目录。
- 大仓库处理：文件、chunk、embedding 分批流式处理，降低内存峰值。
- 项目级上下文：索引时生成 `repo_overview` 和 `repo_manifest`，让模型先了解目录、语言分布和文件清单。
- Phase 2 混合检索：向量召回 + 关键词/路径召回 + 轻量重排 + 同文件邻近 chunk 扩展。
- RAG 问答：FastAPI 提供 `/repos/index` 和 `/chat`，前端通过 SSE 展示流式回答。
- 本地开发兜底：未配置 embedding API 时使用 deterministic hash embedding，方便测试。

## 目录结构

```text
src/
  api/           FastAPI 路由
  ingestion/     仓库解析、GitHub Issues 摄取、索引入口
  processing/    文档切分、图片引用抽取、repo overview/manifest 生成
  retrieval/     Qdrant、embedding、混合检索和重排
  generation/    RAG 上下文拼接、Prompt、LLM 调用
  prompts/       Jinja2 Prompt 模板
ui/              Vue 3 + Vite 前端
tests/           单元测试
docs/            开发计划、配置说明、RAG 设计文档
```

## 快速启动

1. 安装后端依赖：

```powershell
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

2. 配置 `.env`：

```env
LLM_API_KEY=your_key
LLM_BASE_URL=
LLM_CHAT_MODEL=gpt-4o
QDRANT_MODE=local
QDRANT_PATH=data/qdrant
```

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

Vite 默认代理 `/api` 到 `http://127.0.0.1:8002`。

## Phase 2 检索配置

这些环境变量可以按仓库大小和模型上下文窗口调整：

```env
RAG_RETRIEVAL_K=16
RAG_MAX_CONTEXT_CHARS=24000
RAG_REPO_CONTEXT_DOC_LIMIT=8
RAG_HYBRID_VECTOR_CANDIDATES=48
RAG_HYBRID_KEYWORD_CANDIDATES=800
RAG_HYBRID_NEIGHBOR_WINDOW=1
```

说明：

- `RAG_RETRIEVAL_K`：最终主检索返回的核心证据数量。
- `RAG_HYBRID_VECTOR_CANDIDATES`：向量召回候选数量。
- `RAG_HYBRID_KEYWORD_CANDIDATES`：关键词/路径召回最多扫描的仓库文档数量。
- `RAG_HYBRID_NEIGHBOR_WINDOW`：命中代码 chunk 后，额外带上同文件前后几个 chunk。
- `RAG_MAX_CONTEXT_CHARS`：送入模型的上下文字符预算。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
cd ui
npm run build
```

## 进一步阅读

- [环境配置](docs/SETUP.md)
- [RAG 设计](docs/RAG.md)
- [开发计划](docs/PLAN.md)

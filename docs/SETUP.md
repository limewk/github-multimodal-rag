# 环境配置指南

本文档说明如何在本地运行 GitHub 多模态 RAG 智能问答系统。

## 1. 前置依赖

- Python 3.10+
- Node.js 18+
- Git
- `uv` 或 `pip`

推荐使用 `uv` 创建和管理 Python 虚拟环境。

## 2. 后端环境

在项目根目录执行：

```powershell
uv venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

如果已经存在 `.venv`，只需要激活环境并安装依赖：

```powershell
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

## 3. 环境变量

项目当前没有强依赖 `.env.example`，可以在根目录手动创建 `.env`。

最小本地开发配置：

```env
QDRANT_MODE=local
QDRANT_PATH=data/qdrant
RAG_EMBEDDING_PROVIDER=hash
```

使用 OpenAI-compatible LLM 和 embedding：

```env
OPENAI_API_KEY=your_openai_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

LLM_API_KEY=your_llm_key
LLM_BASE_URL=
LLM_CHAT_MODEL=gpt-4o
LLM_PROVIDER=
LLM_EXTRA_BODY=

QDRANT_MODE=local
QDRANT_PATH=data/qdrant
```

读取 GitHub open issues：

```env
GITHUB_TOKEN=your_github_personal_access_token
```

说明：
- `OPENAI_API_KEY` 主要用于 embedding。
- `LLM_API_KEY` 或 `OPENAI_API_KEY` 可用于聊天模型。
- 未配置 embedding key 时，系统会自动使用 deterministic hash embedding，方便本地测试。
- 未配置聊天模型 key 且未配置 `LLM_BASE_URL` 时，系统会返回 offline preview。

## 4. Qdrant 配置

本地文件模式：

```env
QDRANT_MODE=local
QDRANT_PATH=data/qdrant
QDRANT_COLLECTION=github_repo_multi_modal
```

远程服务模式：

```env
QDRANT_MODE=remote
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=
```

也可以直接使用：

```env
QDRANT_URL=https://your-qdrant-url
QDRANT_API_KEY=your_qdrant_key
```

## 5. RAG 参数

```env
RAG_RETRIEVAL_K=16
RAG_REPO_CONTEXT_DOC_LIMIT=8
RAG_MAX_CONTEXT_CHARS=24000
RAG_HYBRID_VECTOR_CANDIDATES=48
RAG_HYBRID_KEYWORD_CANDIDATES=800
RAG_HYBRID_NEIGHBOR_WINDOW=1
RAG_INDEX_BATCH_SIZE=64
RAG_MAX_TEXT_FILE_BYTES=1048576
RAG_GIT_LS_FILES_TIMEOUT_SECONDS=60
```

调优建议：
- 大仓库可适当提高 `RAG_HYBRID_VECTOR_CANDIDATES` 和 `RAG_HYBRID_KEYWORD_CANDIDATES`。
- 如果回答缺少函数上下文，提高 `RAG_HYBRID_NEIGHBOR_WINDOW`。
- 如果模型报上下文过长，降低 `RAG_MAX_CONTEXT_CHARS` 或 `RAG_RETRIEVAL_K`。
- 如果索引速度慢，可调整 `RAG_INDEX_BATCH_SIZE`。

## 6. 启动服务

后端：

```powershell
uvicorn src.api.main:app --reload --port 8002
```

前端：

```powershell
cd ui
npm install
npm run dev
```

前端 Vite 配置会把 `/api` 代理到 `http://127.0.0.1:8002`，默认访问地址是 `http://localhost:3000`。

## 7. 使用流程

1. 打开前端页面。
2. 输入 GitHub URL 或本地仓库路径。
3. 输入分支名，默认为 `main`。
4. 点击开始索引。
5. 索引完成后输入问题。
6. 回答末尾会附带 `Sources`，用于追踪证据文件和行号。

已有仓库在检索策略、manifest 逻辑或 chunk 元数据更新后，需要重新索引。

## 8. 验证命令

后端测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

前端构建：

```powershell
cd ui
npm run build
```

## 9. 常见问题

### 未配置 API Key 可以运行吗？

可以。未配置 embedding key 时使用 hash embedding；未配置聊天模型时返回 offline preview。这样可以先验证仓库读取、索引和检索链路。

### 为什么索引后回答没有更新？

同一个 `repo_id` 重新索引会删除旧文档并写入新文档。若代码更新后回答仍旧，通常需要确认前端返回的是新的 `repo_id`，或删除本地 `data/qdrant` 后重新索引。

### GitHub Issues 没有入库怎么办？

需要配置 `GITHUB_TOKEN`，并确保输入源是 GitHub 仓库 URL。本地路径不会触发 GitHub Issues 读取。

# 环境配置指南

本文档说明如何在本地运行 GitHub 多模态 RAG 智能问答系统。

## 1. 前置依赖

- Python 3.10+
- Node.js 18+
- Git
- `uv` 或 `pip`

## 2. 后端环境

在项目根目录执行：

```powershell
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

如果没有 `.venv`，可以先创建：

```powershell
uv venv
```

## 3. 环境变量

复制 `.env.example` 为 `.env`，至少配置大模型和 Qdrant：

```env
GITHUB_TOKEN=your_github_personal_access_token_here

LLM_API_KEY=your_llm_api_key_here
LLM_BASE_URL=
LLM_CHAT_MODEL=gpt-4o
LLM_PROVIDER=
LLM_EXTRA_BODY=

QDRANT_MODE=local
QDRANT_PATH=data/qdrant
```

开发阶段如果没有 OpenAI embedding key，系统会自动使用 hash embedding，便于本地测试。

## 4. Phase 2 检索参数

混合检索相关参数：

```env
RAG_RETRIEVAL_K=16
RAG_REPO_CONTEXT_DOC_LIMIT=8
RAG_MAX_CONTEXT_CHARS=24000
RAG_HYBRID_VECTOR_CANDIDATES=48
RAG_HYBRID_KEYWORD_CANDIDATES=800
RAG_HYBRID_NEIGHBOR_WINDOW=1
```

调优建议：

- 大仓库可适当提高 `RAG_HYBRID_VECTOR_CANDIDATES` 和 `RAG_HYBRID_KEYWORD_CANDIDATES`。
- 如果回答缺少函数上下文，提高 `RAG_HYBRID_NEIGHBOR_WINDOW`。
- 如果模型报上下文过长，降低 `RAG_MAX_CONTEXT_CHARS` 或 `RAG_RETRIEVAL_K`。

## 5. 启动服务

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

前端 Vite 配置会把 `/api` 代理到 `http://127.0.0.1:8002`。

## 6. 使用流程

1. 打开前端页面。
2. 输入 GitHub URL 或本地仓库路径。
3. 点击“开始分析仓库”。
4. 索引完成后输入问题。
5. 回答末尾会附带 Sources，便于追踪证据。

已有仓库在检索策略或 manifest 逻辑更新后，需要重新索引。

## 7. 验证命令

```powershell
.\.venv\Scripts\python.exe -m pytest
cd ui
npm run build
```

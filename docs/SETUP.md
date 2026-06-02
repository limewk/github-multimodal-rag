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

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Windows PowerShell：

```powershell
uv venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

如果已经存在 `.venv`，只需要激活环境并重新安装依赖即可。上传接口依赖 `python-multipart`，已写入 `requirements.txt`。

## 3. 前端环境

```bash
cd ui
npm install
```

前端开发服务器使用 Vite，默认端口为 `3000`。

## 4. 环境变量

项目会读取根目录 `.env`。可以复制 `.env.example` 后按需修改：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

### 最小本地开发配置

无需真实模型 Key，embedding 使用本地 hash，聊天模型无 Key 时会返回 offline preview。

```env
QDRANT_MODE=local
QDRANT_PATH=data/qdrant
QDRANT_COLLECTION=github_repo_multi_modal
RAG_EMBEDDING_PROVIDER=hash
```

### OpenAI-compatible LLM

适用于 ModelScope、DeepSeek、Qwen、通义千问、智谱、本地 Ollama、vLLM 等兼容 OpenAI Chat Completions 格式的服务。

```env
LLM_API_KEY=your_llm_key
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_CHAT_MODEL=your-model-id
LLM_PROVIDER=
LLM_EXTRA_BODY=

QDRANT_MODE=local
QDRANT_PATH=data/qdrant
QDRANT_COLLECTION=github_repo_multi_modal
RAG_EMBEDDING_PROVIDER=hash
```

ModelScope 示例：

```env
LLM_API_KEY=your_modelscope_key
LLM_BASE_URL=https://api-inference.modelscope.cn/v1
LLM_CHAT_MODEL=deepseek-ai/DeepSeek-V3.2
LLM_PROVIDER=
LLM_EXTRA_BODY=
```

### OpenAI embedding

如果希望使用真实 embedding 而不是本地 hash：

```env
OPENAI_API_KEY=your_openai_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
RAG_EMBEDDING_PROVIDER=openai
```

说明：

- `LLM_API_KEY` 或 `OPENAI_API_KEY` 可用于聊天模型。
- `OPENAI_API_KEY` 主要用于 OpenAI embedding。
- 未配置 embedding key 时，系统会自动使用 deterministic hash embedding，方便本地测试。
- 未配置聊天模型 key 且未配置 `LLM_BASE_URL` 时，系统会返回 offline preview。

### GitHub Issues

读取 GitHub open issues 时需要配置：

```env
GITHUB_TOKEN=your_github_personal_access_token
```

本地路径索引不会触发 GitHub Issues 读取。

## 5. Qdrant 配置

推荐本地文件模式，索引会持久化到项目目录：

```env
QDRANT_MODE=local
QDRANT_PATH=data/qdrant
QDRANT_COLLECTION=github_repo_multi_modal
```

如需避免本地文件锁，也可以用内存模式：

```env
QDRANT_LOCATION=:memory:
```

注意：内存模式在后端重启后会丢失索引，需要重新索引仓库。

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

## 6. RAG 参数

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

## 7. 启动服务

后端：

```bash
.venv/bin/python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```bash
cd ui
npm run dev
```

前端 Vite 配置会把 `/api` 代理到 `http://127.0.0.1:8000`，默认访问地址是 `http://127.0.0.1:3000/`。

## 8. 使用流程

1. 打开前端页面并登录或注册。
2. 输入 GitHub URL 或本地仓库路径。
3. 输入分支名，默认为 `main`。
4. 点击开始索引。
5. 在文件浏览、代码解析、图谱统计或可视化页面查看仓库结构。
6. 在智能问答页输入问题，也可以上传 PDF、Word、Markdown、TXT、CSV 或图片作为补充上下文。
7. 回答中的引用来源默认折叠，展开后可以点击跳转到代码片段。

已有仓库在检索策略、manifest 逻辑、chunk 元数据或源码内容更新后，需要重新索引。

## 9. 验证命令

后端测试：

```bash
.venv/bin/python -m pytest
```

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

前端构建：

```bash
cd ui
npm run build
```

## 10. 常见问题

### 未配置 API Key 可以运行吗？

可以。未配置 embedding key 时使用 hash embedding；未配置聊天模型时返回 offline preview。这样可以先验证仓库读取、索引和检索链路。

### 为什么索引后回答没有更新？

同一个 `repo_id` 重新索引会删除旧文档并写入新文档。若代码更新后回答仍旧，通常需要确认前端返回的是新的 `repo_id`，或删除本地 `data/qdrant` 后重新索引。

### 上传文件时报 JSON 解析错误怎么办？

当前版本后端同时支持 `/upload` 和 `/upload/`，前端使用 `/api/upload/`。如果仍出现空响应或非 JSON 响应，请先确认后端正在 `127.0.0.1:8000` 运行，并检查 Vite 代理配置。

### GitHub Issues 没有入库怎么办？

需要配置 `GITHUB_TOKEN`，并确保输入源是 GitHub 仓库 URL。本地路径不会触发 GitHub Issues 读取。

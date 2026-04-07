# 项目环境配置指南 (Environment Setup Guide)

本文档旨在帮助团队成员（及后续开发者）快速在本地搭建“面向 GitHub 仓库的多模态RAG智能问答系统”的开发环境。本系统采用前后端分离架构：后端基于 Python (FastAPI + LangChain)，前端基于 Node.js (Vue 3 + Vite)。

## 1. 前置开发依赖 (Prerequisites)
在开始配置之前，请确保您的计算机上已安装以下软件：
- **Python**: 3.10 或更高版本。
- **Node.js**: 18.0 或更高版本 (建议使用 LTS 版本)。
- **Git**: 用于版本控制和代码拉取。
- **包管理工具**: `pip` (Python) 和 `npm` (Node.js)。

---

## 2. 代码获取 (Clone Repository)
如果您尚未拉取代码，请使用以下命令将项目克隆到本地：
```bash
git clone https://github.com/您的用户名/您的仓库名.git
cd 您的仓库名
```
*(注：如果已经在本地工作区 `d:\Desktop\软件工程\github-multimodal-rag`，可跳过此步)*

---

## 3. 后端环境配置 (Backend Setup - Python)

后端核心负责数据的爬取、多模态处理（Tree-sitter、LangChain、Qdrant）以及暴漏 API 接口。

1. **进入项目根目录：**
   ```bash
   cd github-multimodal-rag
   ```

2. **创建 Python 虚拟环境 (Virtual Environment)：**
   使用虚拟环境可以隔离项目依赖，防止与全局 Python 环境冲突。
   - Windows: `python -m venv venv`
   - Mac/Linux: `python3 -m venv venv`

3. **激活虚拟环境：**
   - Windows (Command Prompt): `venv\Scripts\activate.bat`
   - Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
   - Mac/Linux: `source venv/bin/activate`

4. **安装后端依赖：**
   激活虚拟环境后，确保命令行前有 `(venv)` 标识，然后执行：
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 4. 环境变量配置 (Environment Variables)

系统需要调用 GitHub API 和大语言模型 API。我们需要在根目录下配置环境变量。

1. 在项目根目录 (`github-multimodal-rag/`) 找到 `.env.example` 文件。
2. 复制该文件并重命名为 `.env`。
3. 打开 `.env` 并填入您真实的 API 密钥等信息：
   ```env
   # Github Integration (获取代码和Issue需要的鉴权)
   GITHUB_TOKEN=your_github_personal_access_token_here

   # OpenAI / GPT-4V for Vision & Text (LLM & Embedding 模型密钥)
   OPENAI_API_KEY=your_openai_api_key_here

   # Vector DB configs (Qdrant 向量数据库配置)
   # 如果使用 Qdrant 本地内存模式或 Docker 模式，请按需修改
   QDRANT_HOST=localhost
   QDRANT_PORT=6333

   # 应用日志等级
   LOG_LEVEL=INFO
   ```

---

## 5. 前端环境配置 (Frontend Setup - Vue3)

前端页面使用 Vue 3 + Vite 构建，位于 `ui/` 目录下。

1. **进入前端目录：**
   ```bash
   cd ui
   ```

2. **安装 Node 依赖：**
   ```bash
   npm install
   ```

---

## 6. 启动开发服务器 (Run the Servers)

为了进行日常开发，您需要同时启动后端 API 服务和前端页面。建议在 VS Code 中**开启两个终端**分别运行。

### 终端 1：启动 FastAPI 后端服务
1. 确保在根目录 `github-multimodal-rag/` 且**虚拟环境已激活** `(venv)`。
2. 运行后端服务：
   ```bash
   uvicorn src.api.main:app --reload
   ```
3. 服务默认运行在 `http://127.0.0.1:8000`。
   - 您可以访问 `http://127.0.0.1:8000/docs` 查看由 Swagger 自动生成的 API 接口交互文档。

### 终端 2：启动 Vue 前端服务
1. 确保在前端目录 `github-multimodal-rag/ui/`。
2. 启动 Vite 开发服务器：
   ```bash
   npm run dev
   ```
3. 服务通常会运行在 `http://localhost:3000` (或 5173，视终端输出而定)。
4. Vite 配置中已经设定了 `/api` 相关的代理 (Proxy)，前端发送的 API 请求会自动转发到后端的 `8000` 端口，无需担心开发时的跨域 (CORS) 问题。

---

## 7. Qdrant 向量数据库准备 (可选/进阶)
在进行到向量检索开发 (Phase 3) 时，您需要一个 Qdrant 实例。
- **方案 A (推荐开发者使用本地 Docker):**
  ```bash
  docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage:z qdrant/qdrant
  ```
- **方案 B (Qdrant Cloud):**
  注册 Qdrant Cloud 获取集群 URL 和 API Key，然后将其更新至 `.env` 文件。
- **方案 C (本地内存 Memory 模式):**
  在 LangChain / Qdrant-Client 初始化时直接指明 `location=":memory:"` 进行快读测试。
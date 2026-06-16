# 从零安装与启动指南

本文档面向第一次部署或换一台新机器安装 GitHub 多模态 RAG 智能问答系统的场景。按顺序完成后，应能在本机启动：

- 后端 API：`http://127.0.0.1:8000`
- 前端页面：`http://127.0.0.1:3000`
- API 文档：`http://127.0.0.1:8000/docs`

项目支持本地仓库和 GitHub 仓库索引、代码结构展示、RAG 问答、文件上传、图片 OCR、历史对话和引用跳转。

## 1. 准备项目代码

如果还没有项目代码，先克隆仓库：

```bash
git clone https://github.com/limewk/github-multimodal-rag.git
cd github-multimodal-rag
```

如果需要指定分支，将 `main` 替换为实际要使用的分支，例如 `main`、`OCR` 或 `6.2-update`：

```bash
git fetch origin
git switch main
```

如果你已经在项目目录中，例如 `/Users/liuweikang/Documents/rag`，直接进入该目录即可：

```bash
cd /Users/liuweikang/Documents/rag
```

## 2. 安装系统依赖

必须安装：

- Git
- Python 3.10 或更高版本
- Node.js 18 或更高版本
- Tesseract OCR
- Tesseract 英文和中文简体语言包

推荐安装：

- `uv`：用于创建 Python 虚拟环境和安装后端依赖
- Homebrew、apt、nvm 等系统包管理工具

### macOS

安装 Homebrew 后执行：

```bash
brew install git python node uv tesseract tesseract-lang
```

说明：

- `tesseract` 提供 OCR 命令。
- `tesseract-lang` 提供 `chi_sim` 中文简体语言包。
- 如果已经安装过 `tesseract`，只缺中文语言包，也可以单独执行：

```bash
brew install tesseract-lang
```

### Ubuntu / Debian

安装 Node.js 20、Python、Git、OCR：

```bash
sudo apt update
sudo apt install -y git curl python3 python3-venv python3-pip
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo apt install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-chi-sim
python3 -m pip install --user uv
```

如果 `uv` 安装后命令不可用，确认 `~/.local/bin` 已加入 `PATH`：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Windows

建议使用 PowerShell。

1. 安装 Git for Windows：
   - 下载地址：https://git-scm.com/download/win

2. 安装 Python 3.10+：
   - 下载地址：https://www.python.org/downloads/windows/
   - 安装时勾选 `Add python.exe to PATH`。

3. 安装 Node.js 18+：
   - 下载地址：https://nodejs.org/
   - 推荐安装 LTS 版本。

4. 安装 Tesseract OCR：
   - 可使用 UB Mannheim Windows build：https://github.com/UB-Mannheim/tesseract/wiki
   - 安装时选择中文简体语言包，或手动把 `chi_sim.traineddata` 放入 Tesseract 的 `tessdata` 目录。

5. 安装 `uv`：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

如果 `uv` 不可用，也可以后面使用 `python -m venv` 和 `pip` 安装依赖。

## 3. 检查系统依赖是否安装成功

在项目目录执行：

```bash
git --version
python3 --version
node --version
npm --version
uv --version
tesseract --version
tesseract --list-langs
```

macOS / Linux 上，`tesseract --list-langs` 应至少包含：

```text
eng
chi_sim
```

Windows PowerShell 可执行：

```powershell
git --version
python --version
node --version
npm --version
uv --version
tesseract --version
tesseract --list-langs
```

如果 Windows 找不到 `tesseract` 命令，需要把 Tesseract 安装目录加入 `PATH`，或在 `.env` 中配置完整路径：

```env
OCR_TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## 4. 安装后端依赖

在项目根目录执行。

macOS / Linux：

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

如果没有 `uv`，使用 Python 自带虚拟环境：

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

安装完成后检查：

```bash
.venv/bin/python -c "import fastapi, qdrant_client, langchain; print('backend ok')"
```

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -c "import fastapi, qdrant_client, langchain; print('backend ok')"
```

## 5. 安装前端依赖

进入前端目录安装 Node 依赖：

```bash
cd ui
npm install
cd ..
```

如果 npm 下载很慢，可以临时使用国内镜像：

```bash
cd ui
npm install --registry=https://registry.npmmirror.com
cd ..
```

安装完成后可检查：

```bash
cd ui
npm run build
cd ..
```

## 6. 创建并配置 `.env`

项目从根目录 `.env` 读取配置。第一次安装时复制示例文件：

macOS / Linux：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

### 最小本地开发配置

不配置真实模型 Key 也能启动项目。此模式可以验证仓库读取、索引、上传、OCR 和前端页面；聊天会进入离线预览或有限能力模式。

```env
GITHUB_TOKEN=

LLM_API_KEY=
LLM_BASE_URL=
LLM_CHAT_MODEL=gpt-4o
LLM_PROVIDER=
LLM_EXTRA_BODY=

RAG_EMBEDDING_PROVIDER=hash
RAG_HASH_EMBEDDING_DIM=384

QDRANT_MODE=local
QDRANT_PATH=data/qdrant
QDRANT_COLLECTION=github_repo_multi_modal

OCR_ENABLED=true
OCR_LANGS=eng+chi_sim
OCR_TESSERACT_CMD=tesseract
OCR_TIMEOUT_SECONDS=20
OCR_MAX_TEXT_CHARS=8000

LOG_LEVEL=INFO
```

### 使用 ModelScope / DeepSeek / Qwen 等 OpenAI-compatible 模型

如果你有 OpenAI-compatible 网关或 ModelScope API Key，配置：

```env
LLM_API_KEY=your_model_api_key
LLM_BASE_URL=https://api-inference.modelscope.cn/v1
LLM_CHAT_MODEL=deepseek-ai/DeepSeek-V3.2
LLM_PROVIDER=
LLM_EXTRA_BODY=
```

注意：

- `LLM_BASE_URL` 必须以服务商文档为准。
- `LLM_CHAT_MODEL` 必须填写服务商实际支持的模型 ID。
- Key 不要提交到 Git 仓库。
- 如果模型服务要求额外 provider 参数，可通过 `LLM_PROVIDER` 或 `LLM_EXTRA_BODY` 配置。

### 使用 OpenAI embedding

默认推荐使用 `hash` embedding，安装简单、无费用。若要使用 OpenAI embedding：

```env
OPENAI_API_KEY=your_openai_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
RAG_EMBEDDING_PROVIDER=openai
```

### GitHub Issues 入库

普通仓库代码索引不需要 GitHub Token。只有要读取 GitHub open issues 时才需要：

```env
GITHUB_TOKEN=your_github_personal_access_token
```

本地路径索引不会读取 GitHub Issues。

## 7. Qdrant 向量库配置

默认推荐本地持久化模式：

```env
QDRANT_MODE=local
QDRANT_PATH=data/qdrant
QDRANT_COLLECTION=github_repo_multi_modal
```

特点：

- 索引数据保存在 `data/qdrant`。
- 后端重启后索引仍在。
- 同一时间不要启动多个后端实例共用同一个 `data/qdrant`，否则可能出现文件锁错误。

临时开发可用内存模式：

```env
QDRANT_LOCATION=:memory:
```

注意：内存模式在后端重启后会丢失索引，需要重新索引仓库。

如果要使用远程 Qdrant：

```env
QDRANT_MODE=remote
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=
```

也可以使用 URL：

```env
QDRANT_URL=https://your-qdrant-url
QDRANT_API_KEY=your_qdrant_key
```

## 8. OCR 配置与中文识别检查

项目默认对上传图片和仓库图片文件执行 OCR：

```env
OCR_ENABLED=true
OCR_LANGS=eng+chi_sim
OCR_TESSERACT_CMD=tesseract
OCR_TIMEOUT_SECONDS=20
OCR_MAX_TEXT_CHARS=8000
```

检查中文语言包：

```bash
tesseract --list-langs | grep chi_sim
```

Windows PowerShell：

```powershell
tesseract --list-langs | findstr chi_sim
```

如果没有 `chi_sim`：

- macOS：`brew install tesseract-lang`
- Ubuntu/Debian：`sudo apt install -y tesseract-ocr-chi-sim`
- Windows：安装中文简体语言包，或下载 `chi_sim.traineddata` 放入 Tesseract 的 `tessdata` 目录。

如果 OCR 不可用，系统不会中断上传、索引或问答，但图片文字无法进入上下文，回答质量会下降。

## 9. 启动后端

在项目根目录打开第一个终端：

macOS / Linux：

```bash
.venv/bin/python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

启动成功后会看到类似输出：

```text
Uvicorn running on http://127.0.0.1:8000
```

验证后端：

```bash
curl http://127.0.0.1:8000/health
```

预期返回：

```json
{"status":"ok"}
```

浏览器也可以打开：

```text
http://127.0.0.1:8000/docs
```

## 10. 启动前端

保留后端终端不要关闭。另开第二个终端：

```bash
cd ui
npm run dev -- --host 127.0.0.1
```

启动成功后会看到：

```text
Local: http://127.0.0.1:3000/
```

打开浏览器访问：

```text
http://127.0.0.1:3000/
```

前端会把 `/api/*` 请求代理到后端 `http://127.0.0.1:8000`。

验证代理：

```bash
curl http://127.0.0.1:3000/api/health
```

预期返回：

```json
{"status":"ok"}
```

## 11. 第一次使用流程

1. 打开 `http://127.0.0.1:3000/`。
2. 注册或登录本地账号。
3. 输入仓库来源：
   - GitHub URL，例如 `https://github.com/user/repo`
   - 本地绝对路径，例如 `/Users/you/projects/demo`
4. 输入分支名，默认 `main`。
5. 点击开始索引。
6. 索引完成后进入智能问答。
7. 可以上传 PDF、Word、Markdown、TXT、CSV 或图片作为补充上下文。
8. 图片上传后会自动 OCR，识别文本会进入问答上下文。
9. 回答里的引用来源默认折叠，展开后可以点击跳转到代码片段。

已有仓库在代码、检索参数、OCR 或 chunk 逻辑更新后，建议重新索引。

## 12. 测试与构建

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
cd ..
```

如果两项都通过，说明基础安装和主要代码链路正常。

## 13. 常见问题

### 端口 8000 或 3000 被占用

macOS / Linux：

```bash
lsof -iTCP:8000 -sTCP:LISTEN -n -P
lsof -iTCP:3000 -sTCP:LISTEN -n -P
```

如果确认是旧的后端或前端进程，可以停止旧进程后重启。

Windows PowerShell：

```powershell
netstat -ano | findstr :8000
netstat -ano | findstr :3000
```

### 上传文件时报 JSON 解析错误

通常是前端请求到了错误地址，或后端没有运行。按顺序检查：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:3000/api/health
```

两个都应返回 `{"status":"ok"}`。

### Qdrant 文件锁错误

如果看到类似：

```text
Storage folder data/qdrant is already accessed by another instance
```

说明有多个后端进程同时使用 `data/qdrant`。解决方式：

1. 停掉旧后端进程。
2. 只保留一个后端实例。
3. 或改用远程 Qdrant 服务。
4. 临时开发可以配置 `QDRANT_LOCATION=:memory:`，但重启后要重新索引。

### OCR 没有中文结果

检查语言包：

```bash
tesseract --list-langs | grep chi_sim
```

如果没有 `chi_sim`，按第 8 节安装中文语言包。安装后需要重启后端，让 OCR 语言缓存刷新。

### 模型接口调用失败

检查 `.env`：

- `LLM_API_KEY` 是否正确。
- `LLM_BASE_URL` 是否包含 `/v1`，以服务商要求为准。
- `LLM_CHAT_MODEL` 是否是服务商支持的真实模型 ID。
- 本地网络是否能访问模型服务。

未配置模型 Key 时，项目仍可启动和索引，但真实智能回答能力会受限。

### GitHub 仓库拉取失败

检查：

- GitHub URL 是否正确。
- 分支名是否存在。
- 当前网络是否能访问 GitHub。
- 私有仓库是否需要权限。

私有仓库建议先在本地 clone，然后用本地路径索引。

### 前端依赖安装失败

先确认 Node 版本：

```bash
node --version
```

必须是 Node.js 18 或更高。然后清理并重装：

```bash
cd ui
rm -rf node_modules
npm install
```

Windows PowerShell：

```powershell
cd ui
Remove-Item -Recurse -Force node_modules
npm install
```

## 14. 部署到其他系统的注意事项

迁移到另一台机器时，需要重新准备：

- Python 运行环境和后端依赖
- Node.js 和前端依赖
- Tesseract OCR 和 `chi_sim` 中文语言包
- `.env` 配置
- Qdrant 存储或远程 Qdrant 服务

如果复制项目代码但不复制 `data/qdrant`，需要重新索引仓库。

如果部署环境不能安装系统级 Tesseract，例如部分 serverless 平台，需要改用云 OCR 或视觉模型服务。

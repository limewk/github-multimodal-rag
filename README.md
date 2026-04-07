# 面向 GitHub 仓库的多模态RAG智能问答系统 (Multimodal RAG for GitHub Repositories)

## 项目简介 (Overview)
本项目是一个专为分析、理解并针对 GitHub 仓库进行问答的智能辅助系统。结合大语言模型 (LLM) 和视觉语言模型 (VLM)，运用检索增强生成 (RAG) 技术，系统能够无缝处理整个代码仓库中的**文本、代码、以及附带的图像内容**（比如 Issue 中的报错图片、架构图、README中的UI截图等），从而为开发者提供更加准确和深度的问答能力。

## 核心功能 (Key Features)
1. **GitHub 多模态数据摄取**：自动抓取指定仓库或本地仓库的代码(Code)、文档(Markdown/PDF/DOC)及图片(PNG/JPG/SVG/UML文本等)。
2. **多模态向量存储**：文本向量、代码结构化向量及图像 Embedding（如通过 CLIP 模型或统一多模态大模型方案）构建统一的/混合的向量检索库。
3. **混合检索策略**：针对代码语义、文档段落和图片描述的双路或多路召回，并进行重排 (Reranking)。
4. **多模态响应生成**：采用 VLM（如 GPT-4V, Claude 3 或 Qwen-VL 等）对检索到的代码段、图表一并进行理解，生成更贴近上下文的连贯回答。

## 目录结构 (Directory Structure)
```
/
├── config/              # 配置文件存放地 (YAML, JSON 等)
├── data/                # 爬取的或处理中的临时数据与向量库本地文件
├── docs/                # 项目文档（包括 API 文档、需求规格、设计文档）
│   ├── PLAN.md          # <- 项目实施与系统开发详细计划
│   └── SETUP.md         # 项目环境配置指南
├── src/                 # 核心后端与后端代码目录
│   ├── api/             # FastAPI/Flask 接口路由和控制器代码
│   ├── ingestion/       # GitHub 数据摄取模块 (克隆、拉取、爬取 Issue 和 PR)
│   ├── processing/      # 数据清洗与切分 (代码AST解析、Markdown解析、图片抽取)
│   ├── retrieval/       # Embedding 模型加载，向量数据库的连接、写入与混合检索
│   ├── generation/      # RAG 核心管道层与大模型(LLM/VLM)交互模块
│   ├── prompts/         # 集中式提示词存储库 (基于 ai-prompter 与 Jinja2 组装)
│   └── utils/           # 通用工具函数、日志配置、异常处理
├── ui/                  # 前端 Vue 3 单页面应用源码 (使用 Vite 打包)
├── tests/               # 单元测试与集成测试
├── .env.example         # 环境变量示例 (如 GITHUB_TOKEN, OPENAI_API_KEY)
├── .gitignore           # Git 的忽略配置
└── requirements.txt     # Python 依赖包清单
```

## 快速运行 (Quick Start)
请参考 [docs/SETUP.md](docs/SETUP.md) 获取详细的环境配置（包含前端 Vite 及后端 FastAPI 的集成运行步骤）。简要后端启动流程如下：

1. `python -m venv venv`
2. `.\venv\Scripts\Activate.ps1` (Windows) 或 `source venv/bin/activate` (Mac/Linux)
3. `pip install -r requirements.txt`
4. 复制 `.env.example` 到 `.env` 并配置对应秘钥与 Qdrant 数据库连接信息。
5. 运行 API服务: `uvicorn src.api.chat:router --reload` (或根据您的项目入口调整)
6. 启动前端: `cd ui && npm install && npm run dev`


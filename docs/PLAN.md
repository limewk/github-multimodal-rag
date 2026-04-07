# 面向 GitHub 仓库的多模态 RAG 智能问答系统 - 开发计划 (PLAN)

## 目标 (Objective)
通过大模型理解复杂的开源/闭源代码仓库中的**代码、文本以及图像**，打造一个高效协作的 AI 编程伴侣。它能在 GitHub Issues、PR、架构图或 README 截图的帮助下，为代码实现和故障排查提供专家级的多模态问答。

## 技术栈 (Technology Stack)
本项目预期采用的技术组成：
- **后端框架**: FastAPI 或 Flask (基于 Python)
- **大模型 (LLMs / VLMs):**
  - **文本/代码**: GPT-4 (或 Qwen 半开源模型、DeepSeek Coder、Gemini 等)
  - **视觉理解**: GPT-4V、Claude-3 或支持图片与文本对齐的开源模型（如 LLaVA，Qwen-VL）
- **Embedding/Vector DB (向量数据库):**
  - 使用针对代码的高级 Embedding，如 OpenAI `text-embedding-3`, Qwen-Embedding 或 VoyageAI Code。
  - 对于图像理解考虑 CLIP 的联合 Embedding 空间。
  - 库使用：Milvus, Qdrant, Chroma 其中之一。
- **RAG 编排/管道 (Orchestration):** LangChain (以及 LangChain 的各种生态和工具支持，如 langchain-core、langchain-community 等)。
- **代码结构分析:** Tree-Sitter 或是针对特定语言 AST (Abstract Syntax Tree) 的 Parser，辅助切割/打块 (Chunking)。
- **前端交互:** Vue 3 + Vite 作为独立前端应用层，用于提供高性能、模块化多模态展示和人机对话体验。

## 团队分工与人员职责 (Team Collaboration)
本项目共有 5 名开发成员，采用敏捷开发模式（Agile/Scrum）。为保证高效落地，任务角色分配如下：

- **成员 A (项目经理 & 核心算法 / Project Lead & RAG Env)**
  - 职责：整体项目架构把控、技术难点攻坚；负责核心 RAG 模型编排框架（LangChain 的引入）与多模态 Prompt Engineering 调优。
  - 主要模块：`src/generation` 模块的底层逻辑设计与联调。
- **成员 B (数据爬取工程师 / Data Ingestion)**
  - 职责：对接 GitHub API，抓取代码树、Issues、拉取图片；解决反爬和代理墙；验证多种代码语言（Python, Java 等）下的爬取稳定性。
  - 主要模块：`src/ingestion`。
- **成员 C (后端与大模型接入 / Backend & LLM API)**
  - 职责：开发 FastAPI 服务，管理各个应用路由；负责对接 GPT-4 / Qwen 等大模型 API 及异常重试处理；提供标准的 RESTful 接口供前端调用。
  - 主要模块：`src/api`, `src/utils`。
- **成员 D (数据解析与向量检索 / Processing & Retrieval)**
  - 职责：核心代码 Chunking 切块（Tree-sitter 的解析引入）、图文数据的映射；主导 Qdrant/Milvus 向量库的构建和混合搜索算法实现（Hybrid Search）。
  - 主要模块：`src/processing`, `src/retrieval`。
- **成员 E (前端开发与交互体验 / Frontend Dev)**
  - 职责：利用 Vue 3 + Vite 开发单页面 SPA 应用；完成流式响应 (Streaming 或是 Websocket) 接入；以及代码高亮、图片预览、多模态交互界面设计。
  - 主要模块：`ui/`。

## 详细开发阶段与时间表 (Development Phases)

### Phase 1: 需求解析与系统架构初始化 (Week 1)
- **成员 A & C**: 确定模型提供商、向量数据库选型，确立 RESTful API 契约协议风格。完成基础框架搭建 (已完成)。
- **成员 E**: 梳理产品的 UI 原型 (Figma/Axure) 和前台与后端的交互格式，配置 Vue 工程框架。
- **成员 B & D**: 分析 GitHub GraphQL API/REST API 的速率限制；确定图文数据表设计 (Metadata)。

### Phase 2: GitHub 数据的获取与多模态预处理 (Week 2-3)
- **任务 - B**: 编写通用 Crawler 脚本，按文件层级完整拉取并清洗 GitHub Markdown与代码。
- **任务 - D**: 利用 `tree-sitter` 实现对仓库各类代码 (Class / Function) 的自动化打片。抽取 Markdown 内的图片链接并结合上下文打标签。

### Phase 3: 多模态 Embedding 与向量索引构建 (Week 4-5)
- **任务 - D**: 对接 Text Embedding 和 Image-to-Text 模块。把所有 Chunk 存入目标向量库 (如 Qdrant)，实现持久化存储；构建支持带 Metadata 过滤的检索函数。
- **任务 - C**: 构建向量构建的触发点 API（让用户能够由前端点击按钮发起对某个新仓库的爬取与解析流程）。

### Phase 4: LangChain 管道与 VLM 组装 (Week 6-7)
- **任务 - A**: 搭建 LangChain 主检索链路。完成 "查询意图改写" -> "图文双路召回 (Top-K)" -> "重排 (Reranker)" -> "拼接 Prompt" 的核心逻辑。
- **任务 - C**: 将编好的 RAG Node 组入 FastAPI，并支持 SSE (Server-Sent Events) 的流式文本输出。

### Phase 5: 前后端全链路联调与端到端测试 (Week 8)
- **任务 - E**: 全面联调获取数据的接口；展示并美化大模型返回的代码段、文本与高亮图片分析结果。
- **全体成员**: 单元测试覆盖与性能压力测试。测试大型代码库产生的延迟。制定 README 和验收报告。

## 持续关注问题 (Considerations)
1. **GitHub 访问速率限制 (B)**：使用代理与 Personal Access Token 池，处理并发限制。
2. **Large Codebase 处理 (D)**：极大型仓库产生的 Chunk 可能极大造成 OOM；需优化分块逻辑，加入入口权重的判断。
3. **图图/图文对齐质量 (A, D)**：将大量代码实现与架构图映射对应，高度依赖向量 Embedding 质量及 VLM 强表征能力。

---
*注：本计划基于当前项目技术理解与 5 人小组研发能力撰写，将在后续敏捷开发进程中随着测试结果迭代调整。*
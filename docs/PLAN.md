# 开发计划

本文档记录当前 RAG 系统的阶段目标、完成情况和后续开发方向。

## 当前阶段概览

项目已经完成基础 RAG MVP、Phase 2 检索增强和一版前端交互增强。系统当前可以索引本地仓库或 GitHub 仓库，生成仓库概览和文件清单，使用混合检索找回证据，并通过 FastAPI + Vue 前端提供仓库预览、代码结构展示、可视化图谱和流式问答体验。

当前状态：
- Phase 1 稳定索引基础：已完成。
- Phase 2 检索质量增强：已完成。
- Phase 3 代码结构理解：已完成基础结构展示，真实依赖图和调用链仍在推进。
- Phase 4 多模态增强：已完成 OCR 基础版，VLM caption 待开发。
- Phase 5 评测和可观测性：待开发。

## 已完成能力

- GitHub URL / 本地仓库索引。
- 浅克隆 GitHub 仓库，并在 `main` 分支失败时回退到默认分支。
- 本地仓库优先使用 `git ls-files --exclude-standard` 枚举文件。
- 忽略 `.git`、`.venv`、`node_modules`、`dist`、`data` 等依赖、构建和缓存目录。
- 读取常见代码、配置、Markdown、文本文件和图片资源，并对图片执行可降级 OCR。
- 可选读取 GitHub open issues，并作为 `issue` 文档入库。
- 基于语言的代码切分和通用文本切分。
- 为每个 chunk 记录 `repo_id`、`path`、`source_type`、`language`、`chunk_id`、`start_line`、`end_line`。
- 自动生成 `repo_overview` 和分片 `repo_manifest`。
- Qdrant 本地或远程向量存储。
- OpenAI embedding 或 hash embedding 开发兜底。
- 批量 embedding 和 upsert，降低大仓库内存峰值。
- 重新索引时先删除同一 `repo_id` 的旧文档。
- 混合检索：
  - 向量召回。
  - 关键词召回。
  - 路径命中加权。
  - README、入口文件、配置文件、API/router/main 等重要文件加权。
  - 架构/结构/模块类问题提升 overview、manifest、Markdown。
  - 命中代码片段后扩展同文件相邻 chunk。
- RAG 上下文拼接和来源编号。
- SSE 流式问答。
- 未配置 LLM 时返回离线 RAG 预览，便于本地调试。
- 用户认证、仓库预览、代码解析、多级目录和代码片段预览。
- 知识图谱、代码统计、调用图和 Treemap 等可视化视图。
- 文件上传接口，支持 PDF、Word、Markdown、TXT、CSV 和图片作为问答补充上下文。
- 智能问答支持打字机式输出、LaTeX 渲染、引用来源折叠展示和点击引用跳转代码。
- 基础 pytest 测试和前端构建脚本。

## Phase 1：稳定索引基础

状态：已完成。

目标：
- 支持本地仓库和 GitHub 仓库。
- 避免大仓库递归扫描依赖目录。
- 支持常见代码、配置、Markdown、文本和图片引用。
- 索引链路不一次性加载全部文件和 chunk。

关键文件：
- `src/ingestion/repository_loader.py`
- `src/ingestion/indexing.py`
- `src/processing/chunking.py`
- `src/retrieval/vector_store.py`

验收情况：
- `tests/test_repository_loader.py`
- `tests/test_chunking.py`
- `tests/test_vector_store.py`

## Phase 2：检索质量增强

状态：已完成。

目标：改善“模型读不全项目”的问题，让问答不只依赖少量向量相似片段。

已实现：
- `hybrid_search_repo(repo_id, query, k=16)` 作为统一检索入口。
- 固定加载 `repo_overview` 和 `repo_manifest` 作为仓库级上下文。
- 结合向量候选和关键词候选。
- 结合路径、重要文件、source type 和问题意图做轻量重排。
- 对命中的同文件 chunk 做邻近扩展。
- Prompt 要求模型只基于检索上下文回答并引用来源。

关键文件：
- `src/retrieval/vector_store.py`
- `src/generation/rag_pipeline.py`
- `src/prompts/rag_prompt.jinja2`

## Phase 3：代码结构理解

状态：基础版已完成，增强版待开发。

目标：从文本 chunk RAG 升级到代码结构 RAG，更好回答入口流程、模块职责、调用链和跨文件依赖问题。

已实现：
- 基于 AST chunk 元数据记录函数、类、方法等代码片段信息。
- 提供 `/repos/{repo_id}/structure` 接口，返回文件、语言、chunk 类型、名称、行号和代码内容。
- 前端提供多级目录式代码结构树、代码预览、相关片段、解释片段入口。
- 前端提供知识图谱、代码统计、调用图和 Treemap 等可视化视图。

建议任务：
- 继续增强 AST / Tree-sitter 解析覆盖面。
- 抽取导入、导出、路由注册和更可靠的调用边。
- 生成结构化索引文档：
  - `__repo__/symbols.md`
  - `__repo__/imports.md`
  - `__repo__/entrypoints.md`
  - `__repo__/routes.md`
- 建立模块依赖关系，用于回答调用链、模块边界和入口流程。
- 让知识图谱和调用图使用结构化边，而不是只依赖 chunk 元数据和启发式匹配。
- 根据问题类型选择检索策略：
  - 架构类：overview + manifest + imports + entrypoints。
  - 实现类：symbols + 代码 chunk + 邻近 chunk。
  - Bug 类：错误关键词 + 调用链 + 相关测试。

## Phase 4：多模态增强

状态：OCR 基础版已完成，增强版待开发。

目标：从“图片引用”升级为可检索图片文字，并继续增强复杂图片理解。

已实现：
- 上传图片使用 Tesseract OCR 提取文字，并作为问答上下文。
- 仓库图片索引时执行 OCR，识别文本作为 `image_reference` 文档入库。
- OCR 不可用、缺语言包、超时或无文本时降级不中断。

建议任务：
- 下载或读取 Markdown 中引用的本地图片并关联 OCR/caption。
- 使用 VLM 生成图片 caption。
- 对架构图抽取组件、箭头、关系和关键文本。
- 将图片说明作为独立 document 入库，并关联原 Markdown 来源。
- 在回答中同时引用图片文档和原始图片路径。

## Phase 5：评测和可观测性

状态：待开发。

目标：让 RAG 质量可衡量、可调试、可回归。

建议任务：
- 增加 `/repos/{repo_id}/stats`。
- 增加 `/repos/{repo_id}/search-debug`。
- 前端展示检索证据、命中文件、chunk 行号和分数。
- 建立真实仓库评测集。
- 增加指标：
  - 命中文件准确率。
  - 答案引用准确率。
  - 无证据时拒答率。
  - 索引耗时。
  - 问答延迟。

## 当前优先级建议

1. 增加检索调试接口，让每次问答能看到命中文档、分数、来源类型和最终上下文。
2. 继续增强 Phase 3，优先做 Python / JavaScript / TypeScript 的导入、导出、入口文件和真实调用边索引。
3. 为一个真实中型仓库建立 10 到 20 条评测问题，用来验证结构化代码索引是否真正改善回答质量。
4. 增强图片理解能力，为仓库图片和上传图片接入 caption 或视觉模型。

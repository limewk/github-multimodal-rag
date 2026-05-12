# 开发计划

本文档记录当前 RAG 系统的阶段目标、完成情况和后续开发方向。

## 当前阶段概览

项目已经完成基础 RAG MVP，并完成 Phase 2 检索增强。

已完成：

- GitHub URL / 本地仓库索引。
- 大仓库流式解析、分批 embedding 和 Qdrant 写入。
- 代码、Markdown、文本、图片引用的基础切分。
- `repo_overview` 和 `repo_manifest` 项目级上下文。
- Phase 2 混合检索：
  - 向量召回。
  - 关键词和路径召回。
  - 轻量重排。
  - 重要文件加权。
  - 同文件邻近 chunk 扩展。
- FastAPI `/repos/index` 和 `/chat`。
- Vue 前端索引和流式问答。
- 基础单元测试。

## Phase 1：稳定索引基础

状态：已完成。

目标：

- 支持本地仓库和 GitHub 仓库。
- 避免大仓库递归扫描依赖目录。
- 支持常见代码和配置文件。
- 索引链路不一次性加载全部文件和 chunk。

关键文件：

- `src/ingestion/repository_loader.py`
- `src/ingestion/indexing.py`
- `src/processing/chunking.py`
- `src/retrieval/vector_store.py`

## Phase 2：检索质量增强

状态：已完成。

目标：改善“模型读不全项目”的问题，让问答不只依赖少量向量相似片段。

已实现能力：

- `hybrid_search_repo`：统一执行混合检索。
- 向量候选：使用 embedding 从 Qdrant 召回语义相关 chunk。
- 关键词候选：扫描 repo 内文档，按 query token、正文和路径命中计分。
- 路径优先：当问题提到文件名、目录名、函数名时提高相关路径权重。
- 重要文件优先：README、入口文件、配置文件、API/router/main 等路径有轻量加权。
- 概览问题识别：当问题询问架构、结构、模块、技术栈时，提升 `repo_overview`、`repo_manifest`、Markdown 的排序。
- 邻近 chunk 扩展：命中代码片段后自动带上同文件前后 chunk，保留局部上下文。

关键文件：

- `src/retrieval/vector_store.py`
- `src/generation/rag_pipeline.py`
- `src/prompts/rag_prompt.jinja2`

可调参数：

```env
RAG_RETRIEVAL_K=16
RAG_REPO_CONTEXT_DOC_LIMIT=8
RAG_MAX_CONTEXT_CHARS=24000
RAG_HYBRID_VECTOR_CANDIDATES=48
RAG_HYBRID_KEYWORD_CANDIDATES=800
RAG_HYBRID_NEIGHBOR_WINDOW=1
```

## Phase 3：代码结构理解

状态：待开发。

目标：从文本 chunk RAG 进一步升级到代码结构 RAG。

计划：

- 引入 AST / Tree-sitter 解析。
- 抽取类、函数、方法、导入、导出。
- 生成符号索引：
  - `__repo__/symbols.md`
  - `__repo__/imports.md`
  - `__repo__/entrypoints.md`
- 建立模块依赖关系，用于回答调用链、模块边界、入口流程。
- 根据问题类型选择检索策略：
  - 架构类问题：overview + manifest + imports。
  - 实现类问题：symbols + 代码 chunk + 邻近 chunk。
  - Bug 类问题：错误关键词 + 调用链 + 相关测试。

## Phase 4：多模态增强

状态：待开发。

目标：从图片引用升级到真正的图片内容理解。

计划：

- 下载 Markdown 中的图片。
- OCR 提取图片文字。
- 使用 VLM 生成图片 caption。
- 对架构图抽取组件、箭头、关系。
- 将图片说明作为独立 document 入库，并关联原 Markdown 来源。

## Phase 5：评测和可观测性

状态：待开发。

目标：让 RAG 质量可衡量、可调试。

计划：

- 增加 `/repos/{repo_id}/stats`。
- 增加 `/repos/{repo_id}/search-debug`。
- 前端展示检索证据、命中文件、chunk 行号和来源。
- 建立真实仓库评测集。
- 指标：
  - 命中文件准确率。
  - 答案引用准确率。
  - 无证据时拒答率。
  - 索引耗时。
  - 问答延迟。

## 当前优先级

下一阶段建议优先开发 Phase 3。Phase 2 已经解决“检索面太窄”的主要问题，但大型仓库中真正困难的是跨文件结构关系，尤其是调用链、入口流程和模块依赖。

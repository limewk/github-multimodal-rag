# RAG 设计说明

本文档说明当前 RAG 链路、Phase 2 混合检索策略和调优方式。

## 1. 数据流

```text
GitHub URL / Local Path
  -> resolve_repository_source
  -> iter_repository_files / iter_github_issues
  -> iter_repository_documents
  -> index_documents
  -> Qdrant
  -> hybrid_search_repo + repo_overview/repo_manifest
  -> Prompt
  -> LLM streaming answer
```

## 2. 索引内容

每个仓库索引时会产生以下 document：

- `code`：代码文件 chunk。
- `markdown`：Markdown 文件 chunk。
- `text`：普通文本 chunk。
- `issue`：GitHub Issue 内容。
- `image_reference`：图片文件或 Markdown 图片引用。
- `repo_overview`：仓库级摘要，包括文件数、语言分布、顶层目录。
- `repo_manifest`：仓库文件清单，按固定大小分片。

`repo_overview` 和 `repo_manifest` 是让模型理解项目全局范围的关键。已有仓库在此逻辑更新后需要重新索引。

## 3. Phase 2 混合检索

Phase 2 的主入口是：

```python
hybrid_search_repo(repo_id, query, k=16)
```

检索步骤：

1. 向量召回：使用 embedding 在 Qdrant 内按 `repo_id` 过滤召回候选。
2. 关键词召回：扫描仓库文档，按 query token、正文命中、路径命中计分。
3. 轻量重排：综合向量分、关键词分、路径分、重要文件分。
4. 问题意图加权：架构/结构/模块/技术栈类问题会提升 overview、manifest、Markdown。
5. 邻近 chunk 扩展：命中代码片段后带上同文件前后 chunk，保留局部上下文。
6. 去重并按上下文顺序返回。

## 4. 问答上下文组织

`stream_rag_answer` 会先加载：

- `repo_overview`
- `repo_manifest`

然后再加载 `hybrid_search_repo` 返回的具体证据。最终由 `format_docs` 拼接成带来源编号的上下文，并受 `RAG_MAX_CONTEXT_CHARS` 限制。

## 5. 参数说明

```env
RAG_RETRIEVAL_K=16
RAG_REPO_CONTEXT_DOC_LIMIT=8
RAG_MAX_CONTEXT_CHARS=24000
RAG_HYBRID_VECTOR_CANDIDATES=48
RAG_HYBRID_KEYWORD_CANDIDATES=800
RAG_HYBRID_NEIGHBOR_WINDOW=1
```

- `RAG_RETRIEVAL_K`：最终主证据数量。更高会提高覆盖率，但增加上下文消耗。
- `RAG_REPO_CONTEXT_DOC_LIMIT`：固定加载的 overview/manifest 数量。
- `RAG_MAX_CONTEXT_CHARS`：Prompt 上下文最大字符数。
- `RAG_HYBRID_VECTOR_CANDIDATES`：向量召回候选池大小。
- `RAG_HYBRID_KEYWORD_CANDIDATES`：关键词召回最多扫描的文档数。
- `RAG_HYBRID_NEIGHBOR_WINDOW`：同文件邻近 chunk 数量。

## 6. 调优建议

- 回答缺少整体项目结构：提高 `RAG_REPO_CONTEXT_DOC_LIMIT`。
- 回答漏掉具体函数：提高 `RAG_HYBRID_KEYWORD_CANDIDATES` 或 `RAG_HYBRID_NEIGHBOR_WINDOW`。
- 回答引用太少：提高 `RAG_RETRIEVAL_K`。
- 模型上下文过长：降低 `RAG_MAX_CONTEXT_CHARS` 或 `RAG_RETRIEVAL_K`。
- 大仓库检索变慢：降低 `RAG_HYBRID_KEYWORD_CANDIDATES`。

## 7. 已知限制

- 关键词召回目前是轻量实现，不是完整 BM25。
- 尚未使用 cross-encoder 或 LLM reranker。
- 尚未建立 AST 级符号索引和调用关系。
- 图片仍以引用和上下文为主，尚未做 OCR/VLM caption。

这些限制会在 Phase 3 和 Phase 4 中继续补齐。

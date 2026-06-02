# RAG 设计说明

本文档说明当前 RAG 链路、Phase 2 混合检索策略、关键配置和已知限制。

## 1. 数据流

```text
GitHub URL / Local Path
  -> resolve_repository_source
  -> iter_repository_files / iter_github_issues
  -> iter_repository_documents
  -> index_documents
  -> Qdrant
  -> load_repo_context_documents + hybrid_search_repo
  -> format_docs
  -> Prompt
  -> LLM streaming answer / offline preview
```

## 2. 索引内容

每个仓库索引时会产生以下 document：

- `code`：代码文件 chunk。
- `markdown`：Markdown 文件 chunk。
- `text`：普通文本文件 chunk。
- `issue`：GitHub open issue 内容，需要配置 `GITHUB_TOKEN`。
- `image_reference`：图片文件或 Markdown 图片引用。
- `repo_overview`：仓库级摘要，包含文件数、source type、语言分布、顶层目录。
- `repo_manifest`：仓库文件清单，按固定大小分片。

`repo_overview` 和 `repo_manifest` 是模型理解项目全局范围的关键上下文。已有仓库在 manifest 或检索逻辑更新后需要重新索引。

## 3. 元数据约定

每个 chunk 会带上统一元数据：

```json
{
  "repo_id": "repo-name-hash",
  "source_type": "code",
  "path": "src/app.py",
  "language": "python",
  "chunk_id": 0,
  "start_line": 1,
  "end_line": 20
}
```

这些字段用于：
- 在 Qdrant 中隔离不同仓库。
- 格式化回答来源。
- 做路径关键词匹配。
- 扩展同文件相邻 chunk。
- 支撑 `/repos/{repo_id}/structure` 的代码结构展示。
- 后续支持检索调试和更可靠的前端证据展示。

## 4. Phase 2 混合检索

主入口：

```python
hybrid_search_repo(repo_id, query, k=16)
```

检索步骤：

1. 向量召回：使用 embedding 在 Qdrant 内按 `repo_id` 过滤召回语义相关 chunk。
2. 关键词召回：滚动扫描仓库文档，按 query token、正文命中和路径命中计分。
3. 轻量重排：综合向量分、关键词分、路径分、重要文件分和 source type 分。
4. 问题意图加权：架构、结构、模块、技术栈类问题会提升 `repo_overview`、`repo_manifest` 和 Markdown。
5. 邻近 chunk 扩展：命中代码片段后带上同文件前后 chunk，保留局部上下文。
6. 去重并返回最终证据。

默认权重位于 `src/retrieval/vector_store.py`，当前定位是轻量、可解释、无需额外模型的 reranker。

## 5. 问答上下文组织

`stream_rag_answer` 会先加载：
- `repo_overview`
- `repo_manifest`

然后再加载 `hybrid_search_repo` 返回的具体证据。最终由 `format_docs` 拼接成带来源编号的上下文，并受 `RAG_MAX_CONTEXT_CHARS` 限制。

回答结束后会追加：

```text
Sources:
[1] src/app.py:1-20
[2] README.md:4-18
```

这样用户可以回溯证据来源。

前端会提取这段来源清单，将其折叠为“引用来源”下拉区域。默认只展示回答正文，展开后可以查看来源文件、行号，并点击跳转到对应代码片段。

## 6. LLM 与离线模式

聊天模型通过 `ChatOpenAI` 接入 OpenAI-compatible API：

- `LLM_CHAT_MODEL`：聊天模型名。
- `LLM_API_KEY` 或 `OPENAI_API_KEY`：聊天模型 Key。
- `LLM_BASE_URL`：兼容服务地址，可为空。
- `LLM_PROVIDER` / `LLM_EXTRA_BODY`：额外 provider 参数。

如果没有配置聊天模型 Key 且没有配置 `LLM_BASE_URL`，系统会返回 offline preview，展示问题和检索上下文前缀，便于本地调试索引和检索。

## 7. 参数说明

```env
RAG_RETRIEVAL_K=16
RAG_REPO_CONTEXT_DOC_LIMIT=8
RAG_MAX_CONTEXT_CHARS=24000
RAG_HYBRID_VECTOR_CANDIDATES=48
RAG_HYBRID_KEYWORD_CANDIDATES=800
RAG_HYBRID_NEIGHBOR_WINDOW=1
RAG_INDEX_BATCH_SIZE=64
RAG_MAX_TEXT_FILE_BYTES=1048576
```

- `RAG_RETRIEVAL_K`：最终主证据数量。更高会提高覆盖率，但增加上下文消耗。
- `RAG_REPO_CONTEXT_DOC_LIMIT`：固定加载的 overview/manifest 数量。
- `RAG_MAX_CONTEXT_CHARS`：Prompt 上下文最大字符数。
- `RAG_HYBRID_VECTOR_CANDIDATES`：向量候选池大小。
- `RAG_HYBRID_KEYWORD_CANDIDATES`：关键词召回最多扫描的文档数量。
- `RAG_HYBRID_NEIGHBOR_WINDOW`：同文件邻近 chunk 数量。
- `RAG_INDEX_BATCH_SIZE`：索引入库批大小。
- `RAG_MAX_TEXT_FILE_BYTES`：单个文本文件最大读取字节数。

## 8. 调优建议

- 回答缺少整体项目结构：提高 `RAG_REPO_CONTEXT_DOC_LIMIT`。
- 回答漏掉具体函数或路径：提高 `RAG_HYBRID_KEYWORD_CANDIDATES` 或 `RAG_HYBRID_NEIGHBOR_WINDOW`。
- 回答引用太少：提高 `RAG_RETRIEVAL_K`。
- 模型上下文过长：降低 `RAG_MAX_CONTEXT_CHARS` 或 `RAG_RETRIEVAL_K`。
- 大仓库检索变慢：降低 `RAG_HYBRID_KEYWORD_CANDIDATES`，或后续引入倒排索引/BM25。

## 9. 已知限制

- 关键词召回目前是轻量实现，不是完整 BM25。
- 尚未使用 cross-encoder 或 LLM reranker。
- 已有基础 AST chunk 元数据和代码结构接口，但导入关系、导出符号和真实调用链仍需增强。
- 图片仍以引用和上下文为主，尚未做 OCR/VLM caption。
- 尚未提供检索调试接口，无法直接查看候选分数和重排过程。
- 目前没有系统化评测集，难以量化每次检索策略调整的收益。

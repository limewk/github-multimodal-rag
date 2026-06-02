# GitHub 多模态 RAG 系统 - 黑盒白盒测试计划

## 一、项目概述

### 核心功能
1. **仓库索引模块** (`handleIndexRepo` / `index_repository_endpoint`)
2. **问答模块** (`sendMessage` / `chat_endpoint`)
3. **数据解析模块** (`readApiResponse`)
4. **图片 OCR 模块** (`extract_image_text_from_bytes` / `upload_file`)

---

## 二、黑盒测试设计（基于功能需求）

### 2.1 等价类划分与边界值分析

#### 【功能1】仓库索引功能

**输入参数：** `repositorySource`（仓库地址）、`branch`（分支）

##### 等价类划分：

| 等价类编号 | 类别 | 有效/无效 | 描述 | 测试用例 |
|--------|------|---------|------|---------|
| EC1 | GitHub URL | 有效 | 有效的GitHub仓库URL | `https://github.com/user/repo` |
| EC2 | 本地路径 | 有效 | 有效的本地仓库路径 | `/path/to/repo` 或 `C:\path\repo` |
| EC3 | 空值 | 无效 | 空字符串或仅空格 | `""` 或 `"   "` |
| EC4 | 无效GitHub格式 | 无效 | 格式不符的GitHub链接 | `https://github.com/invalid` |
| EC5 | 不存在的本地路径 | 无效 | 本地路径不存在 | `/nonexistent/path` |
| EC6 | 特殊字符 | 无效 | 包含特殊字符的输入 | `<script>alert()</script>` |

##### 分支参数等价类：

| 等价类编号 | 有效/无效 | 描述 | 测试用例 |
|--------|---------|------|---------|
| EC7 | 有效 | 合法分支名 | `main`, `dev`, `feature/new` |
| EC8 | 有效 | 空值（使用默认） | `""` → `main` |
| EC9 | 无效 | 不存在分支 | `nonexistent-branch` |

##### 边界值测试：

| 边界值 | 测试点 | 期望结果 |
|-------|-------|--------|
| 最小长度 | 单字符 | 应拒绝或处理 |
| 最大长度 | 超长URL(>2048) | 应拒绝或处理 |
| 空格边界 | 前后仅空格 | 应识别为空 |
| 特殊字符边界 | `/./` 或 `/../` | 路径遍历风险 |

---

#### 【功能2】问答功能

**输入参数：** `question`（问题）、`repoId`（仓库ID）

##### 等价类划分：

| 等价类编号 | 有效/无效 | 描述 | 测试用例 |
|--------|---------|------|---------|
| EC10 | 有效 | 正常问题 | `"这个项目是做什么的？"` |
| EC11 | 有效 | 短问题 | `"什么？"` |
| EC12 | 有效 | 长问题 | `"请详细解释..."(>1000字)` |
| EC13 | 无效 | 空问题 | `""` 或 `"   "` |
| EC14 | 无效 | 缺少repoId | repoId为空或undefined |
| EC15 | 无效 | 无效repoId | `"invalid-repo-id-format"` |
| EC16 | 有效 | 特殊字符问题 | `"@#$%^&*()"` |
| EC17 | 有效 | 代码片段问题 | `"def foo(): pass"` |

##### 流式响应处理等价类：

| 等价类编号 | 有效/无效 | 描述 | 测试用例 |
|--------|---------|------|---------|
| EC18 | 有效 | 正常SSE流 | `data: chunk1\n\ndata: chunk2\n\ndata: [DONE]` |
| EC19 | 有效 | 空响应体 | `data: \n\n` |
| EC20 | 无效 | 格式错误 | `invalid-sse-format` |
| EC21 | 无效 | 网络错误 | 连接超时/断开 |
| EC22 | 有效 | 多行内容 | SSE中包含\n的数据 |

#### 【功能3】图片 OCR 功能

**输入参数：** 图片文件、`OCR_LANGS`、Tesseract 可用状态

##### 等价类划分：

| 等价类编号 | 有效/无效 | 描述 | 测试用例 |
|--------|---------|------|---------|
| EC23 | 有效 | Tesseract 和语言包可用 | 英文截图 |
| EC24 | 有效 | 部分语言包缺失 | `OCR_LANGS=eng+chi_sim` 但仅安装 `eng` |
| EC25 | 有效 | OCR 无识别文本 | 纯色图片 |
| EC26 | 有效 | Tesseract 不存在 | 未安装系统 OCR |
| EC27 | 有效 | OCR 超时 | 大图或命令卡住 |

预期：所有 OCR 降级场景都不应阻断上传、仓库索引或问答，只返回明确 `ocr_status`。

---

### 2.2 黑盒测试用例设计

#### 测试场景1：正常流程
```
【TC-BLK-001】正常索引GitHub仓库
前置条件：网络连接正常，目标仓库存在
输入：repositorySource="https://github.com/pytorch/pytorch", branch="main"
步骤：
  1. 填入仓库地址
  2. 点击"开始索引仓库"
  3. 等待索引完成
期望结果：
  - repoStatus显示 "索引完成：xxx chunks"
  - repoId被正确赋值
  - 按钮恢复可用状态
测试类型：功能测试

【TC-BLK-002】正常提出问题
前置条件：仓库已索引成功（参考TC-BLK-001）
输入：question="这个项目的主要功能是什么？"
步骤：
  1. 在问答框输入问题
  2. 点击发送或按Enter
  3. 等待响应
期望结果：
  - AI 消息内容逐步显示模型回答
  - 消息气泡显示用户问题和助手回答
  - 最后显示 [DONE] 标记
测试类型：功能测试、流式测试
```

#### 测试场景2：边界值测试
```
【TC-BLK-003】空仓库地址
输入：repositorySource="", branch="main"
步骤：
  1. 不输入仓库地址
  2. 点击"开始索引"
期望结果：
  - 不发送请求（前端验证）
  - 无错误消息显示（可选择添加提示）

【TC-BLK-004】超长仓库地址
输入：repositorySource=超过2048字符的URL, branch="main"
步骤：
  1. 输入过长的URL
  2. 点击"开始索引"
期望结果：
  - 要么截断，要么显示错误提示
  - 不导致前端崩溃

【TC-BLK-005】不存在的本地仓库
输入：repositorySource="/nonexistent/repo/path", branch="main"
步骤：
  1. 输入不存在的本地路径
  2. 点击"开始索引"
期望结果：
  - 后端返回404或400错误
  - repoStatus显示 "❌ 找不到仓库" 或类似
  - repoId不被赋值
```

#### 测试场景3：无效输入测试
```
【TC-BLK-006】空问题输入
输入：question="", repoId已设置
步骤：
  1. 点击发送而未输入问题
期望结果：
  - 不发送请求（前端验证）
  - "发送"按钮不启用

【TC-BLK-007】缺少repoId的问答
输入：question="有效问题", repoId=""
步骤：
  1. 在repoId为空时尝试提问
期望结果：
  - 不发送请求
  - 输入框被禁用

【TC-BLK-008】特殊字符XSS攻击
输入：repositorySource="<script>alert('xss')</script>"
步骤：
  1. 输入包含脚本的特殊字符
  2. 提交表单
期望结果：
  - 被正确编码或过滤
  - 不执行脚本代码
  - 显示错误提示
测试类型：安全测试
```

#### 测试场景4：异常处理测试
```
【TC-BLK-009】网络错误处理
条件：模拟网络断开/请求超时
步骤：
  1. 索引或问答时网络中断
期望结果：
  - 显示错误信息
  - repoStatus/AI 消息内容显示 "❌ ..."
  - isIndexing/isAnswering恢复为false
  - UI可继续交互

【TC-BLK-010】服务器错误（HTTP 500）
条件：后端返回500错误
步骤：
  1. 触发索引或问答
  2. 后端返回500错误
期望结果：
  - 显示 "服务器内部错误"
  - 不导致前端崩溃

【TC-BLK-011】空响应处理
条件：后端返回空响应体
步骤：
  1. 调用API
  2. 后端返回空body
期望结果：
  - readApiResponse返回 `{detail: "服务返回了空响应（HTTP xxx）"}`
  - 显示用户友好的错误信息

【TC-BLK-012】非JSON响应
条件：后端返回非JSON文本
步骤：
  1. 调用API
  2. 返回HTML或纯文本
期望结果：
  - JSON.parse失败
  - 返回 `{detail: 原始文本}`
  - 显示原始文本给用户
```

#### 测试场景5：状态管理测试
```
【TC-BLK-013】重复索引同一仓库
步骤：
  1. 索引仓库A
  2. 不清除历史直接索引仓库B
期望结果：
  - repoId被更新为新的仓库
  - 对话历史可选清空或保留
  - 能正常切换仓库

【TC-BLK-014】快速连续请求
步骤：
  1. 快速点击多次"开始索引"
  2. 快速连续发送多个问题
期望结果：
  - 请求被防抖或节流
  - isIndexing/isAnswering阻止并发
  - 只处理最后一次请求或都处理

【TC-BLK-015】回复后清空历史
步骤：
  1. 完成一次问答
  2. 点击"清空历史"按钮
期望结果：
  - chatMessages清空
  - AI 消息内容清空
  - msgSources清空
  - 可继续新提问
```

#### 测试场景6：流式响应处理
```
【TC-BLK-016】SSE流式接收
条件：后端流式返回多个chunk
步骤：
  1. 提问后等待SSE响应
期望结果：
  - AI 消息内容逐步追加
  - 用户可看到逐字显示效果
  - 最终显示完整回答

【TC-BLK-017】SSE含有换行符
条件：后端返回包含\n的SSE数据
步骤：
  1. 提问
  2. 后端返回多行数据
期望结果：
  - 正确解析多行内容
  - AI 消息内容保留原始换行

【TC-BLK-018】SSE[DONE]标记处理
条件：后端流式完成
步骤：
  1. 等待完整流式响应
期望结果：
  - 接收到 [DONE] 时停止读取
  - isAnswering设为false
  - 输入框恢复可用
```

---

## 三、白盒测试设计（基于代码逻辑）

### 3.1 代码流程分析与路径覆盖

#### 【模块1】handleIndexRepo 函数控制流

```
START
  │
  ├─ 条件1: repositorySource.value.trim() 为空?
  │  ├─ YES → RETURN (无操作)
  │  └─ NO → 继续
  │
  ├─ isIndexing = true
  ├─ repoStatus = '正在构建索引...'
  │
  ├─ 条件2: repositorySource.startsWith('http')?
  │  ├─ YES → payload = { github_url, branch }
  │  └─ NO → payload = { local_path, branch }
  │
  ├─ FETCH /api/repos/index
  │
  ├─ 条件3: response.ok?
  │  ├─ NO → throw Error
  │  └─ YES → 继续
  │
  ├─ repoId = data.repo_id
  ├─ repoStatus = '索引完成：...'
  │
  ├─ CATCH异常:
  │  └─ repoStatus = error.message || '索引构建失败'
  │
  ├─ FINALLY:
  │  └─ isIndexing = false
  │
END
```

**圈复杂度计算：**
- 决策点：3个 (条件1、条件2、条件3) + catch块 + finally块
- 圈复杂度 M = 3 + 1 = **4**

##### 基本路径设计（线性独立路径）：

| 路径编号 | 路径描述 | 触发条件 |
|--------|--------|--------|
| 路径1 | 仓库源为空 → 直接返回 | `repositorySource = ""` |
| 路径2 | GitHub URL + 成功索引 | `repositorySource = "https://github.com/..."` + 响应成功 |
| 路径3 | 本地路径 + 成功索引 | `repositorySource = "/path/..."` + 响应成功 |
| 路径4 | 索引过程中异常 | 任何输入 + response.ok = false |

##### 白盒测试用例：

```
【TC-WB-001】路径1：空仓库源检测
输入：repositorySource = "", branch = "main"
预期执行：直接return，不进行后续操作
验证：
  - fetch 未被调用
  - isIndexing 保持false
  - repoStatus 保持空
方法：Mock fetch，断言其未被调用

【TC-WB-002】路径2：GitHub URL分支
输入：repositorySource = "https://github.com/pytorch/pytorch", branch = "main"
预期执行：
  1. 条件1 通过（非空）
  2. isIndexing = true
  3. 条件2 通过（startsWith('http'))
  4. payload.github_url 被设置
  5. fetch 被调用，响应成功
期望结果：
  - repoId 被正确赋值
  - repoStatus 包含 "索引完成"
  - isIndexing 恢复为false
验证：Mock fetch返回成功响应

【TC-WB-003】路径3：本地路径分支
输入：repositorySource = "/home/user/repo", branch = "dev"
预期执行：
  1. 条件1 通过
  2. 条件2 不通过（不startsWith('http'))
  3. payload.local_path 被设置
  4. branch = "dev" 被传递
期望结果：
  - fetch 请求体包含 {local_path: "...", branch: "dev"}
验证：检查fetch调用的参数

【TC-WB-004】路径4：异常处理
输入：任意有效源，但后端返回错误
预期执行：
  1. response.ok = false
  2. throw Error 被触发
  3. catch块执行
期望结果：
  - repoStatus 包含 "❌"
  - isAnswering 仍为false
  - 应用不崩溃
验证：Mock fetch返回失败状态码
```

---

#### 【模块2】sendMessage 函数控制流

```
START
  │
  ├─ 条件1: query.value.trim() 为空 OR !repoId OR isAnswering?
  │  ├─ YES → RETURN
  │  └─ NO → 继续
  │
  ├─ isAnswering = true
  ├─ AI 消息内容 = ''
  │
  ├─ FETCH /api/chat
  │
  ├─ 条件2: !response.ok OR !response.body?
  │  ├─ YES → throw Error
  │  └─ NO → 继续
  │
  ├─ reader = response.body.getReader()
  ├─ buffer = ''
  │
  ├─ WHILE循环：
  │  ├─ 读取数据chunk
  │  ├─ buffer += decode(chunk)
  │  ├─ 条件3: buffer.split('\n\n')
  │  │  └─ FOR每个event:
  │  │     ├─ 条件4: line.startsWith('data: ')?
  │  │     ├─ 条件5: data === '[DONE]'?
  │  │     └─ AI 消息内容 += data
  │  └─ UNTIL done
  │
  ├─ CATCH异常:
  │  └─ AI 消息内容 = error.message
  │
  ├─ FINALLY:
  │  └─ isAnswering = false
  │
END
```

**圈复杂度计算：**
- 决策点：5个 (条件1-5) + catch + finally + while + for
- 圈复杂度 M = 5 + 1 (while) + 1 (for) = **7**

##### 基本路径设计：

| 路径编号 | 条件组合 | 触发条件 |
|--------|--------|---------|
| 路径1 | query为空 | `query = ""` |
| 路径2 | repoId为空 | `repoId = ""` |
| 路径3 | 正在回答中 | `isAnswering = true` |
| 路径4 | 响应失败 | `response.ok = false` |
| 路径5 | 正常流式接收（单chunk） | response成功 + 单个chunk |
| 路径6 | 流式接收多chunks | response成功 + 多个chunks + 遇到[DONE] |
| 路径7 | 流处理异常 | 流处理过程中异常 |

##### 白盒测试用例：

```
【TC-WB-005】路径1：空问题检测
输入：query = "", repoId = "valid-id"
预期：直接return，fetch未调用

【TC-WB-006】路径2：缺少repoId
输入：query = "有效问题", repoId = ""
预期：直接return，fetch未调用

【TC-WB-007】路径3：重复回答防护
输入：query = "问题", isAnswering = true（已在回答）
预期：直接return，新请求不发送

【TC-WB-008】路径4：响应失败处理
输入：有效query和repoId，但后端返回500
预期：
  - fetch被调用
  - 进入catch块
  - AI 消息内容 = "...错误信息..."
  - isAnswering = false

【TC-WB-009】路径5：单chunk流式接收
输入：后端返回单个SSE chunk
Mock数据：
  response.body.getReader() 返回:
    {done: false, value: "data: Hello\n\n"}
    {done: true}
预期：
  - AI 消息内容 = "Hello"
  - isAnswering = false

【TC-WB-010】路径6：多chunk流式接收[DONE]
输入：后端返回多个chunk + [DONE]
Mock数据：
  chunk1: "data: 我是\n\n"
  chunk2: "data: 一个\n\n"
  chunk3: "data: [DONE]\n\n"
预期：
  - AI 消息内容 逐步追加 "我是一个"
  - 接收[DONE]时停止
  - 最终AI 消息内容 = "我是一个"

【TC-WB-011】路径7：流处理异常
输入：流处理过程中reader.read()抛出异常
预期：
  - catch块捕获异常
  - AI 消息内容 = 错误信息
  - isAnswering = false
```

---

#### 【模块3】readApiResponse 函数控制流

```
START
  │
  ├─ text = await response.text()
  │
  ├─ 条件1: !text.trim()?
  │  ├─ YES → return {detail: "服务返回了空响应..."}
  │  └─ NO → 继续
  │
  ├─ TRY:
  │  └─ return JSON.parse(text)
  │
  ├─ CATCH:
  │  └─ return {detail: text}
  │
END
```

**圈复杂度：M = 2**

##### 白盒测试用例：

```
【TC-WB-012】空响应处理
输入：response.text() = ""
预期：返回 {detail: "服务返回了空响应（HTTP 200）"}

【TC-WB-013】仅空格响应
输入：response.text() = "   "
预期：返回 {detail: "服务返回了空响应（HTTP 404）"}

【TC-WB-014】有效JSON响应
输入：response.text() = '{"repo_id": "123", "chunks": 100}'
预期：返回 {repo_id: "123", chunks: 100}

【TC-WB-015】无效JSON响应
输入：response.text() = "<html>404 Not Found</html>"
预期：返回 {detail: "<html>404 Not Found</html>"}

【TC-WB-016】null响应
输入：response.text() = "null"
预期：返回 null（有效JSON）

【TC-WB-017】数组JSON响应
输入：response.text() = '[{"id":1},{"id":2}]'
预期：返回数组结构
```

---

#### 【模块4】后端 index_repository_endpoint 函数控制流

```python
START
  │
  ├─ 条件1: !source (both github_url and local_path empty)?
  │  ├─ YES → HTTPException(422)
  │  └─ NO → 继续
  │
  ├─ TRY:
  │  └─ result = index_repository(source, branch)
  │
  ├─ CATCH Exception:
  │  ├─ logger.exception(...)
  │  └─ HTTPException(500, detail)
  │
  ├─ return IndexRepositoryResponse(...)
  │
END
```

**圈复杂度：M = 2**

##### 白盒测试用例：

```
【TC-WB-018】缺少github_url和local_path
输入：IndexRepositoryRequest(github_url=None, local_path=None)
预期：
  - 返回 HTTPException(status_code=422)
  - detail = "Either github_url or local_path must be provided."

【TC-WB-019】有效GitHub URL
输入：IndexRepositoryRequest(github_url="https://github.com/pytorch/pytorch", local_path=None, branch="main")
预期：
  - index_repository 被调用
  - 返回 IndexRepositoryResponse
  - 状态码200

【TC-WB-020】有效本地路径
输入：IndexRepositoryRequest(github_url=None, local_path="/path/to/repo", branch="dev")
预期：
  - index_repository 被调用，传入branch="dev"
  - 返回成功响应

【TC-WB-021】两个都有时优先local_path
输入：github_url="..." and local_path="/path"
预期：
  - 使用 local_path（或github_url，取决于逻辑）

【TC-WB-022】index_repository异常捕获
输入：有效请求但仓库不存在
预期：
  - 异常被捕获
  - 返回 HTTPException(500)
  - detail = 异常信息
```

---

#### 【模块5】后端 chat_endpoint 函数控制流

```python
START
  │
  ├─ ChatRequest(repo_id, question) 验证
  │
  ├─ generate_chat_stream(repo_id, question)
  │
  ├─ ASYNC FOR chunk in stream_rag_answer(...):
  │  ├─ yield _sse_data(chunk)
  │
  ├─ yield "data: [DONE]\n\n"
  │
  ├─ return StreamingResponse(...)
  │
END
```

**圈复杂度：M = 1**（主要逻辑在_sse_data）

##### 白盒测试用例：

```
【TC-WB-023】正常SSE流式生成
输入：ChatRequest(repo_id="valid", question="什么？")
预期：
  - StreamingResponse 返回text/event-stream
  - 逐个yield SSE格式的chunk
  - 最后yield [DONE]标记

【TC-WB-024】_sse_data格式验证
输入：chunk = "Hello World"
预期：返回 "data: Hello World\n\n"

【TC-WB-025】_sse_data多行处理
输入：chunk = "Line1\nLine2"
预期：返回 "data: Line1\ndata: Line2\n\n"

【TC-WB-026】_sse_data空行
输入：chunk = ""
预期：返回 "data: \n\n"
```

---

## 四、测试执行与验证

### 4.1 前端单元测试框架

```javascript
// tests/handleIndexRepo.test.js
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'

describe('handleIndexRepo', () => {
  let repositorySource, branch, isIndexing, repoStatus, repoId
  let fetchMock

  beforeEach(() => {
    repositorySource = ref('')
    branch = ref('main')
    isIndexing = ref(false)
    repoStatus = ref('')
    repoId = ref('')
    
    // Mock fetch
    fetchMock = vi.fn()
    global.fetch = fetchMock
  })

  it('TC-WB-001: 应忽略空仓库源', () => {
    repositorySource.value = ''
    handleIndexRepo()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('TC-WB-002: GitHub URL 成功索引', async () => {
    repositorySource.value = 'https://github.com/pytorch/pytorch'
    branch.value = 'main'
    
    fetchMock.mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({
        repo_id: 'test-123',
        status: 'success',
        chunks: 100
      })
    })

    await handleIndexRepo()
    
    expect(repoId.value).toBe('test-123')
    expect(repoStatus.value).toContain('索引完成')
    expect(isIndexing.value).toBe(false)
  })

  // ... 更多测试用例
})
```

### 4.2 后端单元测试框架

```python
# tests/test_repos.py
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

class TestIndexRepositoryEndpoint:
    
    def test_tc_wb_018_missing_source(self):
        """缺少source应返回422"""
        response = client.post('/api/repos/index', json={
            'branch': 'main'
        })
        assert response.status_code == 422
        assert 'Either' in response.json()['detail'][0]['msg']
    
    def test_tc_wb_019_github_url(self, monkeypatch):
        """有效GitHub URL应返回成功"""
        mock_index = lambda *a, **kw: type('Result', (), {
            'repo_id': 'test-123',
            'status': 'success',
            'chunks': 100
        })()
        monkeypatch.setattr(
            'src.ingestion.indexing.index_repository',
            mock_index
        )
        
        response = client.post('/api/repos/index', json={
            'github_url': 'https://github.com/pytorch/pytorch',
            'branch': 'main'
        })
        assert response.status_code == 200
        assert response.json()['repo_id'] == 'test-123'
```

---

## 五、测试覆盖率目标

| 指标 | 目标 |
|------|-----|
| **行覆盖率** | ≥ 85% |
| **分支覆盖率** | ≥ 80% |
| **路径覆盖率** | 100% （基本路径法） |
| **等价类覆盖** | 100% |
| **边界值覆盖** | 100% |

---

## 六、自动化测试策略

### 前端测试
```bash
npm test                    # 运行所有单元测试
npm run test:coverage       # 生成覆盖率报告
npm run test:ui             # 交互式测试运行器
```

### 后端测试
```bash
pytest tests/ -v            # 详细输出
pytest tests/ --cov=src     # 覆盖率报告
pytest tests/ -m smoke      # 只运行smoke测试
```

### 集成测试
```bash
pytest tests/integration/   # E2E集成测试
npm run test:e2e            # 前端E2E测试
```

---

## 七、测试优先级

| 优先级 | 测试用例 | 原因 |
|-------|---------|------|
| **P0 (关键)** | TC-BLK-001, TC-BLK-002, TC-WB-018, TC-WB-019 | 核心业务流程 |
| **P1 (高)** | TC-BLK-009, TC-BLK-010, TC-WB-008 | 异常处理 |
| **P2 (中)** | TC-BLK-003~008, TC-WB-005~007 | 边界/无效输入 |
| **P3 (低)** | TC-BLK-013~018, TC-WB-024~026 | 特殊场景 |

---

## 八、缺陷等级与处理

| 等级 | 定义 | 示例 |
|------|------|------|
| **Critical** | 功能完全不可用 | 索引API返回500 |
| **Major** | 核心功能受损 | 流式响应中断 |
| **Minor** | 功能可用但不完美 | 错误提示文案改进 |
| **Trivial** | 界面/文案优化 | 按钮颜色调整 |

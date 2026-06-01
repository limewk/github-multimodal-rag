# 测试执行报告

## 一、测试概览

### 项目信息
- **项目名称**: GitHub多模态RAG智能问答系统
- **测试方式**: 黑盒 + 白盒
- **测试方法**: 等价类划分、边界值分析、基本路径法
- **测试环境**: Node.js + Python + FastAPI

### 测试指标目标
| 指标 | 目标值 |
|------|-------|
| 行覆盖率 | ≥ 85% |
| 分支覆盖率 | ≥ 80% |
| 路径覆盖率 | 100% |
| 缺陷检出率 | ≥ 80% |

---

## 二、黑盒测试执行

### 2.1 前端黑盒测试

#### 测试工具
```bash
npm install --save-dev vitest @vitest/ui
npm install --save-dev @testing-library/vue
```

#### 执行命令
```bash
cd ui/
npm run test                    # 运行所有黑盒测试
npm run test -- --ui          # 交互式测试
npm run test -- --coverage    # 生成覆盖率
```

#### 测试用例统计

**功能1: 仓库索引 (handleProcess)**

| 测试用例ID | 等价类 | 描述 | 预期结果 | 状态 |
|-----------|-------|------|--------|------|
| TC-BLK-001 | EC1 | GitHub URL 有效 | 索引成功，显示chunks数 | ◻ |
| TC-BLK-002 | EC2 | 本地路径有效 | 索引成功 | ◻ |
| TC-BLK-003 | EC3 | 空仓库源 | 不发送请求 | ◻ |
| TC-BLK-004 | EC4 | 无效GitHub格式 | 后端返回错误 | ◻ |
| TC-BLK-005 | EC5 | 不存在本地路径 | 后端返回404 | ◻ |
| TC-BLK-006 | EC6 | XSS特殊字符 | 拒绝执行脚本 | ◻ |
| TC-BLK-007 | 边界 | 最小长度URL | 处理或拒绝 | ◻ |
| TC-BLK-008 | 边界 | 超长URL(>2048) | 拒绝或截断 | ◻ |
| TC-BLK-009 | EC7-9 | 分支名处理 | 使用指定分支 | ◻ |

**功能2: 问答功能 (handleQuery)**

| 测试用例ID | 等价类 | 描述 | 预期结果 | 状态 |
|-----------|-------|------|--------|------|
| TC-BLK-010 | EC10 | 正常问题 | 接收回答 | ◻ |
| TC-BLK-011 | EC11 | 短问题 | 接收回答 | ◻ |
| TC-BLK-012 | EC12 | 超长问题 | 处理成功 | ◻ |
| TC-BLK-013 | EC13 | 空问题 | 不发送请求 | ◻ |
| TC-BLK-014 | EC14 | 缺少repoId | 输入框禁用 | ◻ |
| TC-BLK-015 | EC18 | 正常SSE流 | 逐步显示 | ◻ |
| TC-BLK-016 | EC19 | 空SSE数据 | 正确处理 | ◻ |
| TC-BLK-017 | EC20 | 格式错误SSE | 显示错误 | ◻ |
| TC-BLK-018 | EC22 | 多行SSE数据 | 保留换行 | ◻ |

**异常与状态测试**

| 测试用例ID | 场景 | 预期结果 | 状态 |
|-----------|------|--------|------|
| TC-BLK-019 | 网络错误 | 显示友好错误信息 | ◻ |
| TC-BLK-020 | HTTP 500 | 显示服务器错误 | ◻ |
| TC-BLK-021 | 空响应体 | 显示"空响应"提示 | ◻ |
| TC-BLK-022 | 非JSON响应 | 显示原始文本 | ◻ |
| TC-BLK-023 | 快速连续请求 | 防止重复/并发 | ◻ |
| TC-BLK-024 | 清空历史 | 重置所有状态 | ◻ |

**测试结果统计**
```
总计: 24个测试用例
通过: 0/24 (0%)
失败: 0/24 (0%)
待执行: 24/24 (100%)
```

---

### 2.2 后端黑盒测试

#### 测试工具
```bash
pip install pytest pytest-asyncio pytest-cov
```

#### 执行命令
```bash
cd backend/
pytest tests/test_basic_units.py::TestIndexRepositoryEndpoint -v
pytest tests/test_basic_units.py::TestChatEndpoint -v
pytest tests/test_basic_units.py -v --cov=src --cov-report=html
```

#### 测试用例统计

**模块1: 仓库索引端点 (/api/repos/index)**

| 测试用例ID | 等价类 | 输入 | 预期状态码 | 状态 |
|-----------|-------|------|----------|------|
| TC-BLK-001 | EC1 | github_url=有效URL | 200 | ◻ |
| TC-BLK-002 | EC2 | local_path=有效路径 | 200 | ◻ |
| TC-BLK-003 | EC7 | branch=main | 200 | ◻ |
| TC-BLK-004 | EC3 | 缺少github_url和local_path | 422 | ◻ |
| TC-BLK-005 | EC3 | github_url=None, local_path=None | 422 | ◻ |
| TC-BLK-006 | EC4 | github_url=无效格式 | 500 | ◻ |
| TC-BLK-007 | 边界 | github_url="" | 422 | ◻ |
| TC-BLK-008 | 边界 | github_url="   " | 422 | ◻ |
| TC-BLK-009 | 边界 | 超长URL(>2048) | 500 | ◻ |
| TC-BLK-010 | 边界 | branch="a"(单字符) | 200 | ◻ |
| TC-BLK-012 | 异常 | 网络超时 | 500 | ◻ |
| TC-BLK-013 | 异常 | 文件不存在 | 500 | ◻ |
| TC-BLK-014 | 异常 | 权限被拒绝 | 500 | ◻ |

**模块2: 聊天端点 (/api/chat)**

| 测试用例ID | 等价类 | 输入 | 预期状态码 | 状态 |
|-----------|-------|------|----------|------|
| TC-BLK-015 | EC18 | 正常SSE流 | 200 + event-stream | ◻ |
| TC-BLK-016 | EC13 | question="" | 422或400 | ◻ |
| TC-BLK-017 | EC14 | 缺少repo_id | 422 | ◻ |
| TC-BLK-018 | EC15 | repo_id="" | 422 | ◻ |

**测试结果统计**
```
总计: 18个测试用例
通过: 0/18 (0%)
失败: 0/18 (0%)
待执行: 18/18 (100%)
```

---

## 三、白盒测试执行

### 3.1 前端白盒测试（基本路径法）

#### readJsonResponse 函数分析
- **圈复杂度**: 2
- **基本路径数**: 3

```
路径1: 空响应 → 条件1 YES → 返回
路径2: 有效JSON → 条件1 NO → try成功 → 返回
路径3: 无效JSON → 条件1 NO → try失败 → catch返回
```

#### 测试用例

| 路径 | 测试用例ID | 输入条件 | 验证点 | 状态 |
|------|-----------|--------|------|------|
| 路径1 | TC-WB-012 | text="" | 返回含"空响应"detail | ◻ |
| 路径1 | TC-WB-013 | text="   " | 返回含"空响应"detail | ◻ |
| 路径2 | TC-WB-014 | text='{"status":"ok"}' | 返回JSON对象 | ◻ |
| 路径3 | TC-WB-015 | text="invalid" | 返回原文本作为detail | ◻ |

#### handleProcess 函数分析
- **圈复杂度**: 4
- **基本路径数**: 4

```
路径1: 空源 → 条件1 YES → return
路径2: GitHub URL + 成功 → 条件1 NO → 条件2 YES → 条件3 YES
路径3: 本地路径 + 成功 → 条件1 NO → 条件2 NO → 条件3 YES
路径4: 任何 + 异常 → catch分支
```

| 路径 | 测试用例ID | 输入条件 | 验证点 | 状态 |
|------|-----------|--------|------|------|
| 路径1 | TC-WB-001 | repositorySource="" | fetch未调用 | ◻ |
| 路径2 | TC-WB-002 | GitHub URL, 响应成功 | repoId被赋值 | ◻ |
| 路径3 | TC-WB-003 | 本地路径, 响应成功 | payload含local_path | ◻ |
| 路径4 | TC-WB-004 | 任何源, 响应失败 | statusText含错误 | ◻ |

#### handleQuery 函数分析
- **圈复杂度**: 7
- **基本路径数**: 7

```
路径1: query为空 → 条件1A YES → return
路径2: repoId为空 → 条件1B YES → return
路径3: 正在回答 → 条件1C YES → return
路径4: 响应失败 → 条件1 NO → 条件2 YES → throw
路径5: 单chunk流 → 正常流程 + done
路径6: 多chunk流 → while循环 + for循环 + [DONE]
路径7: 流异常 → catch异常
```

| 路径 | 测试用例ID | 触发条件 | 验证点 | 状态 |
|------|-----------|--------|------|------|
| 路径1 | TC-WB-005 | query="" | fetch未调用 | ◻ |
| 路径2 | TC-WB-006 | repoId="" | fetch未调用 | ◻ |
| 路径3 | TC-WB-007 | isAnswering=true | fetch未调用 | ◻ |
| 路径4 | TC-WB-008 | response.ok=false | 进入catch | ◻ |
| 路径5 | TC-WB-009 | 单chunk + done | responseText=data | ◻ |
| 路径6 | TC-WB-010 | 多chunk + [DONE] | 正确追加&停止 | ◻ |
| 路径7 | TC-WB-011 | 流异常 | 异常被捕获 | ◻ |

### 3.2 后端白盒测试（基本路径法）

#### index_repository_endpoint 函数分析
- **圈复杂度**: 2
- **基本路径数**: 2

```
路径1: 缺少source → 条件1 YES → HTTPException(422)
路径2: 有source → 条件1 NO → try调用 → 成功/异常
```

| 路径 | 测试用例ID | 触发条件 | 验证点 | 状态 |
|------|-----------|--------|------|------|
| 路径1 | TC-WB-018 | github_url=None, local_path=None | 422错误 | ◻ |
| 路径2A | TC-WB-019 | github_url有效 | 200成功 | ◻ |
| 路径2B | TC-WB-020 | local_path有效 | 200成功 | ◻ |
| 路径2C | TC-WB-021 | 异常发生 | 500错误 | ◻ |

#### _sse_data 函数分析
- **圈复杂度**: 1
- **基本路径数**: 1

```
单一路径: 格式化SSE
```

| 测试用例ID | 输入 | 验证点 | 状态 |
|-----------|------|------|------|
| TC-WB-024 | "Hello" | "data: Hello\n\n" | ◻ |
| TC-WB-025 | "L1\nL2" | 多行格式化 | ◻ |
| TC-WB-026 | "" | "data: \n\n" | ◻ |

**测试结果统计**
```
前端基本路径覆盖: 0/11 (0%)
后端基本路径覆盖: 0/7 (0%)
总计: 18个白盒测试用例
```

---

## 四、执行步骤

### 第一步：准备测试环境
```bash
# 前端
cd ui/
npm install

# 后端
pip install pytest pytest-asyncio pytest-cov
```

### 第二步：运行前端测试
```bash
cd ui/
npm run test -- tests/basic.test.js -v
npm run test:coverage
```

### 第三步：运行后端测试
```bash
pytest tests/test_basic_units.py -v --cov=src
pytest tests/test_basic_units.py::TestIndexRepositoryEndpoint -v
pytest tests/test_basic_units.py::TestChatEndpoint -v
```

### 第四步：生成覆盖率报告
```bash
# 前端
npm run test:coverage

# 后端
pytest tests/test_basic_units.py --cov=src --cov-report=html
# 打开 htmlcov/index.html
```

---

## 五、缺陷跟踪模板

### 缺陷记录示例
```
【BUG-001】
严重程度: Critical
模块: 仓库索引
测试用例: TC-BLK-004
重现步骤: 
  1. 在仓库地址输入框输入无效URL格式
  2. 点击"开始分析"
预期结果: 显示"格式错误"提示
实际结果: 发送请求，后端500错误
根本原因: 前端未验证URL格式
修复建议: 添加URL正则验证

【BUG-002】
严重程度: Major
模块: 流式响应处理
测试用例: TC-BLK-017
重现步骤: 后端返回格式错误的SSE
预期结果: 显示错误提示
实际结果: responseText显示乱码
根本原因: SSE解析逻辑缺陷
```

---

## 六、关键测试数据

### 测试用例数统计
| 类别 | 数量 |
|------|------|
| 黑盒测试 | 42 |
| 白盒测试 | 25 |
| 集成测试 | 1 |
| **总计** | **68** |

### 覆盖率目标
| 指标 | 目标 | 实现 |
|------|------|------|
| 等价类覆盖 | 100% | ◻ |
| 边界值覆盖 | 100% | ◻ |
| 基本路径覆盖 | 100% | ◻ |
| 行覆盖率 | ≥85% | ◻ |
| 分支覆盖率 | ≥80% | ◻ |

---

## 七、测试进度表

| 阶段 | 开始日期 | 截止日期 | 状态 |
|------|---------|---------|------|
| 黑盒测试 | 2026-05-27 | 2026-05-29 | ◻ |
| 白盒测试 | 2026-05-29 | 2026-05-31 | ◻ |
| 缺陷修复 | 2026-06-01 | 2026-06-03 | ◻ |
| 回归测试 | 2026-06-03 | 2026-06-05 | ◻ |
| 最终评估 | 2026-06-05 | 2026-06-06 | ◻ |

---

## 八、风险评估

| 风险项 | 概率 | 影响 | 应对措施 |
|-------|------|------|--------|
| 后端API变更 | 中 | 高 | 定期同步API定义 |
| 网络环境问题 | 中 | 中 | 使用Mock模拟 |
| 流式响应超时 | 低 | 高 | 设置合理超时 |
| 依赖包版本冲突 | 低 | 中 | 锁定版本号 |

---

## 九、签名与审批

| 角色 | 姓名 | 签名 | 日期 |
|------|------|------|------|
| 测试负责人 | | | |
| 项目经理 | | | |
| 技术主管 | | | |

---

**文档版本**: v1.0  
**最后更新**: 2026-05-26  
**下次审查**: 测试完成后

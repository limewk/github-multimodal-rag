<script setup>
import { ref } from 'vue'

const repositorySource = ref('https://github.com/...')
const branch = ref('main')
const repoId = ref('')
const query = ref('')
const responseText = ref('')
const statusText = ref('')
const isIndexing = ref(false)
const isAnswering = ref(false)

const readJsonResponse = async (response) => {
  const text = await response.text()
  if (!text.trim()) {
    return { detail: `服务返回了空响应（HTTP ${response.status}）` }
  }

  try {
    return JSON.parse(text)
  } catch {
    return { detail: text }
  }
}

const handleProcess = async () => {
  if (!repositorySource.value.trim()) return
  isIndexing.value = true
  statusText.value = '正在构建索引...'
  responseText.value = ''

  try {
    const payload = repositorySource.value.startsWith('http')
      ? { github_url: repositorySource.value, branch: branch.value || 'main' }
      : { local_path: repositorySource.value, branch: branch.value || 'main' }
    const response = await fetch('/api/repos/index', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    const data = await readJsonResponse(response)
    if (!response.ok) {
      throw new Error(formatErrorDetail(data.detail, response.status))
    }
    repoId.value = data.repo_id
    statusText.value = `索引完成：${data.chunks} 个 chunks，repo_id=${data.repo_id}`
  } catch (error) {
    statusText.value = error.message || '索引构建失败'
  } finally {
    isIndexing.value = false
  }
}

const handleQuery = async () => {
  if (!query.value.trim() || !repoId.value || isAnswering.value) return
  isAnswering.value = true
  responseText.value = ''

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_id: repoId.value, question: query.value })
    })
    if (!response.ok || !response.body) {
      const data = await readJsonResponse(response)
      throw new Error(formatErrorDetail(data.detail, response.status))
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split('\n\n')
      buffer = events.pop() || ''
      for (const event of events) {
        const data = event
          .split('\n')
          .filter((line) => line.startsWith('data: '))
          .map((line) => line.slice(6))
          .join('\n')
        if (data === '[DONE]') break
        responseText.value += data
      }
    }
  } catch (error) {
    responseText.value = error.message || '大模型请求异常或服务尚未启动'
  } finally {
    isAnswering.value = false
  }
}

const formatErrorDetail = (detail, status) => {
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join('\n')
  }
  if (detail && typeof detail === 'object') {
    return JSON.stringify(detail)
  }
  return detail || `请求失败：${status}`
}
</script>

<template>
  <main class="container">
    <h1>面向 GitHub 仓库的多模态 RAG 辅助助手</h1>

    <section class="settings">
      <h2>仓库索引</h2>
      <div class="repo-form">
        <input v-model="repositorySource" type="text" placeholder="GitHub URL 或本地仓库路径" />
        <input v-model="branch" class="branch-input" type="text" placeholder="branch" />
        <button :disabled="isIndexing" @click="handleProcess">
          {{ isIndexing ? '索引中...' : '开始分析仓库' }}
        </button>
      </div>
      <p v-if="statusText" class="status">{{ statusText }}</p>
    </section>

    <section class="chat-area">
      <h2>智能问答</h2>
      <div class="chat-form">
        <input
          v-model="query"
          :disabled="!repoId || isAnswering"
          placeholder="先索引仓库，再基于源码、README 或图片引用提问"
          @keyup.enter="handleQuery"
        />
        <button :disabled="!repoId || isAnswering" @click="handleQuery">
          {{ isAnswering ? '生成中...' : '发送' }}
        </button>
      </div>

      <pre v-if="responseText" class="response-box">{{ responseText }}</pre>
    </section>
  </main>
</template>

<style scoped>
.container {
  font-family: Arial, Helvetica, sans-serif;
  margin: 0 auto;
  max-width: 920px;
  padding: 24px;
}

h1 {
  font-size: 28px;
  line-height: 1.3;
  margin: 0 0 24px;
}

h2 {
  font-size: 18px;
  margin: 0 0 12px;
}

.settings,
.chat-area {
  border-top: 1px solid #d8dee4;
  padding: 20px 0;
}

.repo-form,
.chat-form {
  display: flex;
  gap: 10px;
}

input {
  border: 1px solid #c9d1d9;
  border-radius: 6px;
  flex: 1;
  font-size: 14px;
  min-width: 0;
  padding: 9px 10px;
}

.branch-input {
  flex: 0 0 120px;
}

button {
  background: #1f6feb;
  border: 0;
  border-radius: 6px;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  padding: 9px 14px;
  white-space: nowrap;
}

button:disabled {
  background: #8c959f;
  cursor: not-allowed;
}

.status {
  color: #57606a;
  font-size: 14px;
  margin: 12px 0 0;
}

.response-box {
  background: #f6f8fa;
  border: 1px solid #d8dee4;
  border-radius: 6px;
  line-height: 1.5;
  margin-top: 16px;
  overflow: auto;
  padding: 14px;
  white-space: pre-wrap;
}

@media (max-width: 720px) {
  .repo-form,
  .chat-form {
    flex-direction: column;
  }

  .branch-input {
    flex: 1;
  }
}
</style>

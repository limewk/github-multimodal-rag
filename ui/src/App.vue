<script setup>
import { ref } from 'vue'
import axios from 'axios'

const githubUrl = ref('https://github.com/...')
const query = ref('')
const responseText = ref('')

const handleProcess = () => {
  alert(`开始请求后端处理仓库：${githubUrl.value}`)
}

const handleQuery = async () => {
  if (!query.value) return
  responseText.value = '思考中...'
  try {
    // 假设后端存在 POST /query 端点
    // const res = await axios.post('/api/query', { question: query.value })
    // responseText.value = res.data.answer
    setTimeout(() => {
      responseText.value = `这是针对您的多模态问题的模拟回答：\n\n您询问的是 "${query.value}"。 (暂未真正连接后端 API)`
    }, 1000)
  } catch (error) {
    responseText.value = '大模型请求异常或服务尚未启动'
  }
}
</script>

<template>
  <div class="container">
    <h1>面向 GitHub 仓库的多模态RAG辅助助手</h1>
    
    <div class="settings">
      <h2>⚙️ 设置</h2>
      <input v-model="githubUrl" type="text" style="width: 300px; padding: 5px;" />
      <button @click="handleProcess">开始分析仓库索引</button>
    </div>

    <div class="chat-area">
      <h3>💬 智能问答</h3>
      <input 
        v-model="query" 
        @keyup.enter="handleQuery" 
        placeholder="您可以指着具体的架构图、Issue或者源码段提问"
        style="width: 400px; padding: 5px;"
      />
      <button @click="handleQuery">发送</button>
      
      <div v-if="responseText" class="response-box">
        <p>{{ responseText }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container {
  font-family: sans-serif;
  margin: 0 auto;
  max-width: 800px;
  padding: 20px;
}
.settings {
  background: #f5f5f5;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
}
.chat-area {
  margin-top: 20px;
}
.response-box {
  margin-top: 20px;
  padding: 15px;
  background-color: #eef8ff;
  border-left: 4px solid #007bff;
  white-space: pre-wrap;
}
button {
  margin-left: 10px;
  padding: 6px 12px;
  cursor: pointer;
}
</style>

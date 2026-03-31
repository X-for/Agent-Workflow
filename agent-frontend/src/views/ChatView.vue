<template>
  <div class="chat-layout">
    <!-- 顶部状态栏 -->
    <header class="chat-header">
      <div class="header-left">
        <el-button circle icon="ArrowLeft" @click="$router.push('/')" />
        <div class="task-info">
          <span class="task-name">任务执行中: {{ taskId }}</span>
          <span class="status-dot"></span>
          <span class="status-text">Agent 在线</span>
        </div>
      </div>
      <div class="header-right">
        <el-button type="danger" link @click="clearChat">
          <span class="icon">🧹</span> 清空上下文
        </el-button>
      </div>
    </header>

    <!-- 聊天记录滚动区 -->
    <main class="chat-scroll-area" ref="chatHistoryRef">
      <div class="chat-container">
        
        <div 
          v-for="(msg, index) in messages" 
          :key="index" 
          :class="['message-row', msg.role]"
        >
          <!-- 头像 -->
          <div class="avatar" :class="msg.role">
            {{ msg.role === 'user' ? '🧑' : '🤖' }}
          </div>
          
          <div class="message-content">
            <!-- 名字 -->
            <div class="sender-name" v-if="msg.role === 'agent'">
              {{ msg.agentName || 'Agent' }}
            </div>
            
            <!-- 如果 Agent 调用了工具 -->
            <div v-if="msg.toolCall" class="tool-call-box">
              <div class="tool-header">
                <span class="tool-icon">🛠️</span>
                <span class="tool-title">调用工具：{{ msg.toolCall.name }}</span>
              </div>
              <div class="tool-code">
                <code>{{ msg.toolCall.args }}</code>
              </div>
            </div>
            
            <!-- 正文气泡 -->
            <div class="text-bubble" v-if="msg.content || msg.loading">
              <span v-if="msg.content">{{ msg.content }}</span>
              
              <!-- 优雅的思考动画 -->
              <div v-if="msg.loading" class="thinking-indicator">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 底部占位符，防止最后一条消息被输入框挡住 -->
        <div class="scroll-anchor"></div>
      </div>
    </main>

    <!-- 底部悬浮输入区 -->
    <div class="input-wrapper">
      <div class="input-container">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="1"
          :autosize="{ minRows: 1, maxRows: 4 }"
          placeholder="给 Agent 发送指令... (Shift + Enter 换行，Enter 发送)"
          @keydown.enter="handleEnter"
          class="modern-input"
        />
        <button 
          class="send-btn" 
          :class="{ active: inputText.trim().length > 0 }"
          @click="sendMessage"
          :disabled="isSending || !inputText.trim()"
        >
          <span class="send-icon">↑</span>
        </button>
      </div>
      <div class="footer-tip">Agent Workflow 由 Vue 3 + Element Plus 强力驱动</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const taskId = ref(route.params.taskId || 'Unknown_Task')
const chatHistoryRef = ref(null)

const messages = ref([
  {
    role: 'agent',
    agentName: '系统管家',
    content: '你好！工作流已加载完毕，你可以随时向我下发指令。'
  }
])

const inputText = ref('')
const isSending = ref(false)

const scrollToBottom = async () => {
  await nextTick()
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
  }
}

// 处理回车发送 (阻止默认的换行行为)
const handleEnter = (e) => {
  if (!e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

const sendMessage = async () => {
  if (!inputText.value.trim() || isSending.value) return

  const userMsg = inputText.value
  messages.value.push({ role: 'user', content: userMsg })
  
  inputText.value = ''
  isSending.value = true
  scrollToBottom()

  const agentResponseIndex = messages.value.length
  messages.value.push({
    role: 'agent',
    agentName: '处理节点_01',
    content: '',
    loading: true
  })
  scrollToBottom()

  // 模拟思考和工具调用
  setTimeout(() => {
    messages.value[agentResponseIndex].loading = false
    messages.value[agentResponseIndex].toolCall = {
      name: 'search_database',
      args: `{\n  "query": "${userMsg}",\n  "limit": 5\n}`
    }
    messages.value[agentResponseIndex].content = '我已经检索了相关数据。'
    scrollToBottom()

    setTimeout(() => {
      messages.value.push({
        role: 'agent',
        agentName: '总结节点',
        content: `根据你刚才下发的指令 "${userMsg}"，我已经完成了数据处理和分析工作，并已同步到系统中。还需要我做些什么吗？`
      })
      isSending.value = false
      scrollToBottom()
    }, 1500)

  }, 1200)
}

const clearChat = () => {
  messages.value = [{ role: 'agent', agentName: '系统管家', content: '上下文已重置。' }]
}

onMounted(() => {
  scrollToBottom()
})
</script>

<style scoped>
.chat-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  background-color: var(--el-bg-color-page);
}

/* 顶部状态栏 */
.chat-header {
  height: 56px;
  background-color: var(--el-bg-color-overlay);
  border-bottom: 1px solid var(--el-border-color-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.task-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.task-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.status-dot {
  width: 8px;
  height: 8px;
  background-color: var(--el-color-success);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--el-color-success);
}
.status-text {
  font-size: 0.8rem;
  color: var(--el-text-color-secondary);
}

/* 聊天滚动区 */
.chat-scroll-area {
  flex-grow: 1;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.chat-container {
  max-width: 860px;
  margin: 0 auto;
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.scroll-anchor {
  height: 80px; /* 为底部输入框留出空间 */
}

/* 消息行 */
.message-row {
  display: flex;
  gap: 16px;
  max-width: 100%;
}

.message-row.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}
.avatar.agent { background: #fff; border: 1px solid var(--el-border-color-lighter); }
html.dark .avatar.agent { background: var(--el-bg-color); }
.avatar.user { background: var(--el-color-primary); }

.message-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 80%;
}

.message-row.user .message-content {
  align-items: flex-end;
}

.sender-name {
  font-size: 0.8rem;
  color: var(--el-text-color-secondary);
  font-weight: 500;
}

/* 气泡样式 */
.text-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 1rem;
  line-height: 1.6;
  word-break: break-word;
}

.message-row.user .text-bubble {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-text-color-primary);
  border-bottom-right-radius: 2px;
}
html.dark .message-row.user .text-bubble {
  background-color: var(--el-color-primary-dark-2);
}

.message-row.agent .text-bubble {
  background-color: transparent;
  color: var(--el-text-color-primary);
  padding: 0; /* Agent 回复采用极简无边框样式，类似 ChatGPT */
}

/* 工具调用卡片 */
.tool-call-box {
  background-color: var(--el-fill-color-light);
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  overflow: hidden;
  margin-bottom: 4px;
}

.tool-header {
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: var(--el-fill-color);
  font-size: 0.85rem;
  color: var(--el-text-color-regular);
  font-weight: 500;
}

.tool-code {
  padding: 12px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.8rem;
  color: var(--el-text-color-secondary);
  white-space: pre-wrap;
}

/* 思考动画 */
.thinking-indicator {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}
.dot {
  width: 6px;
  height: 6px;
  background-color: var(--el-text-color-secondary);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}
.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* 底部输入区 */
.input-wrapper {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, var(--el-bg-color-page) 60%, transparent);
  padding: 24px 20px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: none; /* 让背景渐变不可点击，防止挡住滚动内容 */
}

.input-container {
  max-width: 800px;
  width: 100%;
  position: relative;
  pointer-events: auto; /* 恢复输入框的点击能力 */
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color);
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.06);
  padding: 12px;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  transition: border-color 0.2s;
}

.input-container:focus-within {
  border-color: var(--el-color-primary);
}

/* 覆盖 Element Plus 默认输入框样式，使其无边框 */
:deep(.modern-input .el-textarea__inner) {
  box-shadow: none !important;
  background: transparent !important;
  padding: 0 !important;
  font-size: 1rem;
  line-height: 1.5;
}

.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background-color: var(--el-fill-color);
  color: var(--el-text-color-placeholder);
  cursor: not-allowed;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.send-btn.active {
  background-color: var(--el-color-primary);
  color: #fff;
  cursor: pointer;
}

.send-btn.active:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
}

.send-icon {
  font-weight: bold;
  font-size: 1.2rem;
}

.footer-tip {
  margin-top: 12px;
  font-size: 0.75rem;
  color: var(--el-text-color-placeholder);
}
</style>
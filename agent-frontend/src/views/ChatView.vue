<template>
  <div class="chat-container">
    <!-- 顶部导航栏 -->
    <div class="chat-header">
      <div class="header-left">
        <el-button icon="ArrowLeft" circle @click="$router.push('/')" />
        <span class="task-title">当前对话任务: {{ taskId }}</span>
      </div>
      <div class="header-right">
        <!-- 你可以在这里加一个清空对话的按钮 -->
        <el-button type="danger" plain size="small" @click="clearChat">清空对话</el-button>
      </div>
    </div>

    <!-- 聊天记录展示区 -->
    <div class="chat-history" ref="chatHistoryRef">
      <div 
        v-for="(msg, index) in messages" 
        :key="index" 
        :class="['message-wrapper', msg.role === 'user' ? 'is-user' : 'is-agent']"
      >
        <!-- 头像 -->
        <div class="avatar">
          {{ msg.role === 'user' ? '🧑' : '🤖' }}
        </div>
        
        <!-- 消息气泡 -->
        <div class="message-content">
          <!-- 名字 -->
          <div class="sender-name">
            {{ msg.role === 'user' ? 'You' : (msg.agentName || 'Agent') }}
          </div>
          
          <!-- 正文 -->
          <div class="text-bubble">
            <!-- 如果 Agent 正在调用工具，展示工具调用过程 -->
            <div v-if="msg.toolCall" class="tool-call-info">
              <el-tag size="small" type="info">
                🛠️ 正在调用工具: {{ msg.toolCall.name }}
              </el-tag>
              <div class="tool-args">{{ msg.toolCall.args }}</div>
            </div>
            
            <!-- 普通文本内容 -->
            <span v-if="msg.content">{{ msg.content }}</span>
            
            <!-- Loading 状态 -->
            <span v-if="msg.loading" class="loading-dots">
              思考中<span>.</span><span>.</span><span>.</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部输入区 -->
    <div class="chat-input-area">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="3"
        placeholder="输入你想让 Agent 帮忙做的事情... (按 Ctrl+Enter 发送)"
        @keydown.ctrl.enter.prevent="sendMessage"
      />
      <div class="send-action">
        <el-button type="primary" :disabled="!inputText.trim() || isSending" @click="sendMessage">
          发送请求
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
// 从路由参数中获取当前正在对话的任务 ID
const taskId = ref(route.params.taskId || '未知任务')

// 聊天记录数组
// role: 'user' | 'agent'
const messages = ref([
  {
    role: 'agent',
    agentName: 'System',
    content: '你好！我是你的 Agent 助手，工作流已加载完毕，随时可以开始工作。请问有什么我可以帮你的？'
  }
])

const inputText = ref('')
const isSending = ref(false)
const chatHistoryRef = ref(null)

// 滚动到底部的辅助方法
const scrollToBottom = async () => {
  await nextTick()
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
  }
}

// 发送消息逻辑
const sendMessage = async () => {
  if (!inputText.value.trim() || isSending.value) return

  const userMsg = inputText.value
  
  // 1. 把用户的消息推入列表
  messages.value.push({
    role: 'user',
    content: userMsg
  })
  
  inputText.value = '' // 清空输入框
  isSending.value = true
  scrollToBottom()

  // 2. 模拟向后端发送请求，创建一个带有 loading 状态的临时 Agent 消息
  const agentResponseIndex = messages.value.length
  messages.value.push({
    role: 'agent',
    agentName: '处理节点_1',
    content: '',
    loading: true
  })
  scrollToBottom()

  // 【教学点】：这里你需要替换成真实的后端请求逻辑 (如 fetch / websocket)
  // 比如： const res = await fetch('/api/chat', { body: JSON.stringify({ message: userMsg, taskId: taskId.value }) })
  
  // 模拟网络延迟和 Agent 调用工具的过程
  setTimeout(() => {
    // 模拟 Agent 决定调用工具
    messages.value[agentResponseIndex].loading = false
    messages.value[agentResponseIndex].toolCall = {
      name: 'search_google',
      args: `{"query": "${userMsg}"}`
    }
    messages.value[agentResponseIndex].content = '我已经帮你查阅了相关资料。'
    scrollToBottom()

    // 模拟最终回复
    setTimeout(() => {
      messages.value.push({
        role: 'agent',
        agentName: '总结节点',
        content: `根据我查到的资料，针对你的请求 "${userMsg}"，我的建议是：这是一个非常好的想法，我们可以利用刚刚配置的工作流分发任务。`
      })
      isSending.value = false
      scrollToBottom()
    }, 1500)

  }, 1500)
}

// 清空对话
const clearChat = () => {
  messages.value = [
    { role: 'agent', agentName: 'System', content: '对话已清空，我们可以重新开始。' }
  ]
}

// 初始化时确保滚动在底部
onMounted(() => {
  scrollToBottom()
})
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  background-color: #f5f7fa;
}

.chat-header {
  height: 60px;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.task-title {
  margin-left: 15px;
  font-weight: bold;
  font-size: 16px;
  color: #303133;
}

.chat-history {
  flex-grow: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-wrapper {
  display: flex;
  max-width: 80%;
  gap: 12px;
}

/* 用户发的消息靠右，头像在右侧 */
.message-wrapper.is-user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

/* Agent 的消息靠左 */
.message-wrapper.is-agent {
  align-self: flex-start;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.message-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-wrapper.is-user .message-content {
  align-items: flex-end;
}

.sender-name {
  font-size: 12px;
  color: #909399;
}

.text-bubble {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.5;
  color: #303133;
  word-break: break-all;
}

.is-user .text-bubble {
  background-color: #409EFF;
  color: #fff;
  border-top-right-radius: 0;
}

.is-agent .text-bubble {
  background-color: #fff;
  border: 1px solid #ebeef5;
  border-top-left-radius: 0;
}

.tool-call-info {
  background-color: #f4f4f5;
  padding: 8px;
  border-radius: 4px;
  margin-bottom: 8px;
  font-family: monospace;
}

.tool-args {
  margin-top: 4px;
  font-size: 12px;
  color: #606266;
}

.loading-dots span {
  animation: blink 1.4s infinite both;
}
.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes blink {
  0% { opacity: 0.2; }
  20% { opacity: 1; }
  100% { opacity: 0.2; }
}

.chat-input-area {
  padding: 20px;
  background-color: #fff;
  border-top: 1px solid #e4e7ed;
}

.send-action {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}
</style>
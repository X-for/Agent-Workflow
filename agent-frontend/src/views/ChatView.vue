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
            <!-- 名字和折叠控制按钮 -->
            <div class="sender-header" v-if="msg.role === 'agent'">
              <span class="sender-name">{{ msg.agentName || 'Agent' }}</span>
              <el-button 
                v-if="!msg.loading && msg.content" 
                size="small" 
                link 
                type="info"
                @click="msg.isCollapsed = !msg.isCollapsed"
                style="margin-left: 8px; font-size: 12px;"
              >
                {{ msg.isCollapsed ? '展开内容 ▾' : '折叠收起 ▴' }}
              </el-button>
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
            <!-- 使用 v-show 控制整个内容区域的显示/隐藏 -->
            <div v-show="!msg.isCollapsed">
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
              <!-- 使用 v-html 动态渲染解析好的 Markdown HTML -->
                <div 
                  v-if="msg.content" 
                  class="markdown-body"
                  v-html="md.render(msg.content)"
                ></div>
                
                <!-- 优雅的思考动画 -->
                <div v-if="msg.loading" class="thinking-indicator">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </div>
              </div>
            </div>
            <!-- 折叠后的精简提示 -->
            <div v-show="msg.isCollapsed" class="collapsed-tip text-bubble">
              <i>已折叠的节点输出...</i>
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
        <!-- 新增：隐藏的真实文件选择框 -->
        <input 
          type="file" 
          ref="fileInputRef" 
          style="display: none" 
          @change="handleFileUpload" 
        />
        
        <!-- 新增：显示出来的附件按钮 -->
        <button 
          class="attach-btn" 
          @click="triggerFileInput"
          title="上传文件到当前工作区"
        >
          <span class="attach-icon">📎</span>
        </button>

        <el-input
          v-model="inputText"
          type="textarea"
          :rows="1"
          :autosize="{ minRows: 1, maxRows: 4 }"
          placeholder="给 Agent 发送指令... (Shift + Enter 换行，Enter 发送)"
          @keydown.enter="handleEnter"
          class="modern-input"
        />
        <!-- 保持原来的发送按钮不变 -->
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
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
// 引入一种你喜欢的高亮主题（这里用 github 的深色主题，很百搭）
import 'highlight.js/styles/github-dark.css' 

// 初始化 MarkdownIt 并配置高亮规则
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true, // 🌟 新增这一行：将 \n 解析为 <br>
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return '<pre class="hljs"><code>' +
               hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
               '</code></pre>';
      } catch (__) {}
    }
    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>';
  }
})

const route = useRoute()
const taskId = ref(route.params.taskId || 'Unknown_Task')
const chatHistoryRef = ref(null)

const API_BASE_URL = 'http://localhost:8001'

const messages = ref([
  {
    role: 'agent',
    agentName: '系统管家',
    content: `你好！[${taskId.value}] 工作流已加载完毕，你可以随时向我下发指令。`
  }
])

const inputText = ref('')
const isSending = ref(false)

// 专门负责更新折叠状态的函数
const updateCollapseState = () => {
  // 只过滤出 Agent 消息
  const agentMessages = messages.value.filter(m => m.role === 'agent');
  if (agentMessages.length > 0) {
    // 先把所有 Agent 消息都设为折叠
    agentMessages.forEach(msg => {
      msg.isCollapsed = true;
    });
    // 最后一条 Agent 消息强制展开
    agentMessages[agentMessages.length - 1].isCollapsed = false;
  }
}

// 自动滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
  }
}

// 处理回车发送
const handleEnter = (e) => {
  if (!e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// 处理文件上传
// 引用文件输入框
const fileInputRef = ref(null)

// 触发隐藏的 input
const triggerFileInput = () => {
  fileInputRef.value.click()
}

// 处理文件上传
const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  // 立即在聊天框里显示一条系统提示，告诉用户正在上传
  messages.value.push({ 
    role: 'agent', 
    agentName: '系统管家', 
    content: `正在上传文件：**${file.name}** ...` 
  })
  scrollToBottom()

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await fetch(`${API_BASE_URL}/api/upload/${taskId.value}`, {
      method: 'POST',
      body: formData // 注意：传 formData 时不要加 Content-Type header，浏览器会自动处理 boundary
    })
    
    const result = await response.json()
    if (response.ok && result.status === 'success') {
      // 告诉用户上传成功，并提示他可以让 Agent 读取了
      messages.value.push({ 
        role: 'agent', 
        agentName: '系统管家', 
        content: `✅ 文件 **${file.name}** 已成功保存到工作区目录。\n\n你现在可以要求 Agent 读取或分析它了。` 
      })
    } else {
      throw new Error(result.message)
    }
  } catch (error) {
    ElMessage.error(`上传失败: ${error.message}`)
    messages.value.push({ 
      role: 'agent', 
      agentName: '系统管家', 
      content: `❌ 文件 **${file.name}** 上传失败。` 
    })
  } finally {
    // 清空 input，允许重复上传同名文件
    event.target.value = ''
    scrollToBottom()
  }
}

// === 核心：发起真实后端对话请求 ===
const sendMessage = async () => {
  if (!inputText.value.trim() || isSending.value) return

  const userMsg = inputText.value
  // 1. 把用户的消息推入列表
  messages.value.push({ role: 'user', content: userMsg })
  
  inputText.value = ''
  isSending.value = true
  scrollToBottom()

  // 2. 准备发给后端的数据（需要带上当前任务的图纸信息）
  // 尝试从本地存储中获取刚才编排好的节点和连线
  const savedData = localStorage.getItem(`workflow_${taskId.value}`)
  let nodes = []
  let edges = []
  if (savedData) {
    const parsed = JSON.parse(savedData)
    nodes = parsed.nodes || []
    edges = parsed.edges || []
  }

// ====== payload：======
  // 将前端的 nodes 映射成后端 backend/graph.py 想要的格式
  const formattedNodes = nodes.map(n => ({
    id: n.id,
    name: n.label, // 后端要 name，我们把 label 给它
    description: n.data?.prompt || '', // 后端要 description，我们把 prompt 给它
    tools: n.data?.tools || [],  // 确保 tools 也是个数组
    models: n.data?.models || 'deepseek-chat' // 传递模型信息
  }))

  // 确保 edges 格式也是后端想要的 (Vue Flow 默认的连线是 source 和 target，但你的后端可能是 from 和 to，我们做个保险转换)
  const formattedEdges = edges.map(e => ({
    from: e.source, // Vue Flow 叫 source，后端叫 from
    to: e.target,    // Vue Flow 叫 target，后端叫 to
    is_debate: e.data?.is_debate === true, // 如果有辩论属性，也传递给后端  
    is_reject: e.data?.is_reject === true, // 
  }))

  const payload = {
    thread_id: taskId.value,
    user_input: userMsg,
    nodes: formattedNodes,
    edges: formattedEdges
  }
// ==========================

  // 3. 在聊天区创建一个空的 Agent 消息框，准备接收流式打字
  const agentResponseIndex = messages.value.length
  messages.value.push({
    role: 'agent',
    agentName: 'Agent 网络',
    content: '',
    loading: true // 显示思考中的小圆点
  })
  scrollToBottom()

  try {
    // 4. 发起 Fetch 请求，并处理 Server-Sent Events (流式响应)
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    // 关闭 Loading 状态，准备打字
    messages.value[agentResponseIndex].loading = false

    // 获取响应的可读流
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let done = false
    let buffer = ''

    // 5. 循环读取数据流
    while (!done) {
      const { value, done: readerDone } = await reader.read()
      done = readerDone
      
      if (value) {
        // 把新数据加入缓冲池
        buffer += decoder.decode(value, { stream: true })
        // 按 SSE 的标准结束符（双换行）进行切割
        const parts = buffer.split('\n\n')
        
        // 最后一个元素可能是不完整的数据块，留到下一次循环处理
        buffer = parts.pop()
        
        for (const part of parts) {
          if (part.startsWith('data: ')) {
            const jsonStr = part.replace('data: ', '').trim()
            if (jsonStr) {
              try {
                // 安全解析 JSON，完美保留所有换行和缩进
                const dataObj = JSON.parse(jsonStr)
                // 后端传过来的当前发言人
                const incomingAgent = dataObj.agentName || 'Agent 网络'
                
                // LangGraph 会有一些内部节点(比如 __start__), 我们过滤掉它
                if (incomingAgent.startsWith('__')) continue
                
                // 获取当前界面的最后一个消息气泡
                const lastMsg = messages.value[messages.value.length - 1]
                
                // 🌟 核心判断：如果最后一条消息就是当前 Agent 说的，直接追加字
                if (lastMsg.role === 'agent' && (lastMsg.agentName === incomingAgent || lastMsg.agentName === 'Agent 网络')) {
                  lastMsg.agentName = incomingAgent // 更新正确的名称
                  lastMsg.content += dataObj.content
                  lastMsg.loading = false
                } else {
                  // 🌟 如果换人了 (说明流转到了下一个节点)，我们新建一个聊天气泡！
                  messages.value.push({
                    role: 'agent',
                    agentName: incomingAgent,
                    content: dataObj.content,
                    loading: false
                  })
                }
                
                const el = chatHistoryRef.value
                if (el) {
                  // 判断距离底部的距离是否小于 100 像素
                  const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight <= 100
                  if (isAtBottom) {
                    scrollToBottom()
                  }
                }
                
              } catch (err) {
                console.warn("解析 chunk 失败:", jsonStr)
              }
            }
          }
        }
      }
    }
    // 流式数据接收完毕，更新折叠状态
    updateCollapseState()
  } catch (error) {
    console.error('对话请求失败:', error)
    messages.value[agentResponseIndex].loading = false
    messages.value[agentResponseIndex].content = '⚠️ 连接后端失败或发生错误，请检查 FastAPI 服务是否正常运行。'
    ElMessage.error('对话请求失败')
  } finally {
    // 无论成功还是失败，最后都解除发送按钮的禁用状态
    isSending.value = false
    scrollToBottom()
  }
}

// === 彻底清空上下文记忆 ===
const clearChat = async () => {
  // 先给用户弹个确认框（防止误触，毕竟删了就找不回了）
  try {
    await ElMessageBox.confirm(
      '确定要清空该工作流的上下文记忆吗？此操作无法撤销。',
      '⚠️ 清空记忆',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // 如果用户点确定，请求后端彻底清除 SQLite 记忆
    const response = await fetch(`${API_BASE_URL}/api/history/${taskId.value}`, {
      method: 'DELETE'
    })
    
    if (response.ok) {
      // 1. 清空前端界面的消息列表
      messages.value = [{ 
        role: 'agent', 
        agentName: '系统管家', 
        content: '✨ 上下文记忆已被彻底擦除。我们重新开始吧！' 
      }]
      ElMessage.success('上下文已彻底清空')
    } else {
      throw new Error('后端清理失败')
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('清理失败: ' + err.message)
    }
  }
}

onMounted(async () => {
  // 加载历史记忆
  try {
    const res = await fetch(`${API_BASE_URL}/api/history/${taskId.value}`)
    if (res.ok) {
      const data = await res.json()
      if (data.messages && data.messages.length > 0) {
        messages.value = data.messages
        updateCollapseState() // 加载历史后更新折叠状态
      }
    }
  } catch (e) {
    console.error('获取历史记录失败', e)
  }
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

/* --- Markdown 渲染样式 --- */
.markdown-body {
  font-family: inherit;
  line-height: 1.6;
}

/* 段落间距 */
.markdown-body p {
  margin-bottom: 12px;
}
.markdown-body p:last-child {
  margin-bottom: 0;
}

/* 代码块美化 */
.markdown-body pre {
  background-color: #1e1e1e !important;
  color: #d4d4d4;
  padding: 12px 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
  font-family: 'Fira Code', Consolas, Monaco, monospace;
  font-size: 0.9em;
}

/* 行内代码 */
.markdown-body code {
  background-color: var(--el-fill-color-dark);
  color: var(--el-color-danger);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9em;
}

/* pre 块内的 code 不需要行内样式 */
.markdown-body pre code {
  background-color: transparent;
  color: inherit;
  padding: 0;
  border-radius: 0;
}

/* 列表缩进 */
.markdown-body ul, .markdown-body ol {
  padding-left: 20px;
  margin-bottom: 12px;
}

/* 表格基本样式 */
.markdown-body table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 12px;
}

.markdown-body th, .markdown-body td {
  border: 1px solid var(--el-border-color);
  padding: 8px 12px;
}

/* 附件按钮样式 */
.attach-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background-color: transparent;
  color: var(--el-text-color-regular);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.attach-btn:hover {
  background-color: var(--el-fill-color-light);
  color: var(--el-color-primary);
}

.attach-icon {
  font-size: 1.2rem;
  transform: rotate(-45deg); /* 让别针稍微倾斜一点更好看 */
}

.sender-header {
  display: flex;
  align-items: center;
}
.collapsed-tip {
  color: var(--el-text-color-secondary);
  font-size: 0.85rem;
  background-color: var(--el-fill-color-light) !important;
  cursor: pointer;
}
.collapsed-tip:hover {
  background-color: var(--el-fill-color) !important;
}
</style>
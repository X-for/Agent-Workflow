<template>
  <div class="page-container">
    <!-- 头部区域：现代风标题和主按钮 -->
    <header class="page-header">
      <div class="title-group">
        <h1 class="gradient-title">Agent Workspace</h1>
        <p class="subtitle">管理和编排你的智能体工作流</p>
      </div>
      <el-button class="create-btn" type="primary" size="large" @click="createNewTask">
        <span class="icon">+</span> 创建新工作流
      </el-button>
    </header>

    <!-- 卡片网格：完全自适应 -->
    <div class="task-grid">
      <div 
        class="modern-card" 
        v-for="task in tasks" 
        :key="task.id"
      >
        <div class="card-content">
          <div class="card-header">
            <div class="avatar">🤖</div>
            <h3 class="task-name">{{ task.name }}</h3>
          </div>
          
          <div class="task-meta">
            <div class="meta-item">
              <span class="meta-icon">📁</span>
              <span class="meta-text">{{ task.path }}</span>
            </div>
            <p class="task-desc">{{ task.description }}</p>
          </div>
        </div>

        <!-- 悬浮操作栏 -->
        <div class="card-actions">
          <button class="action-btn chat-btn" @click="goToChat(task.id)">
            💬 对话
          </button>
          <button class="action-btn edit-btn" @click="goToEditor(task.id)">
            ⚙️ 编辑
          </button>
          <!-- 🌟 新增的复制按钮 -->
          <button class="action-btn copy-btn" @click="duplicateWorkflow(task)">
            📑 复制
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus' // 👈 增加引入


const router = useRouter()
const tasks = ref([])
// 增加一个 loading 状态
const loading = ref(true) 

// 后端 API 地址
const API_BASE_URL = 'http://localhost:8001'

onMounted(async () => {
  try {
    // 调用后端 GET /api/tasks 接口
    const response = await fetch(`${API_BASE_URL}/api/tasks`)
    if (!response.ok) throw new Error('网络请求失败')
    
    const data = await response.json()
    
    // 后端返回的是 {"tasks": ["dir1", "dir2"]} 格式
    // 我们把它映射成前端卡片需要的格式
    tasks.value = data.tasks.map(taskName => ({
      id: taskName, 
      name: taskName, 
      path: `/workspace/${taskName}`, 
      description: `基于目录 ${taskName} 的智能体工作流。`
    }))
  } catch (error) {
    console.error('获取任务失败:', error)
    // 如果后端没开或者报错，给个友好的提示，并塞一个测试数据防止页面全空
    ElMessage.error('无法连接到后端服务器，请检查 FastAPI 是否在 8001 端口运行！')
  } finally {
    loading.value = false
  }
})

// 替换原来的 createNewTask 函数
const createNewTask = async () => {
  try {
    const { value } = await ElMessageBox.prompt(
      '请输入工作流的名称 (这将在后端创建对应的文件夹)', 
      '🚀 创建新工作流', 
      {
        confirmButtonText: '确认创建',
        cancelButtonText: '取消',
        inputPattern: /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/, // 允许中文、字母、数字、下划线
        inputErrorMessage: '名称只能包含中英文、数字和下划线'
      }
    )
    if (value) {
      // 使用用户输入的名字作为路由参数跳转
      router.push(`/editor/${value}`)
    }
  } catch (e) {
    // 用户点击了取消，什么都不做
  }
}

// === 真正处理复制的逻辑 ===
const duplicateWorkflow = async (originalTask) => {
  try {
    // 1. 弹出输入框，让用户输入新名字
    const { value: newName } = await ElMessageBox.prompt(
      `为复制的 [${originalTask.name}] 输入一个新名称：`,
      '📑 复制工作流',
      {
        confirmButtonText: '确认复制',
        cancelButtonText: '取消',
        inputPattern: /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/,
        inputErrorMessage: '名称只能包含中英文、数字和下划线',
        inputValue: `${originalTask.name}_副本`
      }
    )

    if (!newName) return

    // 2. 发送请求给后端执行物理复制
    const res = await fetch(`${API_BASE_URL}/api/duplicate_workflow`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        original_id: originalTask.id,
        new_id: newName
      })
    })

    const data = await res.json()

    if (res.ok && data.status === 'success') {
      ElMessage.success(data.message)
      
      // 3. 复制前端 localStorage 里的画布坐标信息（这样编辑器里也能看到一模一样的拓扑图）
      const oldConfig = localStorage.getItem(`workflow_${originalTask.id}`)
      if (oldConfig) {
        localStorage.setItem(`workflow_${newName}`, oldConfig)
      }

      // 4. 将新任务直接插入当前列表，避免重新刷新整个页面
      tasks.value.unshift({
        id: newName,
        name: newName,
        path: `/workspace/${newName}`,
        description: `基于目录 ${newName} 的智能体工作流。`
      })
    } else {
      throw new Error(data.message)
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '复制失败，请重试')
    }
  }
}

const goToChat = (taskId) => router.push(`/chat/${taskId}`)
const goToEditor = (taskId) => router.push(`/editor/${taskId}`)
</script>

<style scoped>
/* 容器：限制最大宽度并居中，两边留白呼吸感 */
.page-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 40px 24px;
  height: 100%;
  overflow-y: auto;
}

/* 头部样式 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 48px;
}

.gradient-title {
  font-size: 2.5rem;
  font-weight: 800;
  margin: 0;
  /* 现代风渐变文字 */
  background: linear-gradient(135deg, #409EFF, #8E2DE2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  color: var(--el-text-color-secondary);
  margin: 8px 0 0;
  font-size: 1rem;
}

.create-btn {
  border-radius: 12px;
  font-weight: bold;
  padding: 12px 24px;
  transition: transform 0.2s;
}
.create-btn:hover {
  transform: translateY(-2px);
}
.create-btn .icon {
  margin-right: 6px;
  font-size: 1.2rem;
}

/* CSS Grid 响应式网格布局 */
.task-grid {
  display: grid;
  /* 魔法代码：自动适应列数，屏幕宽就显示3-4列，屏幕窄就变1-2列 */
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
}

/* 现代感卡片 */
.modern-card {
  background-color: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}

.modern-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
  border-color: var(--el-color-primary-light-5);
}

.card-content {
  padding: 24px;
  flex-grow: 1;
}

.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.avatar {
  font-size: 28px;
  background: var(--el-fill-color-light);
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  margin-right: 16px;
}

.task-name {
  margin: 0;
  font-size: 1.25rem;
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.task-meta {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  font-size: 0.85rem;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-light);
  padding: 6px 10px;
  border-radius: 6px;
  width: fit-content;
}

.meta-icon {
  margin-right: 6px;
}

.task-desc {
  margin: 0;
  font-size: 0.95rem;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 卡片操作按钮区 */
.card-actions {
  display: flex;
  border-top: 1px solid var(--el-border-color-lighter);
  background-color: var(--el-fill-color-blank);
}

.action-btn {
  flex: 1;
  padding: 16px 0;
  border: none;
  background: transparent;
  color: var(--el-text-color-regular);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.95rem;
}

.action-btn:hover {
  background-color: var(--el-fill-color-light);
  color: var(--el-color-primary);
}

.chat-btn, .edit-btn {
  border-right: 1px solid var(--el-border-color-lighter);
}
.copy-btn:hover {
  color: var(--el-color-success); /* 给复制按钮一个不同的 Hover 颜色 */
}
</style>
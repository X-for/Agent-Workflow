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
            💬 开始对话
          </button>
          <button class="action-btn edit-btn" @click="goToEditor(task.id)">
            ⚙️ 编辑节点
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const tasks = ref([])

onMounted(() => {
  tasks.value = [
    { id: 'task_001', name: '客服机器人', path: '/agents/customer_service', description: '负责解答用户的常见问题，已接入知识库。' },
    { id: 'task_002', name: '数据分析助手', path: '/agents/data_analyzer', description: '自动读取数据库并生成可视化分析报告。' },
    { id: 'task_003', name: '代码审查专家', path: '/agents/code_reviewer', description: '审查提交的 PR，提供优化建议。' },
  ]
})

const createNewTask = () => router.push('/editor')
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

.chat-btn {
  border-right: 1px solid var(--el-border-color-lighter);
}
</style>
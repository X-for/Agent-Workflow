<template>
  <div class="task-list-container">
    <div class="header">
      <h2>我的 Agent 任务</h2>
      <!-- 创建任务按钮，点击跳到空的编辑器页面 -->
      <el-button type="primary" size="large" @click="createNewTask">创建新任务</el-button>
    </div>

    <!-- 任务卡片列表 -->
    <el-row :gutter="20">
      <el-col :span="8" v-for="task in tasks" :key="task.id" style="margin-bottom: 20px;">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>{{ task.name }}</span>
            </div>
          </template>
          
          <div class="task-info">
            <p><strong>目录:</strong> {{ task.path }}</p>
            <p><strong>描述:</strong> {{ task.description }}</p>
          </div>

          <div class="actions">
            <!-- 跳转到对话界面 -->
            <el-button type="success" plain @click="goToChat(task.id)">开始对话</el-button>
            <!-- 跳转到编辑器界面 -->
            <el-button type="warning" plain @click="goToEditor(task.id)">编辑节点</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// 这个响应式变量用来存储从后端拉取到的任务列表
const tasks = ref([])

onMounted(async () => {
  // 【教学点】：这里是组件加载完成后执行的地方。
  // 以后你可以在这里写： const res = await fetch('你的后端API/getTasks')
  // 然后 tasks.value = await res.json()
  
  // 现在我们先用假数据（Mock数据）模拟一下后端的返回结果，让你能看到界面：
  tasks.value = [
    { id: 'task_001', name: '客服机器人', path: '/agents/customer_service', description: '负责解答用户的常见问题' },
    { id: 'task_002', name: '数据分析助手', path: '/agents/data_analyzer', description: '读取数据库并生成分析报告' }
  ]
})

// 路由跳转逻辑
const createNewTask = () => {
  router.push('/editor') // 不带 ID 就是新建
}

const goToChat = (taskId) => {
  router.push(`/chat/${taskId}`) // 带 ID 去对话
}

const goToEditor = (taskId) => {
  router.push(`/editor/${taskId}`) // 带 ID 去编辑
}
</script>

<style scoped>
.task-list-container {
  padding: 40px;
  max-width: 1200px;
  margin: 0 auto;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}
.card-header {
  font-weight: bold;
  font-size: 18px;
}
.task-info {
  font-size: 14px;
  color: #606266;
  margin-bottom: 20px;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
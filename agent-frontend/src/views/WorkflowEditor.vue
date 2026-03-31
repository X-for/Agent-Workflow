<template>
  <div class="editor-workspace">
    <!-- 顶部状态栏 -->
    <div class="editor-header">
      <div class="header-left">
        <el-button circle icon="ArrowLeft" @click="$router.push('/')" />
        <span class="workflow-title">{{ taskId }} <el-tag size="small" type="info">草稿</el-tag></span>
      </div>
      <div class="header-right">
        <el-button type="primary" round @click="saveWorkflow">
          <span style="margin-right: 4px;">💾</span> 保存编排
        </el-button>
      </div>
    </div>

    <div class="canvas-container">
      <!-- 悬浮式左侧组件库 (类似 Figma 面板) -->
      <div class="floating-sidebar">
        <div class="sidebar-header">
          <h3>组件库</h3>
        </div>
        <div class="components-list">
          <div 
            class="component-item" 
            draggable="true" 
            @dragstart="onDragStart($event, 'agent')"
          >
            <div class="comp-icon">🤖</div>
            <div class="comp-info">
              <span class="comp-name">Agent 节点</span>
              <span class="comp-desc">拖拽添加智能体</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Vue Flow 画布区域 -->
      <div class="canvas-area" @drop="onDrop" @dragover.prevent>
        <VueFlow 
          v-model:nodes="nodes" 
          v-model:edges="edges" 
          class="modern-flow"
          @connect="onConnect"
          @node-click="onNodeClick"
          @pane-click="closePanel"
        >
          <Background pattern-color="var(--el-border-color)" :gap="24" :size="2" />
          <Controls class="modern-controls" />
        </VueFlow>
      </div>

      <!-- 悬浮式右侧属性面板 (取代之前的 Drawer) -->
      <transition name="slide-panel">
        <div v-if="panelVisible && activeNode" class="floating-panel">
          <div class="panel-header">
            <h3>节点配置</h3>
            <div class="panel-actions">
              <el-button size="small" plain @click="duplicateNode">
                <span style="margin-right: 3px;">📑</span> 复制
              </el-button>
              <!-- 🌟 新增的删除按钮 -->
              <el-button size="small" type="danger" plain @click="deleteNode">
                <span style="margin-right: 3px;">🗑️</span> 删除
              </el-button>  
              <el-button size="small" plain @click="closePanel">
                <span style="margin-right: 3px;">🗑️</span> 关闭
              </el-button>
            </div>
          </div>
          
          <div class="panel-body">
            <el-form label-position="top">
              <el-form-item label="节点名称">
                <el-input v-model="activeNode.label" placeholder="给它起个名字..." />
              </el-form-item>

              <el-form-item label="系统提示词 (Prompt)">
                <el-input 
                  v-model="activeNode.data.prompt" 
                  type="textarea" 
                  :rows="8" 
                  resize="none"
                  placeholder="你是一个专业的数据分析师..." 
                />
              </el-form-item>

              <el-form-item label="挂载工具 (Tools)">
                <div class="tools-grid">
                  <div 
                    v-for="tool in availableTools" 
                    :key="tool.name"
                    :class="['tool-card', { active: activeNode.data.tools.includes(tool.name) }]"
                    @click="toggleTool(tool.name)"
                  >
                    <div class="tool-icon">{{ tool.icon }}</div>
                    <div class="tool-name">{{ tool.label }}</div>
                  </div>
                </div>
              </el-form-item>
            </el-form>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { el } from 'element-plus/es/locale/index.mjs'

const route = useRoute()
const taskId = route.params.taskId || 'default_task'

const { addEdges, screenToFlowCoordinate } = useVueFlow()
const nodes = ref([])
const edges = ref([])
let idCounter = 0
const getId = () => `agent_${idCounter++}`

const panelVisible = ref(false)
const activeNode = ref(null)
const availableTools = ref([]) // 改为空数组，等待后端加载
const API_BASE_URL = 'http://localhost:8001'

onMounted(async () => {
  // 1. 从后端获取真实 Tools
  try {
    const res = await fetch(`${API_BASE_URL}/api/tools`)
    if (res.ok) {
      const data = await res.json()
      // 将后端的数据映射为前端格式 (icon随机给个默认的)
      availableTools.value = data.tools.map(t => ({
        name: t.name,
        label: t.name, // 如果后端没有label，直接用name
        desc: t.description,
        icon: '🔧' 
      }))
    }
  } catch (e) {
    ElMessage.error('无法获取后端工具列表')
  }

  // 2. 从本地读取当前任务以前保存的图纸
  const savedData = localStorage.getItem(`workflow_${taskId}`)
  if (savedData) {
    const parsed = JSON.parse(savedData)
    nodes.value = parsed.nodes || []
    edges.value = parsed.edges || []
    // 恢复 ID 计数器
    idCounter = nodes.value.length
  } else {
    // 没保存过就给个初始节点
    nodes.value = [{
      id: 'node_0', type: 'default', position: { x: 300, y: 150 },
      label: '🟢 核心思考节点',
      data: { prompt: '你是一个强大的 AI 助手。', tools: [] },
      style: { 
        borderRadius: '12px', padding: '10px 20px', border: '1px solid var(--el-border-color)',
        backgroundColor: 'var(--el-bg-color-overlay)', color: 'var(--el-text-color-primary)',
        boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
      }
    }]
  }
})

// // 保存逻辑：将画布存入 localStorage
// const saveWorkflow = () => {
//   const workflowData = {
//     nodes: nodes.value,
//     edges: edges.value
//   }
//   localStorage.setItem(`workflow_${taskId}`, JSON.stringify(workflowData))
//   ElMessage.success('编排已保存在本地，可以进入对话测试了！')
// }

// === 下面是原有的交互逻辑保持不变 ===
const onNodeClick = (event) => {
  activeNode.value = event.node
  panelVisible.value = true
}

const closePanel = () => {
  panelVisible.value = false
  setTimeout(() => { activeNode.value = null }, 300)
}

const duplicateNode = () => {
  if (!activeNode.value) return
  const original = activeNode.value
  const newNode = {
    id: getId(), type: original.type,
    position: { x: original.position.x + 30, y: original.position.y + 30 },
    label: original.label + ' (副本)',
    data: { prompt: original.data.prompt, tools: [...original.data.tools] },
    style: { ...original.style }
  }
  nodes.value.push(newNode)
  activeNode.value = newNode
}

// === 删除节点逻辑 ===
const deleteNode = () => {
  if (!activeNode.value) return
  const nodeId = activeNode.value.id
  
  // 1. 从画布中移除该节点
  nodes.value = nodes.value.filter(n => n.id !== nodeId)
  // 2. 同时移除与该节点相关的所有连线
  edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)
  
  // 关闭面板并提示
  closePanel()
  ElMessage.success('节点及关联连线已删除')
}

const toggleTool = (toolName) => {
  const tools = activeNode.value.data.tools
  const index = tools.indexOf(toolName)
  if (index > -1) tools.splice(index, 1)
  else tools.push(toolName)
}

const onDragStart = (event, nodeType) => {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/vueflow', nodeType)
    event.dataTransfer.effectAllowed = 'move'
  }
}

const onDrop = (event) => {
  const type = event.dataTransfer?.getData('application/vueflow')
  if (!type) return
  const position = screenToFlowCoordinate({ x: event.clientX, y: event.clientY })
  const newNode = {
    id: getId(), type: 'default', position, label: `🤖 新建 Agent`,
    data: { prompt: '', tools: [] },
    style: { 
      borderRadius: '12px', padding: '10px 20px', border: '2px solid transparent',
      backgroundColor: 'var(--el-bg-color-overlay)', color: 'var(--el-text-color-primary)',
      boxShadow: '0 4px 12px rgba(0,0,0,0.05)', transition: 'border-color 0.2s'
    }
  }
  nodes.value.push(newNode)
}

const onConnect = (connection) => { addEdges(connection) }

// 保存逻辑：将画布存入 localStorage 并发送给后端持久化
const saveWorkflow = async () => {
  const workflowData = {
    nodes: nodes.value,
    edges: edges.value
  }
  
  // 1. 先存本地，保证前端刷新不丢
  localStorage.setItem(`workflow_${taskId}`, JSON.stringify(workflowData))
  
  // 2. 发送给后端创建真实目录和文件
  try {
    const res = await fetch(`${API_BASE_URL}/api/save_workflow`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        thread_id: taskId,
        nodes: nodes.value,
        edges: edges.value
      })
    })
    
    if (res.ok) {
      ElMessage.success('编排已成功保存到后端工作区！')
    } else {
      throw new Error('后端返回错误')
    }
  } catch (e) {
    console.error(e)
    ElMessage.warning('本地已保存，但同步到后端失败，请检查网络。')
  }
}
</script>

<style scoped>
.editor-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background-color: var(--el-bg-color-page);
}

/* 顶部状态栏 */
.editor-header {
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

.workflow-title {
  font-weight: 600;
  font-size: 1rem;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 画布主区域 */
.canvas-container {
  flex-grow: 1;
  position: relative;
  overflow: hidden;
}

.canvas-area {
  width: 100%;
  height: 100%;
}

/* --- 悬浮式左侧栏 --- */
.floating-sidebar {
  position: absolute;
  top: 24px;
  left: 24px;
  width: 240px;
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-light);
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  z-index: 5;
  overflow: hidden;
  /* 毛玻璃效果 */
  backdrop-filter: blur(10px);
  background-color: rgba(var(--el-bg-color-overlay-rgb), 0.8);
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.sidebar-header h3 {
  margin: 0;
  font-size: 0.9rem;
  color: var(--el-text-color-regular);
}

.components-list {
  padding: 12px;
}

.component-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 10px;
  cursor: grab;
  transition: transform 0.2s, background 0.2s;
}
.component-item:hover {
  transform: translateY(-2px);
  background: var(--el-fill-color);
}
.component-item:active {
  cursor: grabbing;
}

.comp-icon {
  font-size: 24px;
  margin-right: 12px;
  background: #fff;
  border-radius: 8px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}

/* 暗黑模式下图标背景适配 */
html.dark .comp-icon {
  background: var(--el-bg-color);
}

.comp-info {
  display: flex;
  flex-direction: column;
}
.comp-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.comp-desc {
  font-size: 0.75rem;
  color: var(--el-text-color-secondary);
}

/* --- 悬浮式右侧属性面板 --- */
.floating-panel {
  position: absolute;
  top: 24px;
  right: 24px;
  bottom: 24px;
  width: 320px;
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-light);
  border-radius: 16px;
  box-shadow: -4px 8px 24px rgba(0, 0, 0, 0.08);
  z-index: 5;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.panel-header h3 {
  margin: 0;
  font-size: 1rem;
}

.panel-body {
  padding: 20px;
  overflow-y: auto;
  flex-grow: 1;
}

/* 现代化的工具选择网格 */
.tools-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.tool-card {
  border: 1px solid var(--el-border-color);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--el-fill-color-blank);
}

.tool-card:hover {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}

.tool-card.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}
html.dark .tool-card.active {
  background: var(--el-color-primary-dark-2);
}

.tool-icon {
  font-size: 20px;
  margin-bottom: 6px;
}
.tool-name {
  font-size: 0.8rem;
  font-weight: 500;
}

/* 右侧面板滑出动画 */
.slide-panel-enter-active,
.slide-panel-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.slide-panel-enter-from,
.slide-panel-leave-to {
  transform: translateX(120%);
  opacity: 0;
}
</style>

/* 覆盖 Vue Flow 默认控件在暗黑模式下的样式 */
<style>
html.dark .vue-flow__controls {
  background-color: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color);
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
html.dark .vue-flow__controls-button {
  background-color: var(--el-bg-color-overlay);
  color: var(--el-text-color-primary);
  border-bottom-color: var(--el-border-color);
}
html.dark .vue-flow__controls-button:hover {
  background-color: var(--el-fill-color-light);
}
</style>
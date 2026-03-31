<template>
  <div class="editor-container">
    <!-- 左侧侧边栏：组件库 -->
    <div class="sidebar">
      <h3>组件库</h3>
      <p class="desc">拖拽下方节点到画布</p>
      
      <div 
        class="draggable-item agent-node" 
        draggable="true" 
        @dragstart="onDragStart($event, 'agent')"
      >
        🤖 Agent 节点
      </div>
      
      <div class="sidebar-actions">
        <el-button type="primary" style="width: 100%" @click="saveWorkflow">保存当前流程</el-button>
        <el-button style="width: 100%; margin-top: 10px;" @click="$router.push('/')">返回列表</el-button>
      </div>
    </div>

    <!-- 右侧：Vue Flow 画布区域 -->
    <div class="canvas-area" @drop="onDrop" @dragover.prevent>
      <VueFlow 
        v-model:nodes="nodes" 
        v-model:edges="edges" 
        class="vue-flow-basic-example"
        @connect="onConnect"
        @nodeClick="onNodeClick"
      >
        <Background pattern-color="#aaa" :gap="20" />
        <Controls />
      </VueFlow>
    </div>

    <!-- 右侧弹出的属性配置抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="`配置节点: ${selectedNode?.label}`"
      size="400px"
      direction="rtl"
    >
      <div v-if="selectedNode" class="node-config-form">
        
        <div class="form-item">
          <h4>Agent 名称</h4>
          <el-input v-model="selectedNode.label" placeholder="给这个 Agent 起个名字" />
        </div>

        <div class="form-item">
          <h4>系统提示词 (System Prompt)</h4>
          <el-input 
            v-model="selectedNode.data.prompt" 
            type="textarea" 
            :rows="6" 
            placeholder="例如：你是一个专业的数据分析师，请根据提供的数据回答问题..." 
          />
        </div>

        <div class="form-item">
          <h4>可用工具 (Tools)</h4>
          <p class="desc">勾选该 Agent 可调用的工具</p>
          <el-checkbox-group v-model="selectedNode.data.tools">
            <el-checkbox 
              v-for="tool in availableTools" 
              :key="tool.id" 
              :value="tool.id"
              class="tool-checkbox"
            >
              {{ tool.name }} <span class="tool-desc">({{ tool.desc }})</span>
            </el-checkbox>
          </el-checkbox-group>
        </div>

      </div>
    </el-drawer>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'

const { addEdges, screenToFlowCoordinate } = useVueFlow()

const nodes = ref([
  {
    id: 'node_1',
    type: 'default',
    position: { x: 250, y: 100 },
    label: '🟢 开始节点',
    data: { prompt: '我是系统的入口节点。', tools: [] }
  }
])

const edges = ref([])

// === 抽屉与节点配置逻辑 ===
const drawerVisible = ref(false) // 控制抽屉是否显示
const selectedNode = ref(null)   // 当前正在被编辑的节点对象

// 模拟从后端加载的所有可用工具
const availableTools = ref([])

onMounted(() => {
  // 【教学点】：以后你需要写 fetch('/api/tools') 从后端获取真实的 tools 列表
  availableTools.value = [
    { id: 'web_search', name: '网络搜索', desc: '允许 Agent 联网搜索最新信息' },
    { id: 'calculator', name: '计算器', desc: '执行精确的数学计算' },
    { id: 'read_file', name: '读取文件', desc: '读取用户指定的本地或云端文件' },
    { id: 'execute_code', name: '代码执行', desc: '在沙盒中运行 Python 代码' }
  ]
})

// 当画布上的节点被点击时触发
const onNodeClick = (event) => {
  // event.node 就是被点击的那个节点对象
  selectedNode.value = event.node
  drawerVisible.value = true // 弹出右侧抽屉
}

// === 拖拽核心逻辑 ===
let idCounter = 0
const getId = () => `agent_node_${idCounter++}`

const onDragStart = (event, nodeType) => {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/vueflow', nodeType)
    event.dataTransfer.effectAllowed = 'move'
  }
}

const onDrop = (event) => {
  const type = event.dataTransfer?.getData('application/vueflow')
  if (!type) return

  const position = screenToFlowCoordinate({
    x: event.clientX,
    y: event.clientY,
  })

  const newNode = {
    id: getId(),
    type: 'default',
    position,
    label: `🤖 Agent ${idCounter}`,
    // 确保每个新节点都有独立的 data 对象来存放配置
    data: { 
      prompt: '',
      tools: []
    }
  }
  nodes.value.push(newNode)
}

const onConnect = (connection) => {
  addEdges(connection)
}

const saveWorkflow = () => {
  console.log('--- 准备发给后端的保存数据 ---')
  console.log('Nodes:', JSON.parse(JSON.stringify(nodes.value)))
  console.log('Edges:', JSON.parse(JSON.stringify(edges.value)))
  alert('数据已打印到控制台，这些就是用来生成 Agent 工作流的核心配置！')
}
</script>

<style scoped>
/* 之前的样式保持不变 */
.editor-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  background-color: #fff;
}

.sidebar {
  width: 250px;
  background-color: #f8f9fa;
  border-right: 1px solid #e4e7ed;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.desc {
  font-size: 12px;
  color: #909399;
  margin-bottom: 20px;
}

.draggable-item {
  padding: 15px;
  border: 1px dashed #409EFF;
  border-radius: 4px;
  background-color: #ecf5ff;
  color: #409EFF;
  text-align: center;
  cursor: grab;
  margin-bottom: 15px;
  user-select: none;
}
.draggable-item:active {
  cursor: grabbing;
}

.sidebar-actions {
  margin-top: auto;
}

.canvas-area {
  flex-grow: 1;
  height: 100%;
}

/* 新增的抽屉内表单样式 */
.node-config-form .form-item {
  margin-bottom: 25px;
}
.node-config-form h4 {
  margin: 0 0 10px 0;
  font-size: 15px;
  color: #303133;
}
.tool-checkbox {
  display: flex;
  margin-bottom: 10px;
  white-space: normal;
  height: auto;
}
.tool-desc {
  font-size: 12px;
  color: #909399;
  margin-left: 5px;
}
</style>
import { createRouter, createWebHistory } from 'vue-router'
import TaskList from './views/TaskList.vue'
import WorkflowEditor from './views/WorkflowEditor.vue'
import ChatView from './views/ChatView.vue'

const routes = [
  { path: '/', component: TaskList }, // 默认首页是任务列表
  { path: '/editor/:taskId?', component: WorkflowEditor }, // 编辑器，带可选的任务ID
  { path: '/chat/:taskId', component: ChatView } // 聊天界面，必须知道在跟哪个任务聊
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
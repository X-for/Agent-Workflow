// frontend/js/view_tasks.js

// 独立功能：从后端获取任务列表并渲染
export async function loadTasks() {
    const listElement = document.getElementById('task-list');
    
    try {
        const response = await fetch('http://localhost:8001/api/tasks');
        const data = await response.json();
        
        listElement.innerHTML = ''; // 清空加载提示
        
        if (data.tasks.length === 0) {
            listElement.innerHTML = '<li>暂无历史任务，请创建新任务。</li>';
            return;
        }

        // 遍历渲染已有任务
        data.tasks.forEach(taskId => {
            const li = document.createElement('li');
            li.style.margin = "10px 0";
            
            const btn = document.createElement('button');
            btn.innerText = `进入任务: ${taskId}`;
            btn.onclick = () => selectTask(taskId);
            
            li.appendChild(btn);
            listElement.appendChild(li);
        });
    } catch (error) {
        listElement.innerHTML = '<li style="color:red;">后端连接失败，请确保 main.py 已启动。</li>';
        console.error("加载任务失败:", error);
    }
}

// 独立功能：选择或创建任务后，记录全局 ID 并跳转界面
function selectTask(taskId) {
    // 将当前任务 ID 挂载到全局 window 对象上，方便其他界面读取
    window.currentTaskId = taskId;
    alert(`已选中任务: ${taskId}，即将进入节点编排。`);
    
    // 激活导航栏按钮并跳转到界面2 (此处假设你已经在 main.js 写了 switchView 函数)
    document.getElementById('nav-editor').disabled = false;
    document.getElementById('nav-chat').disabled = false;
    // 调用全局的视图切换函数
    window.switchView('editor'); 
}

// 独立功能：绑定“创建新任务”按钮事件
export function initTaskView() {
    document.getElementById('btn-create-task').onclick = () => {
        // 使用时间戳生成一个唯一的 thread_id
        const newTaskId = 'task_' + Date.now();
        selectTask(newTaskId);
    };
    
    // 初始加载一次任务列表
    loadTasks();
}
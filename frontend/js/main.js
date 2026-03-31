import { initTaskView } from './view_tasks.js';
import { initEditorView } from './view_editor.js';
import { initChatView } from './view_chat.js';

// 将 switchView 挂载到全局供 HTML 调用
window.switchView = function (viewName) {
    document.querySelectorAll('.view-container').forEach(el => el.style.display = 'none');
    document.getElementById('view-' + viewName).style.display = 'block';
};

// 初始化界面1
initTaskView();
initEditorView();
initChatView();
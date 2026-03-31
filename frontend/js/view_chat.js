// frontend/js/view_chat.js

export function initChatView() {
    document.getElementById('btn-send').onclick = sendMessage;
}

async function sendMessage() {
    const inputEl = document.getElementById('chat-input');
    const userInput = inputEl.value.trim();
    if (!userInput) return;

    // 1. 校验前置数据是否存在 (必须先选任务、画图纸)
    if (!window.currentTaskId || !window.workflowGraph) {
        alert("缺少任务 ID 或工作流图纸，请先返回配置！");
        return;
    }

    // 2. 渲染用户的气泡并清空输入框
    appendMessage('user', userInput);
    inputEl.value = '';

    // 3. 准备 AI 气泡用于后续的流式追加
    const aiBubble = appendMessage('ai', '思考中...');
    
    try {
        // 4. 发送 POST 请求
        const response = await fetch('http://localhost:8001/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                thread_id: window.currentTaskId,
                user_input: userInput,
                nodes: window.workflowGraph.nodes,
                edges: window.workflowGraph.edges
            })
        });

        // 5. 核心：处理 SSE 流式返回
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        aiBubble.innerText = ''; // 清空"思考中..."

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunkStr = decoder.decode(value);
            // SSE 的格式是 "data: 实际内容\n\n"，需要进行解析拆分
            const lines = chunkStr.split('\n\n');
            for (let line of lines) {
                if (line.startsWith('data: ')) {
                    const text = line.replace('data: ', '');
                    // 将提取出的字追加到当前气泡中
                    aiBubble.innerText += text;
                }
            }
            // 滚动条自动滚动到底部
            document.getElementById('chat-history').scrollTop = document.getElementById('chat-history').scrollHeight;
        }

    } catch (error) {
        aiBubble.innerText = '请求失败，请检查后端运行状态。';
        console.error("对话报错:", error);
    }
}

// 独立功能：在界面上渲染聊天气泡
function appendMessage(role, text) {
    const historyDiv = document.getElementById('chat-history');
    const msgDiv = document.createElement('div');
    
    msgDiv.style.marginBottom = '15px';
    msgDiv.style.padding = '10px 15px';
    msgDiv.style.borderRadius = '8px';
    msgDiv.style.maxWidth = '80%';
    msgDiv.style.whiteSpace = 'pre-wrap'; // 保留换行符
    
    if (role === 'user') {
        msgDiv.style.background = '#e3f2fd';
        msgDiv.style.alignSelf = 'flex-end';
        msgDiv.style.marginLeft = 'auto';
    } else {
        msgDiv.style.background = 'white';
        msgDiv.style.border = '1px solid #ddd';
        msgDiv.style.alignSelf = 'flex-start';
        msgDiv.style.marginRight = 'auto';
    }
    
    msgDiv.innerText = text;
    historyDiv.appendChild(msgDiv);
    historyDiv.scrollTop = historyDiv.scrollHeight;
    
    return msgDiv; // 返回 DOM 节点，方便后续动态追加文字
}
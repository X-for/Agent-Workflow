// frontend/js/view_editor.js

let editor = null;
let availableTools = [];

// 独立功能：初始化画布与加载工具
export async function initEditorView() {
    // 1. 初始化 Drawflow 画布 (允许1个输入锚点，1个输出锚点)
    const container = document.getElementById('drawflow');
    editor = new Drawflow(container);
    editor.reroute = true;
    editor.start();

    // 2. 从后端拉取所有工具
    try {
        const response = await fetch('http://localhost:8001/api/tools');
        const data = await response.json();
        availableTools = data.tools;
        
        // 在左侧面板渲染工具说明
        const toolsDiv = document.getElementById('tools-container');
        toolsDiv.innerHTML = availableTools.map(t => `<div><b>${t.name}</b>: ${t.description}</div>`).join('');
    } catch (e) {
        console.error("加载工具失败:", e);
    }

    // 3. 绑定左侧按钮事件
    document.getElementById('btn-add-agent').onclick = addAgentNode;
    document.getElementById('btn-save-graph').onclick = saveAndProceed;
}

// 独立功能：在画布上添加一个 Agent 节点
function addAgentNode() {
    // 动态生成节点内部的 HTML (包含输入框和工具多选框)
    let toolsHtml = availableTools.map(t => 
        `<label><input type="checkbox" class="node-tool" value="${t.name}"> ${t.name}</label><br>`
    ).join('');

    const nodeHtml = `
        <div style="padding: 10px; background: white; border-radius: 4px;">
            <input type="text" class="node-name" placeholder="Agent 角色名 (如: 规划师)" style="width: 100%; margin-bottom: 5px;">
            <textarea class="node-desc" placeholder="职责描述" style="width: 100%; height: 60px;"></textarea>
            <div style="font-size: 12px; margin-top: 5px;">
                <strong>挂载工具:</strong><br>
                ${toolsHtml}
            </div>
        </div>
    `;

    // 在画布中央添加节点 (1个输入, 1个输出)
    editor.addNode('agent', 1, 1, 150, 150, 'agent-node', {}, nodeHtml);
}

// 独立功能：解析画布图形，翻译成后端需要的格式并跳转
function saveAndProceed() {
    const exported = editor.export().drawflow.Home.data;
    const nodes = [];
    const edges = [];

    // 遍历 Drawflow 生成的数据
    for (const key in exported) {
        const nodeData = exported[key];
        // 关键：通过 DOM 获取用户在输入框里填写的真实内容
        const domElement = document.getElementById(`node-${nodeData.id}`);
        const name = domElement.querySelector('.node-name').value || `未命名_${nodeData.id}`;
        const desc = domElement.querySelector('.node-desc').value || "";
        
        // 收集被勾选的工具
        const selectedTools = Array.from(domElement.querySelectorAll('.node-tool:checked')).map(cb => cb.value);

        nodes.push({
            id: `node_${nodeData.id}`, // 加上前缀作为唯一 ID
            name: name,
            description: desc,
            tools: selectedTools
        });

        // 解析连线 (提取 output 锚点的连接信息)
        const outputs = nodeData.outputs;
        for (const outKey in outputs) {
            outputs[outKey].connections.forEach(conn => {
                edges.push({
                    from: `node_${nodeData.id}`,
                    to: `node_${conn.node}`
                });
            });
        }
    }

    // 将解析好的图纸保存到全局变量，供 Chat 界面读取
    window.workflowGraph = { nodes, edges };
    console.log("生成的图纸:", window.workflowGraph);
    
    // 跳转到聊天界面
    window.switchView('chat');
}
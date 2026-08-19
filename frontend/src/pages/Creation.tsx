import { useState, useCallback, useRef, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Save, RefreshCcw, Plus, Trash2 } from 'lucide-react'
import axios from 'axios'
import { useTheme } from '../App'
import {
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  type Connection,
  type Edge,
  type Node as FlowNode
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import Sidebar from '../components/Sidebar'
import AgentNode from '../components/AgentNode'
import StartEndNode from '../components/StartEndNode'

const nodeTypes = {
  AGENT: AgentNode,
  CUSTOM_AGENT: AgentNode,
  START: StartEndNode,
  END: StartEndNode
}

let id = 0
const getId = () => `node_${id++}`

function validateWorkflow(nodes: FlowNode[], edges: Edge[]): string | null {
  const nodeIds = new Set(nodes.map(node => node.id))
  if (nodeIds.size !== nodes.length) return '存在重复的节点 ID，请删除重复节点后重试。'

  const startNodes = nodes.filter(node => node.type === 'START')
  const endNodes = nodes.filter(node => node.type === 'END')
  if (startNodes.length !== 1 || endNodes.length !== 1) {
    return `工作流必须且只能包含一个 START 和一个 END（当前 ${startNodes.length}/${endNodes.length}）。`
  }

  const adjacency = new Map<string, Set<string>>()
  const indegree = new Map<string, number>()
  nodes.forEach(node => {
    adjacency.set(node.id, new Set())
    indegree.set(node.id, 0)
  })
  const edgeKeys = new Set<string>()

  for (const edge of edges) {
    const sourceNode = nodes.find(node => node.id === edge.source)
    const targetNode = nodes.find(node => node.id === edge.target)
    if (targetNode?.type === 'START') return 'START 节点不能有入边。'
    if (sourceNode?.type === 'END') return 'END 节点不能有出边。'
    if (!sourceNode || !targetNode) return `连线 ${edge.id} 引用了不存在的节点。`
    if (!edge.sourceHandle || !edge.targetHandle) return `连线 ${edge.id} 缺少源端口或目标端口。`

    const outputPorts = (sourceNode.data.output_ports || []) as Array<{ id: string }>
    const inputPorts = (targetNode.data.input_ports || []) as Array<{ id: string }>
    if (!outputPorts.some(port => port.id === edge.sourceHandle)) {
      return `节点 ${edge.source} 不存在输出端口 ${edge.sourceHandle}。`
    }
    if (!inputPorts.some(port => port.id === edge.targetHandle)) {
      return `节点 ${edge.target} 不存在输入端口 ${edge.targetHandle}。`
    }

    const edgeKey = `${edge.source}:${edge.sourceHandle}->${edge.target}:${edge.targetHandle}`
    if (edgeKeys.has(edgeKey)) return `存在重复连线：${edgeKey}`
    edgeKeys.add(edgeKey)

    const targets = adjacency.get(edge.source)!
    if (!targets.has(edge.target)) {
      targets.add(edge.target)
      indegree.set(edge.target, (indegree.get(edge.target) || 0) + 1)
    }
  }

  const queue = nodes.filter(node => indegree.get(node.id) === 0).map(node => node.id)
  let visited = 0
  while (queue.length > 0) {
    const nodeId = queue.shift()!
    visited += 1
    adjacency.get(nodeId)!.forEach(target => {
      const nextDegree = (indegree.get(target) || 0) - 1
      indegree.set(target, nextDegree)
      if (nextDegree === 0) queue.push(target)
    })
  }
  if (visited !== nodes.length) return '工作流包含环路，当前执行器只支持有向无环图（DAG）。'

  const reachable = new Set<string>()
  const stack = [startNodes[0].id]
  while (stack.length > 0) {
    const nodeId = stack.pop()!
    if (reachable.has(nodeId)) continue
    reachable.add(nodeId)
    adjacency.get(nodeId)!.forEach(target => stack.push(target))
  }
  if (!reachable.has(endNodes[0].id)) return 'END 节点无法从 START 节点到达。'
  const unreachable = nodes.filter(node => !reachable.has(node.id))
  if (unreachable.length > 0) return `存在无法从 START 到达的节点：${unreachable.map(node => node.id).join(', ')}`
  return null
}

export default function Creation() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const { isDarkMode } = useTheme()
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null)
  
  const [filename, setFilename] = useState('new_workflow.json')
  const [availableNodes, setAvailableNodes] = useState<any[]>([])
  const [selectedNode, setSelectedNode] = useState<any>(null)
  const [availableTools, setAvailableTools] = useState<string[]>([])

  // 处理编辑模式：加载已有工作流
  useEffect(() => {
    const queryParams = new URLSearchParams(location.search)
    const editId = queryParams.get('edit')
    
    if (editId) {
      console.log('DEBUG: Fetching workflow for edit:', editId)
      setFilename(editId)
      Promise.all([
        axios.get(`/api/workflows/${encodeURIComponent(editId)}`),
        axios.get('/api/nodes')
      ])
        .then(([res, nodesRes]) => {
          console.log('DEBUG: Workflow data received:', res.data)
          if (res.data.status === 'success') {
            const wf = res.data.workflow
            const nodeTemplates = (nodesRes.data.nodes || []) as Array<{
              ref?: string
              name?: string
              input_ports?: Array<Record<string, unknown>>
              output_ports?: Array<Record<string, unknown>>
            }>
            
            // 1. 转换节点
            const flowNodes: FlowNode[] = wf.nodes.map((n: any, index: number) => {
              const template = n.ref
                ? nodeTemplates.find(candidate => candidate.ref === n.ref)
                : undefined
              // 修复类型匹配逻辑：
              // 1. 如果有明确的 type (START/END)，直接使用
              // 2. 如果没有 type 但有 ref，说明是通用节点 (AGENT)
              // 3. 如果既没有 type 也没有 ref，或者 type 是 AGENT 且没有 ref，说明是专用节点 (CUSTOM_AGENT)
              let type = n.type
              if (!type) {
                type = n.ref ? 'AGENT' : 'CUSTOM_AGENT'
              } else if (type === 'AGENT') {
                type = n.ref ? 'AGENT' : 'CUSTOM_AGENT'
              }
              
              return {
                id: n.id,
                type: type,
                position: n.position || { x: 100 + index * 250, y: 200 },
                data: {
                  ...template,
                  ...n,
                  // 确保 label 存在，否则节点可能显示为空白
                  label: n.name || template?.name || n.id,
                  input_ports: n.input_ports || template?.input_ports || [],
                  output_ports: n.output_ports || template?.output_ports || []
                }
              }
            })
            
            // 2. 转换连线
            const flowEdges: Edge[] = wf.connections.map((c: any, index: number) => ({
              id: `edge_${index}`,
              source: c.source_node,
              sourceHandle: c.source_port,
              target: c.target_node,
              targetHandle: c.target_port,
              type: 'default'
            }))
            
            setNodes(flowNodes)
            setEdges(flowEdges)

            // 3. 更新全局 ID 计数器，防止新添加节点 ID 冲突
            const maxId = wf.nodes.reduce((max: number, n: any) => {
              const match = n.id.match(/node_(\d+)/)
              return match ? Math.max(max, parseInt(match[1])) : max
            }, -1)
            id = maxId + 1
          }
        })
        .catch(err => console.error('加载工作流失败', err))
    }
  }, [location.search, setNodes, setEdges])

  useEffect(() => {
    // 获取可用的节点模板
    axios.get('/api/nodes')
      .then(res => {
        setAvailableNodes(res.data.nodes || [])
      })
      .catch(err => {
        console.error('获取可用节点失败', err)
      })
    axios.get('/api/tools').then(res => setAvailableTools(res.data.tools || []))
  }, [])

  const onConnect = useCallback(
    (params: Connection | Edge) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const onNodeClick = (_: any, node: any) => {
    setSelectedNode(node)
  }

  const addPort = (nodeId: string, type: 'input' | 'output') => {
    const field = type === 'input' ? 'input_ports' : 'output_ports'
    const newPort = type === 'input'
      ? { id: `in_${Date.now()}`, name: '新输入' }
      : { id: `out_${Date.now()}`, description: '新输出' }
    const update = (node: any) => ({
      ...node,
      data: { ...node.data, [field]: [...(node.data[field] || []), newPort] }
    })
    setNodes(nds => nds.map(node => node.id === nodeId ? update(node) : node))
    setSelectedNode((current: any) => current?.id === nodeId ? update(current) : current)
  }

  const removePort = (nodeId: string, type: 'input' | 'output', portId: string) => {
    const field = type === 'input' ? 'input_ports' : 'output_ports'
    const update = (node: any) => ({
      ...node,
      data: { ...node.data, [field]: (node.data[field] || []).filter((port: any) => port.id !== portId) }
    })
    setNodes(nds => nds.map(node => node.id === nodeId ? update(node) : node))
    setEdges(eds => eds.filter(edge => (
      type === 'input'
        ? !(edge.target === nodeId && edge.targetHandle === portId)
        : !(edge.source === nodeId && edge.sourceHandle === portId)
    )))
    setSelectedNode((current: any) => current?.id === nodeId ? update(current) : current)
  }

  const updateNodeData = (nodeId: string, newData: any) => {
    setNodes(nds => nds.map(node => {
      if (node.id === nodeId) {
        // 如果是通用节点 (AGENT) 且正在修改关键配置，则将其转换为专用节点 (CUSTOM_AGENT)
        // 关键配置包括：model_name, base_url, system_prompt, tools
        const isAgent = node.type === 'AGENT'
        const isModifyingConfig = newData.model_name !== undefined || 
                                 newData.base_url !== undefined || 
                                 newData.system_prompt !== undefined || 
                                 newData.tools !== undefined
        
        let updatedType = node.type
        const updatedData = { ...node.data, ...newData }

        if (isAgent && isModifyingConfig) {
          console.log(`Node ${nodeId} modified, converting from AGENT to CUSTOM_AGENT to protect template.`)
          updatedType = 'CUSTOM_AGENT'
          // 移除 ref 引用，使其成为独立配置
          delete updatedData.ref
        }

        const updatedNode = {
          ...node,
          type: updatedType,
          data: updatedData
        }
        if (selectedNode?.id === nodeId) setSelectedNode(updatedNode)
        return updatedNode
      }
      return node
    }))
  }

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()

      const typeStr = event.dataTransfer.getData('application/reactflow')
      if (!typeStr || !reactFlowInstance) return

      const nodeTemplate = JSON.parse(typeStr)
      if ((nodeTemplate.type === 'START' || nodeTemplate.type === 'END') && nodes.some(node => node.type === nodeTemplate.type)) {
        alert(`工作流只能包含一个 ${nodeTemplate.type} 节点。`)
        return
      }
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      })

      // 构建 React Flow 节点数据
      const newNode: FlowNode = {
        id: nodeTemplate.type === 'START' ? 'start_node' : 
            nodeTemplate.type === 'END' ? 'end_node' : 
            `${nodeTemplate.id}_${getId()}`,
        type: nodeTemplate.type,
        position,
        data: {
          ...nodeTemplate,
          // 如果是 Agent，记录它的配置文件 ref
          ref: nodeTemplate.type === 'AGENT' ? nodeTemplate.ref : undefined,
          // 无论通用还是专用，都初始化端口，允许在画布上覆盖
          input_ports: nodeTemplate.input_ports || [],
          output_ports: nodeTemplate.output_ports || [],
          // 为自定义节点初始化默认配置
          ...(nodeTemplate.type === 'CUSTOM_AGENT' ? {
            name: '新专用节点',
            model_name: 'deepseek-chat',
            base_url: 'https://api.deepseek.com',
            system_prompt: '你是一个专用助手...',
            tools: [],
            input_ports: [{ id: 'in', name: '输入' }],
            output_ports: [{ id: 'out', description: '输出' }]
          } : {})
        },
      }

      setNodes((nds) => nds.concat(newNode))
    },
    [reactFlowInstance, setNodes, nodes]
  )

  const saveWorkflow = async () => {
    const validationError = validateWorkflow(nodes, edges)
    if (validationError) {
      alert(`保存失败：${validationError}`)
      return
    }

    // 转换 React Flow 的 nodes 为后端 Workflow 需要的结构
    const workflowNodes = nodes.map(n => {
      const baseNode: any = {
        id: n.id,
        type: n.type === 'CUSTOM_AGENT' ? 'AGENT' : n.type, // 后端统一识别为 AGENT
        position: n.position // 保存位置信息，以便下次编辑时还原
      }
      
      if (n.type === 'AGENT') {
        baseNode.ref = n.data.ref
        // 覆盖通用节点的端口配置
        baseNode.input_ports = n.data.input_ports
        baseNode.output_ports = n.data.output_ports
      } else if (n.type === 'CUSTOM_AGENT') {
          // 自定义节点直接把配置塞进 node 结构中，不使用 ref
          baseNode.name = n.data.name
          baseNode.model_name = n.data.model_name
          baseNode.base_url = n.data.base_url
          baseNode.system_prompt = n.data.system_prompt
          baseNode.tools = n.data.tools
          baseNode.input_ports = n.data.input_ports
          baseNode.output_ports = n.data.output_ports
      } else if (n.type === 'START') {
        baseNode.output_ports = Array.isArray(n.data.output_ports) && n.data.output_ports.length > 0
          ? n.data.output_ports
          : [{ id: "out_query" }]
      } else if (n.type === 'END') {
        baseNode.input_ports = Array.isArray(n.data.input_ports) && n.data.input_ports.length > 0
          ? n.data.input_ports
          : [{ id: "in_result" }]
      }
      
      return baseNode
    })

    // 转换 React Flow 的 edges 为后端 Workflow 需要的连接结构
    const connections = edges.map(e => ({
      source_node: e.source,
      source_port: e.sourceHandle || '',
      target_node: e.target,
      target_port: e.targetHandle || ''
    }))

    try {
      await axios.post('/api/workflows', {
        filename,
        workflow_id: filename.replace('.json', ''),
        nodes: workflowNodes,
        connections
      })
      alert('🎉 保存成功！工作流已生成。')
      navigate('/')
    } catch (err) {
      alert('保存失败，请检查控制台。')
      console.error(err)
    }
  }

  const clearCanvas = () => {
    if(confirm('确定要清空画布吗？')) {
      setNodes([])
      setEdges([])
      setSelectedNode(null)
      id = 0
    }
  }

  const deleteSelected = () => {
    const hasSelectedNodes = nodes.some(n => n.selected)
    const hasSelectedEdges = edges.some(e => e.selected)
    
    if (!hasSelectedNodes && !hasSelectedEdges) {
      alert('请先在画布中点击选中要删除的节点或连线！')
      return
    }

    setNodes(nds => nds.filter(n => !n.selected))
    setEdges(eds => eds.filter(e => !e.selected))
    setSelectedNode(null)
  }

  return (
    <div className={`flex-1 flex flex-col h-full transition-colors duration-300 ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className={`px-6 py-4 border-b flex justify-between items-center z-10 shadow-sm transition-colors duration-300 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
        <div>
          <h1 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>拖拽式工作流构建器</h1>
          <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>从右侧拖拽组件以创建多智能体协作流，支持选中后删除 (或按 Backspace 键)</p>
        </div>
        <div className="flex items-center gap-4">
          <input 
            value={filename}
            onChange={e => setFilename(e.target.value)}
            className={`w-64 border rounded-lg px-4 py-2 outline-none focus:ring-2 focus:ring-blue-500/50 font-mono text-sm transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-gray-50 border-gray-300 text-gray-900'}`}
            placeholder="workflow_name.json"
          />
          <button 
            onClick={deleteSelected}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${isDarkMode ? 'bg-red-900/40 hover:bg-red-900/60 text-red-400 border border-red-800/50' : 'bg-red-50 hover:bg-red-100 text-red-600 border border-red-200'}`}
            title="删除选中的节点或连线"
          >
            <Trash2 size={16} /> 删除选中
          </button>
          <button 
            onClick={clearCanvas}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${isDarkMode ? 'bg-gray-700 hover:bg-gray-600 text-gray-200' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}
          >
            <RefreshCcw size={16} /> 清空
          </button>

          <button 
            onClick={saveWorkflow}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors shadow-md hover:shadow-lg"
          >
            <Save size={18} />
            生成并保存 JSON
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <ReactFlowProvider>
          <div className="flex-1 relative" ref={reactFlowWrapper}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onInit={setReactFlowInstance}
              onDrop={onDrop}
              onDragOver={onDragOver}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              fitView
              colorMode={isDarkMode ? 'dark' : 'light'}
            >
              <Background color={isDarkMode ? '#333' : '#cbd5e1'} gap={16} />
              <Controls />
            </ReactFlow>

            {/* 右侧属性编辑面板 */}
            {selectedNode && (selectedNode.type === 'CUSTOM_AGENT' || selectedNode.type === 'AGENT') && (
              <div className={`absolute right-4 top-4 bottom-4 w-80 shadow-xl border rounded-2xl p-6 overflow-y-auto z-10 transition-colors duration-300 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
                <div className="flex justify-between items-center mb-6">
                  <h3 className={`font-bold text-lg ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                    {selectedNode.type === 'CUSTOM_AGENT' ? '专用节点配置' : '通用节点覆盖'}
                  </h3>
                  <button onClick={() => setSelectedNode(null)} className="text-gray-400 hover:text-gray-600">×</button>
                </div>
                
                <div className="space-y-6">
                  {(selectedNode.type === 'CUSTOM_AGENT' || selectedNode.type === 'AGENT') && (
                    <>
                      {selectedNode.type === 'CUSTOM_AGENT' && selectedNode.data.ref === undefined && (
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                          <p className="text-xs text-blue-700 leading-relaxed">
                            💡 <b>已转换为专用节点</b>：由于你修改了配置，该节点已脱离通用模板，其修改仅对当前工作流生效。
                          </p>
                        </div>
                      )}
                      <div>
                        <label className={`block text-xs font-bold uppercase mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                          {selectedNode.type === 'AGENT' ? '通用节点名称 (只读)' : '显示名称'}
                        </label>
                        <input 
                          value={selectedNode.data.name || ''} 
                          onChange={e => selectedNode.type === 'CUSTOM_AGENT' && updateNodeData(selectedNode.id, { name: e.target.value, label: e.target.value })}
                          readOnly={selectedNode.type === 'AGENT'}
                          className={`w-full border rounded-lg p-2 text-sm transition-colors ${
                            selectedNode.type === 'AGENT' ? 'bg-gray-100/50 cursor-not-allowed' : ''
                          } ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-200 text-gray-900'}`}
                        />
                      </div>

                      <div>
                        <label className={`block text-xs font-bold uppercase mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>模型</label>
                        <input 
                          value={selectedNode.data.model_name || ''} 
                          onChange={e => updateNodeData(selectedNode.id, { model_name: e.target.value })}
                          className={`w-full border rounded-lg p-2 text-sm transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-200 text-gray-900'}`}
                        />
                      </div>

                      <div>
                        <label className={`block text-xs font-bold uppercase mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>Base URL</label>
                        <input 
                          value={selectedNode.data.base_url || ''} 
                          onChange={e => updateNodeData(selectedNode.id, { base_url: e.target.value })}
                          className={`w-full border rounded-lg p-2 text-sm transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-200 text-gray-900'}`}
                          placeholder="https://api.openai.com/v1"
                        />
                      </div>

                      <div>
                        <label className={`block text-xs font-bold uppercase mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>System Prompt</label>
                        <textarea 
                          value={selectedNode.data.system_prompt || ''} 
                          onChange={e => updateNodeData(selectedNode.id, { system_prompt: e.target.value })}
                          rows={4}
                          className={`w-full border rounded-lg p-2 text-sm resize-none transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-200 text-gray-900'}`}
                        />
                      </div>

                      <div>
                        <label className={`block text-xs font-bold uppercase mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>工具</label>
                        <div className="flex flex-wrap gap-2">
                          {availableTools.map(tool => (
                            <button
                              key={tool}
                              onClick={() => {
                                const currentTools = selectedNode.data.tools || []
                                const nextTools = currentTools.includes(tool) 
                                  ? currentTools.filter((t: string) => t !== tool)
                                  : [...currentTools, tool]
                                updateNodeData(selectedNode.id, { tools: nextTools })
                              }}
                              className={`px-2 py-1 rounded text-xs border transition-colors ${
                                (selectedNode.data.tools || []).includes(tool)
                                  ? 'bg-blue-600 border-blue-600 text-white'
                                  : isDarkMode ? 'bg-gray-700 border-gray-600 text-gray-300 hover:bg-gray-600' : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'
                              }`}
                            >
                              {tool}
                            </button>
                          ))}
                        </div>
                      </div>
                    </>
                  )}

                  {/* 端口管理 - 通用和专用节点都支持 */}
                  <div className={`pt-4 border-t ${isDarkMode ? 'border-gray-700' : 'border-gray-100'}`}>
                    <div className="flex justify-between items-center mb-3">
                      <label className={`block text-xs font-bold uppercase ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>输入端口</label>
                      <button onClick={() => addPort(selectedNode.id, 'input')} className="text-blue-600 hover:text-blue-700">
                        <Plus size={14} />
                      </button>
                    </div>
                    <div className="space-y-2">
                      {(selectedNode.data.input_ports || []).map((port: any, idx: number) => (
                        <div key={idx} className="flex gap-1 items-center">
                          <input 
                            value={port.id} 
                            onChange={e => {
                              const newPorts = [...selectedNode.data.input_ports]
                              newPorts[idx].id = e.target.value
                              updateNodeData(selectedNode.id, { input_ports: newPorts })
                            }}
                            className={`flex-1 border rounded p-1 text-xs transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-200 text-gray-900'}`}
                            placeholder="ID"
                          />
                          <button onClick={() => removePort(selectedNode.id, 'input', port.id)} className="text-red-400">
                            <Trash2 size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className={`pt-4 border-t ${isDarkMode ? 'border-gray-700' : 'border-gray-100'}`}>
                    <div className="flex justify-between items-center mb-3">
                      <label className={`block text-xs font-bold uppercase ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>输出端口</label>
                      <button onClick={() => addPort(selectedNode.id, 'output')} className="text-blue-600 hover:text-blue-700">
                        <Plus size={14} />
                      </button>
                    </div>
                    <div className="space-y-2">
                      {(selectedNode.data.output_ports || []).map((port: any, idx: number) => (
                        <div key={idx} className="flex gap-1 items-center">
                          <input 
                            value={port.id} 
                            onChange={e => {
                              const newPorts = [...selectedNode.data.output_ports]
                              newPorts[idx].id = e.target.value
                              updateNodeData(selectedNode.id, { output_ports: newPorts })
                            }}
                            className={`flex-1 border rounded p-1 text-xs transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-200 text-gray-900'}`}
                            placeholder="ID"
                          />
                          <button onClick={() => removePort(selectedNode.id, 'output', port.id)} className="text-red-400">
                            <Trash2 size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
          <Sidebar availableNodes={availableNodes} />
        </ReactFlowProvider>
      </div>
    </div>
  )
}

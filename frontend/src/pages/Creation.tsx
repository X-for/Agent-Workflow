import { useState, useCallback, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Save, RefreshCcw, Plus, Trash2 } from 'lucide-react'
import axios from 'axios'
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
  START: StartEndNode,
  END: StartEndNode
}

let id = 0
const getId = () => `node_${id++}`

export default function Creation() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null)
  
  const [filename, setFilename] = useState('new_workflow.json')
  const [availableNodes, setAvailableNodes] = useState<any[]>([])
  const [selectedNode, setSelectedNode] = useState<any>(null)
  const [availableTools, setAvailableTools] = useState<string[]>([])

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
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          const field = type === 'input' ? 'input_ports' : 'output_ports'
          const currentPorts = node.data[field] || []
          const newPort = type === 'input' 
            ? { id: `in_${Date.now()}`, name: '新输入' }
            : { id: `out_${Date.now()}`, description: '新输出' }
          return { ...node, data: { ...node.data, [field]: [...currentPorts, newPort] } }
        }
        return node
      })
    )
  }

  const removePort = (nodeId: string, type: 'input' | 'output', portId: string) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          const field = type === 'input' ? 'input_ports' : 'output_ports'
          const currentPorts = node.data[field] || []
          return { ...node, data: { ...node.data, [field]: currentPorts.filter((p: any) => p.id !== portId) } }
        }
        return node
      })
    )
  }

  const updateNodeData = (nodeId: string, newData: any) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          return { ...node, data: { ...node.data, ...newData } }
        }
        return node
      })
    )
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
    [reactFlowInstance, setNodes]
  )

  const saveWorkflow = async () => {
    // 检查基础节点
    const startNode = nodes.find(n => n.type === 'START')
    const endNode = nodes.find(n => n.type === 'END')
    
    if (!startNode || !endNode) {
      alert('保存失败：工作流必须包含一个开始节点(START)和一个结束节点(END)。')
      return
    }

    // 转换 React Flow 的 nodes 为后端 Workflow 需要的结构
    const workflowNodes = nodes.map(n => {
      const baseNode: any = {
        id: n.id,
        type: n.type === 'CUSTOM_AGENT' ? 'AGENT' : n.type // 后端统一识别为 AGENT
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
        baseNode.output_ports = [{ id: "out_query" }]
      } else if (n.type === 'END') {
        baseNode.input_ports = [{ id: "in_result" }]
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
      id = 0
    }
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-gray-50">
      <div className="bg-white px-6 py-4 border-b border-gray-200 flex justify-between items-center z-10 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">拖拽式工作流构建器</h1>
          <p className="text-sm text-gray-500 mt-1">从右侧拖拽组件以创建多智能体协作流</p>
        </div>
        <div className="flex items-center gap-4">
          <input 
            value={filename}
            onChange={e => setFilename(e.target.value)}
            className="w-64 bg-gray-50 border border-gray-300 text-gray-900 rounded-lg px-4 py-2 outline-none focus:ring-2 focus:ring-blue-500/50 font-mono text-sm"
            placeholder="workflow_name.json"
          />
          <button 
            onClick={clearCanvas}
            className="flex items-center gap-2 bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg font-medium transition-colors"
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
            >
              <Background color="#cbd5e1" gap={16} />
              <Controls />
            </ReactFlow>

            {/* 右侧属性编辑面板 */}
            {selectedNode && (selectedNode.type === 'CUSTOM_AGENT' || selectedNode.type === 'AGENT') && (
              <div className="absolute right-4 top-4 bottom-4 w-80 bg-white shadow-xl border border-gray-200 rounded-2xl p-6 overflow-y-auto z-10">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="font-bold text-lg">
                    {selectedNode.type === 'CUSTOM_AGENT' ? '专用节点配置' : '通用节点覆盖'}
                  </h3>
                  <button onClick={() => setSelectedNode(null)} className="text-gray-400 hover:text-gray-600">×</button>
                </div>
                
                <div className="space-y-6">
                  {selectedNode.type === 'CUSTOM_AGENT' && (
                    <>
                      <div>
                        <label className="block text-xs font-bold text-gray-500 uppercase mb-1">显示名称</label>
                        <input 
                          value={selectedNode.data.name || ''} 
                          onChange={e => updateNodeData(selectedNode.id, { name: e.target.value, label: e.target.value })}
                          className="w-full border border-gray-200 rounded-lg p-2 text-sm"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-gray-500 uppercase mb-1">模型</label>
                        <input 
                          value={selectedNode.data.model_name || ''} 
                          onChange={e => updateNodeData(selectedNode.id, { model_name: e.target.value })}
                          className="w-full border border-gray-200 rounded-lg p-2 text-sm"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Base URL</label>
                        <input 
                          value={selectedNode.data.base_url || ''} 
                          onChange={e => updateNodeData(selectedNode.id, { base_url: e.target.value })}
                          className="w-full border border-gray-200 rounded-lg p-2 text-sm"
                          placeholder="https://api.openai.com/v1"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-gray-500 uppercase mb-1">System Prompt</label>
                        <textarea 
                          value={selectedNode.data.system_prompt || ''} 
                          onChange={e => updateNodeData(selectedNode.id, { system_prompt: e.target.value })}
                          rows={4}
                          className="w-full border border-gray-200 rounded-lg p-2 text-sm resize-none"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-gray-500 uppercase mb-1">工具</label>
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
                                  ? 'bg-blue-50 border-blue-500 text-blue-600'
                                  : 'bg-white border-gray-200 text-gray-500'
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
                  <div className="pt-4 border-t border-gray-100">
                    <div className="flex justify-between items-center mb-3">
                      <label className="block text-xs font-bold text-gray-500 uppercase">输入端口</label>
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
                            className="flex-1 border border-gray-200 rounded p-1 text-xs"
                            placeholder="ID"
                          />
                          <button onClick={() => removePort(selectedNode.id, 'input', port.id)} className="text-red-400">
                            <Trash2 size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="pt-4 border-t border-gray-100">
                    <div className="flex justify-between items-center mb-3">
                      <label className="block text-xs font-bold text-gray-500 uppercase">输出端口</label>
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
                            className="flex-1 border border-gray-200 rounded p-1 text-xs"
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
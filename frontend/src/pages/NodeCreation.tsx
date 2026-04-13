import { useState, useEffect } from 'react'
import { Save, Plus, Trash2, Settings } from 'lucide-react'
import axios from 'axios'
import { useTheme } from '../App'

export default function NodeCreation() {
  const { isDarkMode } = useTheme()
  const [filename, setFilename] = useState('new_agent.json')
  const [name, setName] = useState('自定义智能体')
  const [modelName, setModelName] = useState('deepseek-chat')
  const [baseUrl, setBaseUrl] = useState('https://api.deepseek.com')
  const [systemPrompt, setSystemPrompt] = useState('你是一个AI助手...')
  
  const [availableTools, setAvailableTools] = useState<string[]>([])
  const [selectedTools, setSelectedTools] = useState<string[]>([])
  
  const [inputPorts, setInputPorts] = useState([{ id: 'user_input', name: '用户输入' }])
  const [outputPorts, setOutputPorts] = useState([{ id: 'final_result', description: '输出处理结果' }])

  useEffect(() => {
    axios.get('/api/tools').then(res => {
      setAvailableTools(res.data.tools || [])
    }).catch(err => console.error('Failed to fetch tools:', err))
  }, [])

  const handleToolToggle = (tool: string) => {
    if (selectedTools.includes(tool)) {
      setSelectedTools(selectedTools.filter(t => t !== tool))
    } else {
      setSelectedTools([...selectedTools, tool])
    }
  }

  const saveNode = async () => {
    try {
      await axios.post('/api/nodes', {
        filename,
        name,
        type: 'AGENT',
        model_name: modelName,
        base_url: baseUrl,
        system_prompt: systemPrompt,
        tools: selectedTools,
        input_ports: inputPorts,
        output_ports: outputPorts
      })
      alert('通用节点保存成功！你现在可以在工作流画布中拖拽使用它了。')
      setFilename('')
      setName('')
    } catch (err) {
      alert('保存失败，请查看控制台')
      console.error(err)
    }
  }

  return (
    <div className={`flex-1 p-8 overflow-y-auto transition-colors duration-300 ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className={`max-w-4xl mx-auto rounded-2xl shadow-sm border p-8 transition-colors duration-300 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
        <div className={`flex justify-between items-center mb-8 pb-6 border-b ${isDarkMode ? 'border-gray-700' : 'border-gray-100'}`}>
          <div>
            <h1 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>创建通用节点 (Agent)</h1>
            <p className={`mt-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>设计一个可复用的智能体节点配置，保存后将出现在工作流的组件库中。</p>
          </div>
          <button 
            onClick={saveNode}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-medium transition-colors"
          >
            <Save size={18} />
            保存通用节点
          </button>
        </div>

        <div className="space-y-8">
          {/* 基础配置 */}
          <section className="grid grid-cols-2 gap-6">
            <div>
              <label className={`block text-sm font-bold mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>保存文件名</label>
              <input 
                value={filename} onChange={e => setFilename(e.target.value)}
                className={`w-full border rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500 transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-gray-50 border-gray-300 text-gray-900'}`}
                placeholder="例如: translator_agent.json"
              />
            </div>
            <div>
              <label className={`block text-sm font-bold mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>节点显示名称</label>
              <input 
                value={name} onChange={e => setName(e.target.value)}
                className={`w-full border rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500 transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-gray-50 border-gray-300 text-gray-900'}`}
                placeholder="例如: 翻译专家"
              />
            </div>
            <div>
              <label className={`block text-sm font-bold mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>大模型 (Model)</label>
              <input 
                value={modelName} onChange={e => setModelName(e.target.value)}
                className={`w-full border rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500 transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-gray-50 border-gray-300 text-gray-900'}`}
              />
            </div>
            <div>
              <label className={`block text-sm font-bold mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>API 基础地址 (Base URL)</label>
              <input 
                value={baseUrl} onChange={e => setBaseUrl(e.target.value)}
                className={`w-full border rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500 transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-gray-50 border-gray-300 text-gray-900'}`}
                placeholder="例如: https://api.openai.com/v1"
              />
            </div>
          </section>

          {/* System Prompt */}
          <section>
            <label className={`block text-sm font-bold mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>系统提示词 (System Prompt)</label>
            <textarea 
              value={systemPrompt} onChange={e => setSystemPrompt(e.target.value)}
              rows={5}
              className={`w-full border rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500 resize-y transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-gray-50 border-gray-300 text-gray-900'}`}
              placeholder="你是一个专业的翻译助手..."
            />
          </section>

          {/* 工具选择 */}
          <section>
            <label className={`block text-sm font-bold mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>挂载工具 (Tools)</label>
            <div className="flex flex-wrap gap-3">
              {availableTools.length === 0 ? (
                <span className="text-gray-400 text-sm">暂无可用工具</span>
              ) : (
                availableTools.map(tool => (
                  <button
                    key={tool}
                    onClick={() => handleToolToggle(tool)}
                    className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                      selectedTools.includes(tool)
                        ? 'bg-blue-600 border-blue-600 text-white'
                        : isDarkMode ? 'bg-gray-700 border-gray-600 text-gray-300 hover:bg-gray-600' : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <Settings size={14} className="inline mr-2" />
                    {tool}
                  </button>
                ))
              )}
            </div>
          </section>

          {/* 端口配置 */}
          <div className={`grid grid-cols-2 gap-8 pt-4 border-t ${isDarkMode ? 'border-gray-700' : 'border-gray-100'}`}>
            {/* Input Ports */}
            <section>
              <div className="flex justify-between items-center mb-4">
                <label className={`block text-sm font-bold ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>输入端口 (Input Ports)</label>
                <button onClick={() => setInputPorts([...inputPorts, { id: '', name: '' }])} className="text-blue-600 hover:text-blue-700">
                  <Plus size={18} />
                </button>
              </div>
              <div className="space-y-3">
                {inputPorts.map((port, idx) => (
                  <div key={idx} className="flex gap-2 items-center">
                    <input 
                      value={port.id} placeholder="端口ID (如: in_text)"
                      onChange={e => { const p = [...inputPorts]; p[idx].id = e.target.value; setInputPorts(p) }}
                      className={`flex-1 border rounded p-2 text-sm transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'}`}
                    />
                    <input 
                      value={port.name} placeholder="描述名称"
                      onChange={e => { const p = [...inputPorts]; p[idx].name = e.target.value; setInputPorts(p) }}
                      className={`flex-1 border rounded p-2 text-sm transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'}`}
                    />
                    <button onClick={() => setInputPorts(inputPorts.filter((_, i) => i !== idx))} className="text-red-400 hover:text-red-600">
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            </section>

            {/* Output Ports */}
            <section>
              <div className="flex justify-between items-center mb-4">
                <label className={`block text-sm font-bold ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>输出端口 (Output Ports)</label>
                <button onClick={() => setOutputPorts([...outputPorts, { id: '', description: '' }])} className="text-blue-600 hover:text-blue-700">
                  <Plus size={18} />
                </button>
              </div>
              <div className="space-y-3">
                {outputPorts.map((port, idx) => (
                  <div key={idx} className="flex gap-2 items-center">
                    <input 
                      value={port.id} placeholder="端口ID (如: out_result)"
                      onChange={e => { const p = [...outputPorts]; p[idx].id = e.target.value; setOutputPorts(p) }}
                      className={`flex-1 border rounded p-2 text-sm transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'}`}
                    />
                    <input 
                      value={port.description} placeholder="给大模型看的描述"
                      onChange={e => { const p = [...outputPorts]; p[idx].description = e.target.value; setOutputPorts(p) }}
                      className={`flex-1 border rounded p-2 text-sm transition-colors ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'}`}
                    />
                    <button onClick={() => setOutputPorts(outputPorts.filter((_, i) => i !== idx))} className="text-red-400 hover:text-red-600">
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}
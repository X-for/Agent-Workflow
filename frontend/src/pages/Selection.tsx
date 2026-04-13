import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, FileJson, Edit3 } from 'lucide-react'
import axios from 'axios'
import { useTheme } from '../App'

interface Workflow {
  id: string
  name: string
  description?: string
  nodesCount: number
}

export default function Selection() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const { isDarkMode } = useTheme()

  useEffect(() => {
    // Fetch available workflows from backend
    axios.get('/api/workflows')
      .then(res => {
        setWorkflows(res.data.workflows || [])
      })
      .catch(err => {
        console.error('Failed to load workflows', err)
        // Fallback for demo
        setWorkflows([
          { id: 'test.json', name: '搜索与总结测试流', description: '默认的搜索与总结多智能体工作流', nodesCount: 4 }
        ])
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className={`flex-1 p-8 overflow-y-auto transition-colors duration-300 ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="max-w-5xl mx-auto">
        <h1 className={`text-3xl font-bold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>工作流库</h1>
        <p className={`${isDarkMode ? 'text-gray-400' : 'text-gray-500'} mb-8`}>选择一个现有的多智能体工作流开始对话任务。</p>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className={`animate-spin rounded-full h-12 w-12 border-b-2 ${isDarkMode ? 'border-blue-400' : 'border-blue-600'}`}></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {workflows.map(wf => (
              <div key={wf.id} className={`${isDarkMode ? 'bg-gray-800 border-gray-700 shadow-lg' : 'bg-white border-gray-200 shadow-sm'} rounded-2xl p-6 border hover:shadow-md transition-all flex flex-col`}>
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-12 h-12 ${isDarkMode ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-50 text-blue-600'} rounded-xl flex items-center justify-center`}>
                    <FileJson size={24} />
                  </div>
                  <span className={`${isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'} text-xs px-2 py-1 rounded-full font-medium`}>
                    {wf.nodesCount} 节点
                  </span>
                </div>
                
                <h3 className={`text-xl font-bold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-800'}`}>{wf.name || wf.id}</h3>
                <p className={`text-sm mb-6 flex-1 line-clamp-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  {wf.description || '这是一个多智能体协同的工作流，支持复杂的自动化任务。'}
                </p>

                <div className="flex gap-3">
                  <button 
                    onClick={() => navigate(`/chat/${wf.id}`)}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-colors ${
                      isDarkMode 
                        ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                        : 'bg-gray-900 hover:bg-black text-white'
                    }`}
                  >
                    <Play size={18} />
                    运行
                  </button>
                  <button 
                    onClick={() => navigate(`/create?edit=${wf.id}`)}
                    className={`px-4 flex items-center justify-center rounded-xl font-medium transition-colors ${
                      isDarkMode 
                        ? 'bg-gray-700 hover:bg-gray-600 text-gray-200' 
                        : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                    }`}
                    title="修改工作流结构"
                  >
                    <Edit3 size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
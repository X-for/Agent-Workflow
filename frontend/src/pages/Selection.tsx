import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, FileJson } from 'lucide-react'
import axios from 'axios'

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
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">工作流库</h1>
        <p className="text-gray-500 mb-8">选择一个现有的多智能体工作流开始对话任务。</p>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {workflows.map(wf => (
              <div key={wf.id} className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm hover:shadow-md transition-shadow flex flex-col">
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center">
                    <FileJson size={24} />
                  </div>
                  <span className="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded-full font-medium">
                    {wf.nodesCount} 节点
                  </span>
                </div>
                
                <h3 className="text-xl font-bold text-gray-800 mb-2">{wf.name || wf.id}</h3>
                <p className="text-sm text-gray-500 mb-6 flex-1 line-clamp-2">
                  {wf.description || '这是一个多智能体协同的工作流，支持复杂的自动化任务。'}
                </p>

                <button 
                  onClick={() => navigate(`/chat/${wf.id}`)}
                  className="w-full flex items-center justify-center gap-2 bg-gray-900 hover:bg-black text-white py-3 rounded-xl font-medium transition-colors"
                >
                  <Play size={18} />
                  运行此工作流
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
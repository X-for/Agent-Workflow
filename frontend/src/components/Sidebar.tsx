import React from 'react'
import { useTheme } from '../App'

export default function Sidebar({ availableNodes }: { availableNodes: any[] }) {
  const { isDarkMode } = useTheme()
  const onDragStart = (event: React.DragEvent, node: any) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify(node))
    event.dataTransfer.effectAllowed = 'move'
  }

  return (
    <aside className={`w-72 border-l p-4 overflow-y-auto z-10 flex flex-col transition-colors duration-300 ${
      isDarkMode 
        ? 'bg-gray-800 border-gray-700 shadow-[-4px_0_15px_-3px_rgba(0,0,0,0.3)]' 
        : 'bg-white border-gray-200 shadow-[-4px_0_15px_-3px_rgba(0,0,0,0.05)]'
    }`}>
      <div className="mb-6">
        <h3 className={`text-sm font-bold uppercase tracking-wider mb-4 border-b pb-2 ${
          isDarkMode ? 'text-gray-400 border-gray-700' : 'text-gray-400 border-gray-100'
        }`}>组件库 Nodes</h3>
        <p className={`text-xs mb-4 leading-relaxed p-2 rounded-lg border transition-colors ${
          isDarkMode 
            ? 'bg-blue-900/20 text-blue-300 border-blue-800/50' 
            : 'bg-blue-50 text-gray-500 border-blue-100'
        }`}>
          💡 提示：从下方列表中拖拽节点到左侧画布区域。
        </p>
      </div>
      
      <div className="space-y-4">
        {availableNodes.map((node) => (
          <div
            key={node.id}
            onDragStart={(event) => onDragStart(event, node)}
            draggable
            className={`p-4 border rounded-xl shadow-sm cursor-grab active:cursor-grabbing transition-all hover:-translate-y-1 hover:shadow-md ${
              node.type === 'START' 
                ? (isDarkMode ? 'border-green-800 bg-green-900/20' : 'border-green-300 bg-green-50') : 
                node.type === 'END' 
                ? (isDarkMode ? 'border-red-800 bg-red-900/20' : 'border-red-300 bg-red-50') : 
                (isDarkMode ? 'border-gray-700 bg-gray-700/50' : 'border-blue-200 bg-white')
            }`}
          >
            <div className="font-bold flex items-center gap-2 mb-1">
              <span className={`text-sm w-6 h-6 rounded flex items-center justify-center ${
                node.type === 'START' ? 'bg-green-500 text-white' : 
                  node.type === 'END' ? 'bg-red-500 text-white' : 
                  (isDarkMode ? 'bg-blue-900/50 text-blue-400' : 'bg-blue-100 text-blue-600')
              }`}>
                {node.type === 'START' ? 'S' : node.type === 'END' ? 'E' : '🤖'}
              </span>
              <span className={isDarkMode ? 'text-gray-200' : 'text-gray-800'}>{node.name}</span>
            </div>
            
            <div className={`text-xs mt-2 line-clamp-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              {node.description || (node.type === 'AGENT' ? `参考配置: ${node.ref}` : '')}
            </div>
            
            {/* 端口简要展示 */}
            {node.type === 'AGENT' && (
              <div className="mt-3 flex flex-wrap gap-1">
                {node.input_ports?.map((p: any) => (
                  <span key={`in-${p.id}`} className={`text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 transition-colors ${
                    isDarkMode ? 'bg-green-900/40 text-green-400' : 'bg-green-100 text-green-700'
                  }`}>
                    <div className={`w-1.5 h-1.5 rounded-full ${isDarkMode ? 'bg-green-400' : 'bg-green-500'}`}></div>{p.id}
                  </span>
                ))}
                {node.output_ports?.map((p: any) => (
                  <span key={`out-${p.id}`} className={`text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 transition-colors ${
                    isDarkMode ? 'bg-blue-900/40 text-blue-400' : 'bg-blue-100 text-blue-700'
                  }`}>
                    {p.id}<div className={`w-1.5 h-1.5 rounded-full ${isDarkMode ? 'bg-blue-400' : 'bg-blue-500'}`}></div>
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  )
}
import React from 'react'

export default function Sidebar({ availableNodes }: { availableNodes: any[] }) {
  const onDragStart = (event: React.DragEvent, node: any) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify(node))
    event.dataTransfer.effectAllowed = 'move'
  }

  return (
    <aside className="w-72 bg-white border-l border-gray-200 p-4 overflow-y-auto shadow-[-4px_0_15px_-3px_rgba(0,0,0,0.05)] z-10 flex flex-col">
      <div className="mb-6">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 border-b pb-2">组件库 Nodes</h3>
        <p className="text-xs text-gray-500 mb-4 leading-relaxed bg-blue-50 p-2 rounded-lg border border-blue-100">
          💡 提示：从下方列表中拖拽节点到左侧画布区域。
        </p>
      </div>
      
      <div className="space-y-4">
        {availableNodes.map((node) => (
          <div
            key={node.id}
            onDragStart={(event) => onDragStart(event, node)}
            draggable
            className={`p-4 border rounded-xl shadow-sm cursor-grab active:cursor-grabbing transition-all hover:-translate-y-1 hover:shadow-md
              ${node.type === 'START' ? 'border-green-300 bg-green-50' : 
                node.type === 'END' ? 'border-red-300 bg-red-50' : 
                'border-blue-200 bg-white'}
            `}
          >
            <div className="font-bold flex items-center gap-2 mb-1">
              <span className={`text-sm w-6 h-6 rounded flex items-center justify-center
                ${node.type === 'START' ? 'bg-green-500 text-white' : 
                  node.type === 'END' ? 'bg-red-500 text-white' : 
                  'bg-blue-100 text-blue-600'}
              `}>
                {node.type === 'START' ? 'S' : node.type === 'END' ? 'E' : '🤖'}
              </span>
              <span className="text-gray-800">{node.name}</span>
            </div>
            
            <div className="text-xs text-gray-500 mt-2 line-clamp-2">
              {node.description || (node.type === 'AGENT' ? `参考配置: ${node.ref}` : '')}
            </div>
            
            {/* 端口简要展示 */}
            {node.type === 'AGENT' && (
              <div className="mt-3 flex flex-wrap gap-1">
                {node.input_ports?.map((p: any) => (
                  <span key={`in-${p.id}`} className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded flex items-center gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>{p.id}
                  </span>
                ))}
                {node.output_ports?.map((p: any) => (
                  <span key={`out-${p.id}`} className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded flex items-center gap-1">
                    {p.id}<div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div>
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
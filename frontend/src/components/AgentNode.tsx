import { Handle, Position } from '@xyflow/react'

export default function AgentNode({ data }: any) {
  return (
    <div className="bg-white rounded-xl shadow-lg border-2 border-blue-500 p-4 min-w-[200px]">
      <div className="font-bold text-blue-800 border-b pb-2 mb-2 flex items-center gap-2">
        <span className="bg-blue-100 p-1.5 rounded-md text-blue-600">🤖</span>
        {data.name || data.id}
      </div>
      
      <div className="text-xs text-gray-500 mb-3">{data.ref || 'Custom Agent'}</div>
      
      {/* 动态渲染输入端口 (Left) */}
      <div className="flex flex-col gap-2 relative">
        {data.input_ports?.map((port: any, idx: number) => (
          <div key={port.id} className="relative flex items-center justify-start">
            <Handle
              type="target"
              position={Position.Left}
              id={port.id}
              className="w-3 h-3 bg-green-500 !left-[-22px]"
            />
            <span className="text-xs font-mono bg-gray-100 px-1 rounded">{port.id}</span>
          </div>
        ))}
      </div>

      {/* 动态渲染输出端口 (Right) */}
      <div className="flex flex-col gap-2 relative mt-3">
        {data.output_ports?.map((port: any, idx: number) => (
          <div key={port.id} className="relative flex items-center justify-end">
            <span className="text-xs font-mono bg-gray-100 px-1 rounded">{port.id}</span>
            <Handle
              type="source"
              position={Position.Right}
              id={port.id}
              className="w-3 h-3 bg-blue-500 !right-[-22px]"
            />
          </div>
        ))}
      </div>
    </div>
  )
}
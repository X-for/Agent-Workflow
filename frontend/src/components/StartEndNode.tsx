import { Handle, Position } from '@xyflow/react'

export default function StartEndNode({ data }: any) {
  const isStart = data.type === 'START'
  
  return (
    <div className={`bg-white rounded-full shadow-lg border-4 px-6 py-4 flex items-center justify-center font-bold text-lg
      ${isStart ? 'border-green-500 text-green-700' : 'border-red-500 text-red-700'}
    `}>
      {isStart ? '🚀 START' : '🏁 END'}
      
      {isStart ? (
        <Handle
          type="source"
          position={Position.Right}
          id="out_query"
          className="w-4 h-4 bg-green-500 !right-[-10px]"
        />
      ) : (
        <Handle
          type="target"
          position={Position.Left}
          id="in_result"
          className="w-4 h-4 bg-red-500 !left-[-10px]"
        />
      )}
    </div>
  )
}
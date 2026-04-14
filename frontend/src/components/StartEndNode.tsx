import { Handle, Position } from '@xyflow/react'

export default function StartEndNode({ data }: any) {
  const isStart = data.type === 'START'
  
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-full shadow-lg border-4 px-6 py-4 flex items-center justify-center font-bold text-lg transition-colors
      ${isStart ? 'border-green-500 dark:border-green-600 text-green-700 dark:text-green-400' : 'border-red-500 dark:border-red-600 text-red-700 dark:text-red-400'}
    `}>
      {isStart ? '🚀 START' : '🏁 END'}
      
      {isStart ? (
        <Handle
          type="source"
          position={Position.Right}
          id="out_query"
          className="w-4 h-4 bg-green-500 dark:bg-green-400 !right-[-10px]"
        />
      ) : (
        <Handle
          type="target"
          position={Position.Left}
          id="in_result"
          className="w-4 h-4 bg-red-500 dark:bg-red-400 !left-[-10px]"
        />
      )}
    </div>
  )
}
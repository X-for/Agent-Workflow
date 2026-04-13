import { useState, useRef, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Send, Bot, User, ShieldAlert, Zap } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import axios from 'axios'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export default function Chat() {
  const { workflowId } = useParams<{ workflowId: string }>()
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init',
      role: 'assistant',
      content: `你好！👋 我是 **${workflowId}** 工作流助手。\n我可以调动背后的多个专家 Agent 协同为您工作。请输入您的问题，我们将为您提供详尽的解答与总结。`
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 128)}px`
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    try {
      const res = await axios.post('/api/chat', { 
        workflow_id: workflowId,
        query: userMessage.content 
      })
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: res.data.result || "未找到结果"
      }
      
      setMessages(prev => [...prev, assistantMessage])
    } catch (err: any) {
      console.error(err)
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `❌ 处理请求时发生错误: ${err.message}\n请检查后端服务是否正常运行。`
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 py-3 px-6 flex items-center justify-between z-10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-md">
            <Bot size={22} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-800 leading-tight">{workflowId}</h1>
            <p className="text-xs text-gray-500">Multi-Agent Collaborative System</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex h-3 w-3 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
          </span>
          <span className="text-sm text-gray-600 font-medium">System Online</span>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-4 max-w-4xl mx-auto w-full ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 shadow-sm ${
              msg.role === 'user' ? 'bg-gray-800 text-white' : 'bg-blue-100 text-blue-600'
            }`}>
              {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
            </div>
            <div className={`p-4 rounded-2xl shadow-sm border max-w-[85%] ${
              msg.role === 'user' 
                ? 'bg-gray-800 text-white rounded-tr-none border-gray-700' 
                : 'bg-white text-gray-800 rounded-tl-none border-gray-100 markdown-body'
            }`}>
              {msg.role === 'user' ? (
                <div className="whitespace-pre-wrap">{msg.content}</div>
              ) : (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              )}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex gap-4 max-w-4xl mx-auto w-full">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 flex-shrink-0 mt-1 shadow-sm">
              <Bot size={16} />
            </div>
            <div className="bg-white px-4 py-3 rounded-2xl rounded-tl-none shadow-sm border border-gray-100 flex flex-col justify-center gap-1">
              <div className="text-xs text-blue-500 font-medium mb-1 flex items-center gap-1">
                <Zap size={12} /> Agent 工作流执行中...
              </div>
              <div className="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input */}
      <footer className="bg-white border-t border-gray-200 p-4 pb-6 shrink-0 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
        <div className="max-w-4xl mx-auto relative flex items-end gap-3">
          <div className="flex-1 relative bg-gray-50 border border-gray-300 rounded-2xl shadow-inner focus-within:ring-2 focus-within:ring-blue-500/50 focus-within:border-blue-500 transition-all overflow-hidden flex items-center">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              rows={1}
              className="w-full max-h-32 py-3 px-4 bg-transparent border-none focus:ring-0 resize-none outline-none text-gray-800 text-base"
              placeholder="输入您的问题 (按 Enter 发送，Shift+Enter 换行)..."
              disabled={isLoading}
            />
          </div>
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            className="w-12 h-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-600 disabled:shadow-none flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <Send size={18} className="ml-[-2px]" />
          </button>
        </div>
        <div className="max-w-4xl mx-auto mt-3 text-center">
          <p className="text-xs text-gray-400 flex items-center justify-center gap-1">
            <ShieldAlert size={14} /> AI 生成内容仅供参考，请注意甄别信息准确性。
          </p>
        </div>
      </footer>
    </div>
  )
}
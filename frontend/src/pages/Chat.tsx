import { useState, useRef, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { 
  Send, 
  Bot, 
  User, 
  ShieldAlert, 
  Zap, 
  Moon, 
  Sun, 
  Plus, 
  MessageSquare, 
  ChevronDown, 
  Square,
  ChevronLeft, 
  Trash2, 
  History 
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import axios from 'axios'
import { useTheme } from '../App'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

interface Session {
  id: string
  name: string
  messages: Message[]
}

export default function Chat() {
  const { workflowId } = useParams<{ workflowId: string }>()
  const { isDarkMode, toggleDarkMode } = useTheme()
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSessionId, setCurrentSessionId] = useState('')
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showSessionList, setShowSessionList] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)
  
  // 加载会话列表

  useEffect(() => {
    const fetchSessions = async () => {
      if (!workflowId) return;
      try {
        console.log('正在请求会话列表，workflowId:', workflowId);
        const res = await axios.get(`/api/sessions?workflow_id=${workflowId}`)
        console.log('收到会话列表响应:', res.data);
        if (res.data.status === 'success') {
          const loadedSessions = res.data.sessions.map((s: any) => ({
            ...s,
            messages: s.messages && s.messages.length > 0 ? s.messages : [
              {
                id: 'init',
                role: 'assistant',
                content: `你好！👋 我是 **${workflowId}** 工作流助手。\n我可以调动背后的多个专家 Agent 协同为您工作。请输入您的问题，我们将为您提供详尽的解答与总结。`
              }
            ]
          }))
          setSessions(loadedSessions)
          if (loadedSessions.length > 0) {
            // 优先选择当前已选中的 ID，如果没有则选第一个
            setCurrentSessionId(prev => {
              const exists = loadedSessions.find((ls: any) => ls.id === prev);
              return exists ? prev : loadedSessions[0].id;
            });
          }
        }
      } catch (err) {
        console.error('加载会话失败:', err)
      }
    }
    fetchSessions()
  }, [workflowId])

  const currentSession = sessions.find(s => s.id === currentSessionId) || (sessions.length > 0 ? sessions[0] : { id: '', name: '', messages: [] })
  const messages = currentSession.messages

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const createNewSession = () => {
    const newId = `${workflowId}_session_${Date.now()}`
    const newSession: Session = {
      id: newId,
      name: `新对话 ${sessions.length + 1}`,
      messages: [
        {
          id: 'init',
          role: 'assistant',
          content: `这是新的对话分支。请输入您的问题。`
        }
      ]
    }
    setSessions(prev => [...prev, newSession])
    setCurrentSessionId(newId)
    setShowSessionList(false)
  }

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
      if (!isLoading) {
        sendMessage()
      }
    }
  }

  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsLoading(false)
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim()
    }

    // 更新当前 Session 的消息
    setSessions(prev => prev.map(s => {
      if (s.id === currentSessionId) {
        // 如果是第一条用户消息，更新会话名称
        const isFirstUserMessage = s.messages.filter(m => m.role === 'user').length === 0;
        const newName = isFirstUserMessage 
          ? (userMessage.content.slice(0, 20) + (userMessage.content.length > 20 ? '...' : ''))
          : s.name;
        return { ...s, name: newName, messages: [...s.messages, userMessage] };
      }
      return s;
    }))
    
    setInput('')
    setIsLoading(true)

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    // 创建一个新的 AbortController 实例用于取消请求
    abortControllerRef.current = new AbortController()

    try {
      const res = await axios.post('/api/chat', { 
        workflow_id: workflowId,
        query: userMessage.content,
        session_id: currentSessionId // 传递 session_id 以便后端处理记忆
      }, {
        signal: abortControllerRef.current.signal
      })
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: res.data.result || "未找到结果"
      }
      
      setSessions(prev => prev.map(s => 
        s.id === currentSessionId 
          ? { ...s, messages: [...s.messages, assistantMessage] }
          : s
      ))
    } catch (err: any) {
      if (axios.isCancel(err)) {
        console.log('请求被用户中断')
        const cancelMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `⚠️ 对话已中止。您可以在下方继续提问。`
        }
        setSessions(prev => prev.map(s => 
          s.id === currentSessionId 
            ? { ...s, messages: [...s.messages, cancelMessage] }
            : s
        ))
      } else {
        console.error(err)
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `❌ 处理请求时发生错误: ${err.message}\n请检查后端服务是否正常运行。`
        }
        setSessions(prev => prev.map(s => 
          s.id === currentSessionId 
            ? { ...s, messages: [...s.messages, errorMessage] }
            : s
        ))
      }
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }

  return (
    <div className={`flex flex-col h-full transition-colors duration-300 ${isDarkMode ? 'bg-gray-900 text-gray-100' : 'bg-gray-50 text-gray-800'}`}>
      {/* Header */}
      <header className={`${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} shadow-sm border-b py-3 px-6 flex items-center justify-between z-20 shrink-0`}>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-md">
              <Bot size={22} />
            </div>
            <div>
              <h1 className={`text-lg font-bold leading-tight ${isDarkMode ? 'text-white' : 'text-gray-800'}`}>{workflowId}</h1>
              <p className="text-xs text-gray-500">Multi-Agent Collaborative System</p>
            </div>
          </div>

          {/* Session Selector */}
          <div className="relative ml-4">
            <button 
              onClick={() => setShowSessionList(!showSessionList)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                isDarkMode ? 'bg-gray-700 hover:bg-gray-600 text-gray-200' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
              }`}
            >
              <MessageSquare size={16} />
              <span className="max-w-[100px] truncate">{currentSession.name}</span>
              <ChevronDown size={14} className={`transition-transform ${showSessionList ? 'rotate-180' : ''}`} />
            </button>

            {showSessionList && (
              <div className={`absolute top-full left-0 mt-2 w-56 rounded-xl shadow-xl border z-30 overflow-hidden ${
                isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
              }`}>
                <div className="p-2 max-h-64 overflow-y-auto">
                  {sessions.map(s => (
                    <button
                      key={s.id}
                      onClick={() => {
                        setCurrentSessionId(s.id)
                        setShowSessionList(false)
                      }}
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 transition-colors ${
                        currentSessionId === s.id 
                          ? 'bg-blue-600 text-white' 
                          : isDarkMode ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'
                      }`}
                    >
                      {s.name}
                    </button>
                  ))}
                </div>
                <button 
                  onClick={createNewSession}
                  className={`w-full flex items-center justify-center gap-2 p-3 text-sm font-bold border-t transition-colors ${
                    isDarkMode ? 'border-gray-700 text-blue-400 hover:bg-gray-700' : 'border-gray-100 text-blue-600 hover:bg-gray-50'
                  }`}
                >
                  <Plus size={16} /> 新建对话分支
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={toggleDarkMode}
            className={`p-2 rounded-full transition-colors ${isDarkMode ? 'bg-gray-700 text-yellow-400 hover:bg-gray-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >
            {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <div className="flex items-center gap-2">
            <span className="flex h-3 w-3 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
            <span className={`text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>System Online</span>
          </div>
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
                ? (isDarkMode ? 'bg-blue-700 text-white border-blue-600' : 'bg-gray-800 text-white border-gray-700') + ' rounded-tr-none' 
                : (isDarkMode ? 'bg-gray-800 text-gray-100 border-gray-700' : 'bg-white text-gray-800 border-gray-100') + ' rounded-tl-none markdown-body'
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
            <div className={`${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'} px-4 py-3 rounded-2xl rounded-tl-none shadow-sm border flex flex-col justify-center gap-1`}>
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
      <footer className={`${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-t p-4 pb-6 shrink-0 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]`}>
        <div className="max-w-4xl mx-auto relative flex items-end gap-3">
          <div className={`flex-1 relative rounded-2xl shadow-inner focus-within:ring-2 focus-within:ring-blue-500/50 focus-within:border-blue-500 transition-all overflow-hidden flex items-center ${
            isDarkMode ? 'bg-gray-700 border-gray-600' : 'bg-gray-50 border-gray-300'
          }`}>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              rows={1}
              className={`w-full max-h-32 py-3 px-4 bg-transparent border-none focus:ring-0 resize-none outline-none text-base ${
                isDarkMode ? 'text-white placeholder-gray-400' : 'text-gray-800 placeholder-gray-400'
              }`}
              placeholder="输入您的问题 (按 Enter 发送，Shift+Enter 换行)..."
              disabled={isLoading}
            />
          </div>
          <button
            onClick={isLoading ? stopGeneration : sendMessage}
            disabled={!isLoading && !input.trim()}
            className={`w-12 h-12 rounded-full flex items-center justify-center shadow-md transition-all flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none ${
              isLoading 
                ? 'bg-red-500 hover:bg-red-600 focus:ring-red-500 text-white animate-pulse' 
                : 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500 text-white disabled:hover:bg-blue-600'
            }`}
            title={isLoading ? "中止生成" : "发送消息"}
          >
            {isLoading ? <Square size={16} fill="currentColor" /> : <Send size={18} className="ml-[-2px]" />}
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
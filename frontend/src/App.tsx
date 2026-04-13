import { useState, useEffect, createContext, useContext } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { Bot, Layers, PlusCircle, BoxSelect, Sun, Moon } from 'lucide-react'
import Selection from './pages/Selection'
import Creation from './pages/Creation'
import Chat from './pages/Chat'
import NodeCreation from './pages/NodeCreation'

// 创建主题上下文
const ThemeContext = createContext({
  isDarkMode: false,
  toggleDarkMode: () => {},
})

export const useTheme = () => useContext(ThemeContext)

function Layout({ children }: { children: React.ReactNode }) {
  const { isDarkMode, toggleDarkMode } = useTheme()

  return (
    <div className={`flex h-screen transition-colors duration-300 ${isDarkMode ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`}>
      {/* Sidebar */}
      <aside className={`w-64 border-r flex flex-col transition-colors duration-300 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
        <div className={`p-6 flex items-center justify-between border-b ${isDarkMode ? 'border-gray-700' : 'border-gray-100'}`}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white">
              <Bot size={20} />
            </div>
            <span className={`font-bold text-lg ${isDarkMode ? 'text-white' : 'text-gray-800'}`}>Agent Flow</span>
          </div>
          <button
            onClick={toggleDarkMode}
            className={`p-1.5 rounded-lg transition-colors ${isDarkMode ? 'bg-gray-700 text-yellow-400 hover:bg-gray-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
            title={isDarkMode ? "切换到浅色模式" : "切换到深色模式"}
          >
            {isDarkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          <Link to="/" className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
            isDarkMode 
              ? 'text-gray-300 hover:bg-gray-700 hover:text-blue-400' 
              : 'text-gray-700 hover:bg-blue-50 hover:text-blue-600'
          }`}>
            <Layers size={18} />
            <span className="font-medium">工作流选择</span>
          </Link>
          <Link to="/create" className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
            isDarkMode 
              ? 'text-gray-300 hover:bg-gray-700 hover:text-blue-400' 
              : 'text-gray-700 hover:bg-blue-50 hover:text-blue-600'
          }`}>
            <PlusCircle size={18} />
            <span className="font-medium">构建工作流</span>
          </Link>
          <div className={`pt-4 mt-4 border-t ${isDarkMode ? 'border-gray-700' : 'border-gray-100'}`}>
            <p className={`px-4 text-xs font-bold uppercase tracking-wider mb-2 ${isDarkMode ? 'text-gray-500' : 'text-gray-400'}`}>组件管理</p>
            <Link to="/create-node" className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
              isDarkMode 
                ? 'text-gray-300 hover:bg-gray-700 hover:text-green-400' 
                : 'text-gray-700 hover:bg-green-50 hover:text-green-600'
            }`}>
              <BoxSelect size={18} />
              <span className="font-medium">创建通用节点</span>
            </Link>
          </div>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {children}
      </main>
    </div>
  )
}

function App() {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode')
    return saved === 'true'
  })

  useEffect(() => {
    localStorage.setItem('darkMode', isDarkMode.toString())
    if (isDarkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDarkMode])

  const toggleDarkMode = () => setIsDarkMode(!isDarkMode)

  return (
    <ThemeContext.Provider value={{ isDarkMode, toggleDarkMode }}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Selection />} />
            <Route path="/create" element={<Creation />} />
            <Route path="/create-node" element={<NodeCreation />} />
            <Route path="/chat/:workflowId" element={<Chat />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </ThemeContext.Provider>
  )
}

export default App
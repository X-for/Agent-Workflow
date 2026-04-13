import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { Bot, Layers, PlusCircle, BoxSelect } from 'lucide-react'
import Selection from './pages/Selection'
import Creation from './pages/Creation'
import Chat from './pages/Chat'
import NodeCreation from './pages/NodeCreation'

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 flex items-center gap-3 border-b border-gray-100">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white">
            <Bot size={20} />
          </div>
          <span className="font-bold text-lg text-gray-800">Agent Flow</span>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          <Link to="/" className="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-xl transition-colors">
            <Layers size={18} />
            <span className="font-medium">工作流选择</span>
          </Link>
          <Link to="/create" className="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-xl transition-colors">
            <PlusCircle size={18} />
            <span className="font-medium">构建工作流</span>
          </Link>
          <div className="pt-4 mt-4 border-t border-gray-100">
            <p className="px-4 text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">组件管理</p>
            <Link to="/create-node" className="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-green-50 hover:text-green-600 rounded-xl transition-colors">
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
  return (
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
  )
}

export default App
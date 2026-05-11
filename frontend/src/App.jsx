import { useState, useCallback } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { Menu, Brain } from 'lucide-react'
import { AuthProvider, useAuth } from './hooks/useAuth'
import Sidebar from './components/Sidebar'
import Spinner from './components/Spinner'

import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import TurmasPage from './pages/TurmasPage'
import TurmaDetailPage from './pages/TurmaDetailPage'
import AtividadesPage from './pages/AtividadesPage'
import AtividadeDetailPage from './pages/AtividadeDetailPage'
import AlunoDashboardPage from './pages/AlunoDashboardPage'
import TurmaDashboardPage from './pages/TurmaDashboardPage'
import ProfilePage from './pages/ProfilePage'

function ProtectedLayout() {
  const { user, loading } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const closeSidebar = useCallback(() => setSidebarOpen(false), [])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile top bar */}
        <header className="md:hidden sticky top-0 z-30 flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-200">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 hover:bg-gray-100 rounded-lg text-gray-600"
            aria-label="Abrir menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
              <Brain className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-gray-900 text-sm">CorrigeAI</span>
          </div>
        </header>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<ProtectedLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/turmas" element={<TurmasPage />} />
            <Route path="/turmas/:id" element={<TurmaDetailPage />} />
            <Route path="/atividades" element={<AtividadesPage />} />
            <Route path="/atividades/:id" element={<AtividadeDetailPage />} />
            <Route path="/alunos/:id" element={<AlunoDashboardPage />} />
            <Route path="/turmas/:id/dashboard" element={<TurmaDashboardPage />} />
            <Route path="/perfil" element={<ProfilePage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

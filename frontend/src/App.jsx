import { useState, useCallback, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { Menu } from 'lucide-react'
import logoUrl from './assets/logo.jpg'
import { useQuery } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './hooks/useAuth'
import Sidebar from './components/Sidebar'
import Spinner from './components/Spinner'
import UpgradeModal from './components/UpgradeModal'
import AgenteFlutuante from './components/AgenteFlutuante'
import { api } from './lib/api'

import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import TurmasPage from './pages/TurmasPage'
import TurmaDetailPage from './pages/TurmaDetailPage'
import AtividadesPage from './pages/AtividadesPage'
import AtividadeDetailPage from './pages/AtividadeDetailPage'
import AlunoDashboardPage from './pages/AlunoDashboardPage'
import TurmaDashboardPage from './pages/TurmaDashboardPage'
import ProfilePage from './pages/ProfilePage'
import AgentePage from './pages/AgentePage'

function ProtectedLayout() {
  const { user, loading } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [showUpgrade, setShowUpgrade] = useState(false)
  const closeSidebar = useCallback(() => setSidebarOpen(false), [])

  const { data: professor } = useQuery({
    queryKey: ['me'],
    queryFn: api.auth.me,
    enabled: !!user,
    staleTime: 60_000,
  })

  // Exibe o modal sempre que qualquer request retornar 402
  useEffect(() => {
    const handler = () => setShowUpgrade(true)
    window.addEventListener('quota-exceeded', handler)
    return () => window.removeEventListener('quota-exceeded', handler)
  }, [])

  // Exibe automaticamente se conta já está bloqueada ao carregar
  useEffect(() => {
    if (professor?.plano === 'bloqueado') setShowUpgrade(true)
  }, [professor?.plano])

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
    <div className="flex bg-cream">
      <Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />

      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Mobile top bar */}
        <header className="md:hidden sticky top-0 z-30 flex items-center gap-3 px-4 py-3 bg-brand-600 border-b border-brand-700">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 hover:bg-white/10 rounded-lg text-white/70"
            aria-label="Abrir menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2">
            <img src={logoUrl} alt="CorrigeAI" className="w-7 h-7 rounded-lg object-cover" />
            <span className="font-bold text-white text-sm">CorrigeAI</span>
          </div>
        </header>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>

      {showUpgrade && (
        <UpgradeModal
          professor={professor}
          onClose={() => setShowUpgrade(false)}
        />
      )}

      <AgenteFlutuante />
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
            <Route path="/agente" element={<AgentePage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

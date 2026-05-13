import { useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, Users, FileText, LogOut, Brain, X, Settings, Bot } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

const links = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/turmas', icon: Users, label: 'Turmas' },
  { to: '/atividades', icon: FileText, label: 'Atividades' },
  { to: '/agente', icon: Bot, label: 'Assistente IA' },
]

export default function Sidebar({ isOpen, onClose }) {
  const { user, signOut } = useAuth()
  const location = useLocation()

  // Close drawer on navigation (mobile). onClose is stable via useCallback in App.jsx.
  useEffect(() => { onClose() }, [location.pathname, onClose])

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`
          fixed top-0 left-0 h-full z-50 w-64 bg-brand-600 flex flex-col
          transition-transform duration-300 ease-in-out
          md:sticky md:top-0 md:h-screen md:translate-x-0 md:flex md:transition-none md:z-auto md:shrink-0
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-white/15 rounded-xl flex items-center justify-center flex-shrink-0">
              <Brain className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-bold text-white text-sm">CorrigeAI</p>
              <p className="text-xs text-white/50">Correção com IA</p>
            </div>
          </div>
          {/* Close button — mobile only */}
          <button
            onClick={onClose}
            className="md:hidden p-1.5 hover:bg-white/10 rounded-lg text-white/50"
            aria-label="Fechar menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {links.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-accent-500 text-white'
                    : 'text-white/65 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User / logout */}
        <div className="px-3 py-4 border-t border-white/10">
          <div className="flex items-center gap-3 px-3 py-2 mb-1">
            <div className="w-8 h-8 bg-accent-500/30 rounded-full flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
              {user?.nome?.charAt(0).toUpperCase() || 'P'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{user?.nome || 'Professor'}</p>
              <p className="text-xs text-white/50 truncate">{user?.email || ''}</p>
            </div>
          </div>
          <NavLink
            to="/perfil"
            className={({ isActive }) =>
              `w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-accent-500 text-white'
                  : 'text-white/65 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <Settings className="h-5 w-5" />
            Meu Perfil
          </NavLink>
          <button
            onClick={signOut}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium text-white/65 hover:bg-accent-500/20 hover:text-accent-400 transition-colors"
          >
            <LogOut className="h-5 w-5" />
            Sair
          </button>
        </div>
      </aside>
    </>
  )
}

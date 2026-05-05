import { useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, Users, FileText, LogOut, Brain, X } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

const links = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/turmas', icon: Users, label: 'Turmas' },
  { to: '/atividades', icon: FileText, label: 'Atividades' },
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
          fixed top-0 left-0 h-full z-50 w-64 bg-white border-r border-gray-200 flex flex-col
          transition-transform duration-300 ease-in-out
          md:relative md:translate-x-0 md:flex md:transition-none md:z-auto
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center flex-shrink-0">
              <Brain className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-bold text-gray-900 text-sm">CorrigeAI</p>
              <p className="text-xs text-gray-500">Correção com IA</p>
            </div>
          </div>
          {/* Close button — mobile only */}
          <button
            onClick={onClose}
            className="md:hidden p-1.5 hover:bg-gray-100 rounded-lg text-gray-400"
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
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User / logout */}
        <div className="px-3 py-4 border-t border-gray-100">
          <div className="flex items-center gap-3 px-3 py-2 mb-1">
            <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-700 font-semibold text-sm flex-shrink-0">
              {user?.nome?.charAt(0).toUpperCase() || 'P'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{user?.nome || 'Professor'}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email || ''}</p>
            </div>
          </div>
          <button
            onClick={signOut}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium text-gray-600 hover:bg-red-50 hover:text-red-600 transition-colors"
          >
            <LogOut className="h-5 w-5" />
            Sair
          </button>
        </div>
      </aside>
    </>
  )
}

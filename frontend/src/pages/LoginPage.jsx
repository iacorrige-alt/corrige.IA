import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Brain, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import Spinner from '../components/Spinner'

export default function LoginPage() {
  const { signIn, signUp } = useAuth()
  const navigate = useNavigate()

  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function switchMode(next) {
    setMode(next)
    setError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await signIn(email, password)
      } else {
        await signUp(nome.trim(), email, password)
      }
      navigate('/')
    } catch (err) {
      setError(err.message || 'Ocorreu um erro. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  const isRegister = mode === 'register'

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-600 rounded-2xl shadow-lg mb-4">
            <Brain className="h-9 w-9 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">CorrigeAI</h1>
          <p className="text-gray-500 mt-1">Correção automática com inteligência artificial</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {/* Tab switcher */}
          <div className="flex rounded-xl bg-gray-100 p-1 mb-6">
            <button
              type="button"
              onClick={() => switchMode('login')}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${
                !isRegister
                  ? 'bg-white text-indigo-700 shadow'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Entrar
            </button>
            <button
              type="button"
              onClick={() => switchMode('register')}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${
                isRegister
                  ? 'bg-white text-indigo-700 shadow'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Criar conta
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome completo
                </label>
                <input
                  type="text"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  required
                  placeholder="Prof. Ana Souza"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                E-mail
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="professor@escola.com"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Senha {isRegister && <span className="text-gray-400 font-normal">(mín. 6 caracteres)</span>}
              </label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={isRegister ? 6 : undefined}
                  placeholder="••••••••"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 text-white py-2.5 rounded-xl font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-2"
            >
              {loading ? <Spinner size="sm" /> : null}
              {loading
                ? isRegister ? 'Criando conta...' : 'Entrando...'
                : isRegister ? 'Criar conta' : 'Entrar'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

import { useState, useEffect, useRef, useCallback, createContext, useContext } from 'react'
import { api } from '../lib/api'

const AuthContext = createContext(null)

// Renova o token 5 minutos antes do vencimento (tokens Supabase duram 1h)
const REFRESH_MARGIN_MS = 5 * 60 * 1000

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const refreshTimer = useRef(null)

  const scheduleSessionCheck = useCallback((expiresAt) => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current)
    const msUntilExpiry = expiresAt * 1000 - Date.now()
    const delay = Math.max(0, msUntilExpiry - REFRESH_MARGIN_MS)

    refreshTimer.current = setTimeout(async () => {
      const refreshToken = localStorage.getItem('corrigeai_refresh_token')
      if (!refreshToken) {
        _clearSession()
        return
      }
      try {
        const data = await api.auth.refresh(refreshToken)
        // Persiste os novos tokens e reagenda para o próximo vencimento
        localStorage.setItem('corrigeai_token', data.access_token)
        localStorage.setItem('corrigeai_refresh_token', data.refresh_token)
        localStorage.setItem('corrigeai_expires_at', String(data.expires_at))
        localStorage.setItem('corrigeai_user', JSON.stringify(data))
        setUser({ id: data.user_id, email: data.email, nome: data.nome })
        scheduleSessionCheck(data.expires_at)
      } catch {
        _clearSession()
      }
    }, delay)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function _clearSession() {
    localStorage.removeItem('corrigeai_token')
    localStorage.removeItem('corrigeai_refresh_token')
    localStorage.removeItem('corrigeai_expires_at')
    localStorage.removeItem('corrigeai_user')
    setUser(null)
  }

  function _persistSession(data) {
    localStorage.setItem('corrigeai_token', data.access_token)
    localStorage.setItem('corrigeai_refresh_token', data.refresh_token)
    localStorage.setItem('corrigeai_expires_at', String(data.expires_at))
    localStorage.setItem('corrigeai_user', JSON.stringify(data))
    setUser({ id: data.user_id, email: data.email, nome: data.nome })
    scheduleSessionCheck(data.expires_at)
    return data
  }

  useEffect(() => {
    const token = localStorage.getItem('corrigeai_token')
    if (!token) {
      setLoading(false)
      return
    }

    // Agenda renovação com base no expires_at armazenado (ou decodificado do JWT)
    const storedExpiry = localStorage.getItem('corrigeai_expires_at')
    if (storedExpiry) {
      scheduleSessionCheck(parseInt(storedExpiry, 10))
    } else {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        scheduleSessionCheck(payload.exp)
      } catch { /* token malformado — me() vai rejeitar */ }
    }

    api.auth
      .me()
      .then((prof) => setUser(prof))
      .catch(() => _clearSession())
      .finally(() => setLoading(false))

    return () => { if (refreshTimer.current) clearTimeout(refreshTimer.current) }
  }, [scheduleSessionCheck])

  async function signIn(email, password) {
    return _persistSession(await api.auth.login(email, password))
  }

  async function signUp(nome, email, password) {
    return _persistSession(await api.auth.register(nome, email, password))
  }

  async function signOut() {
    if (refreshTimer.current) clearTimeout(refreshTimer.current)
    try { await api.auth.logout() } catch { /* ignore */ }
    _clearSession()
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

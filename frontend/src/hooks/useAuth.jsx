import { useState, useEffect, useRef, useCallback, createContext, useContext } from 'react'
import { api } from '../lib/api'

const AuthContext = createContext(null)

// Refresh token 5 minutes before expiry (Supabase tokens last 1h)
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
      try {
        // Re-validate session — if expired, clear user
        await api.auth.me()
      } catch {
        localStorage.removeItem('corrigeai_token')
        localStorage.removeItem('corrigeai_user')
        setUser(null)
      }
    }, delay)
  }, [])

  useEffect(() => {
    const token = localStorage.getItem('corrigeai_token')
    if (!token) {
      setLoading(false)
      return
    }

    // Decode expiry from JWT payload (no crypto needed — just inspect)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      scheduleSessionCheck(payload.exp)
    } catch { /* malformed token — let me() handle it */ }

    api.auth
      .me()
      .then((prof) => setUser(prof))
      .catch(() => {
        localStorage.removeItem('corrigeai_token')
        localStorage.removeItem('corrigeai_user')
      })
      .finally(() => setLoading(false))

    return () => { if (refreshTimer.current) clearTimeout(refreshTimer.current) }
  }, [scheduleSessionCheck])

  function _persistSession(data) {
    localStorage.setItem('corrigeai_token', data.access_token)
    localStorage.setItem('corrigeai_user', JSON.stringify(data))
    setUser({ id: data.user_id, email: data.email, nome: data.nome })
    try {
      const payload = JSON.parse(atob(data.access_token.split('.')[1]))
      scheduleSessionCheck(payload.exp)
    } catch { /* ignore malformed token */ }
    return data
  }

  async function signIn(email, password) {
    return _persistSession(await api.auth.login(email, password))
  }

  async function signUp(nome, email, password) {
    return _persistSession(await api.auth.register(nome, email, password))
  }

  async function signOut() {
    if (refreshTimer.current) clearTimeout(refreshTimer.current)
    try { await api.auth.logout() } catch { /* ignore */ }
    localStorage.removeItem('corrigeai_token')
    localStorage.removeItem('corrigeai_user')
    setUser(null)
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

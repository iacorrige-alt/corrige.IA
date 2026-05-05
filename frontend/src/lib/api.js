const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

function getToken() {
  return localStorage.getItem('corrigeai_token')
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || 'Erro na requisição')
  }

  if (res.status === 204) return null
  return res.json()
}

/**
 * Exponential backoff with full jitter for transient network/server errors.
 * Only retries on network failures (TypeError) or 5xx responses — never on
 * 4xx (client errors are deterministic and won't self-heal).
 */
async function withRetry(fn, { maxAttempts = 3, baseDelayMs = 500 } = {}) {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      return await fn()
    } catch (err) {
      const isNetworkError = err instanceof TypeError
      const isServerError = err?.status >= 500

      if ((!isNetworkError && !isServerError) || attempt === maxAttempts - 1) throw err

      const cap = baseDelayMs * 2 ** attempt
      await new Promise((r) => setTimeout(r, Math.random() * cap))
    }
  }
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const api = {
  auth: {
    login: (email, password) =>
      request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
    register: (nome, email, password) =>
      request('/auth/register', { method: 'POST', body: JSON.stringify({ nome, email, password }) }),
    logout: () => request('/auth/logout', { method: 'POST' }),
    me: () => request('/auth/me'),
  },

  // ─── Turmas ────────────────────────────────────────────────────────────────
  turmas: {
    list: () => request('/turmas'),
    get: (id) => request(`/turmas/${id}`),
    dashboard: (id) => request(`/turmas/${id}/dashboard`),
    create: (data) => request('/turmas', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id) => request(`/turmas/${id}`, { method: 'DELETE' }),
  },

  // ─── Alunos ────────────────────────────────────────────────────────────────
  alunos: {
    list: (turmaId) => request(`/turmas/${turmaId}/alunos`),
    create: (turmaId, data) =>
      request(`/turmas/${turmaId}/alunos`, { method: 'POST', body: JSON.stringify(data) }),
    delete: (id) => request(`/alunos/${id}`, { method: 'DELETE' }),
    dashboard: (id) => request(`/alunos/${id}/dashboard`),
  },

  // ─── Atividades ────────────────────────────────────────────────────────────
  atividades: {
    list: () => request('/atividades'),
    get: (id) => request(`/atividades/${id}`),
    create: (data) =>
      request('/atividades', { method: 'POST', body: JSON.stringify(data) }),
    resultados: (id) => request(`/atividades/${id}/resultados`),
    status: (id) => request(`/atividades/${id}/status`),
    upload: (id, files) => {
      const token = getToken()
      const form = new FormData()
      for (const file of files) form.append('files', file)

      const doFetch = () =>
        fetch(`${API_URL}/atividades/${id}/upload`, {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: form,
        }).then(async (r) => {
          if (!r.ok) {
            const e = await r.json().catch(() => ({ detail: r.statusText }))
            const err = new Error(e.detail || `Erro ${r.status}: ${r.statusText}`)
            err.status = r.status
            throw err
          }
          return r.json()
        })

      return withRetry(doFetch, { maxAttempts: 3, baseDelayMs: 800 })
    },
    uploadGabarito: (id, file) => {
      const token = getToken()
      const form = new FormData()
      form.append('file', file)
      return fetch(`${API_URL}/atividades/${id}/gabarito`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      }).then(async (r) => {
        if (!r.ok) {
          const e = await r.json().catch(() => ({ detail: r.statusText }))
          throw new Error(e.detail || `Erro ${r.status}: ${r.statusText}`)
        }
        return r.json()
      })
    },
    deleteGabarito: (id) => request(`/atividades/${id}/gabarito`, { method: 'DELETE' }),
  },
}

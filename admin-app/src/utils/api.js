/**
 * API client — resolves base URL at runtime:
 *   Electron: asks main process via IPC, falls back to localhost:8000
 *   iOS (Capacitor): reads from localStorage (set in Settings page)
 *   Browser dev: VITE_API_URL or localhost:8000
 */

const STORAGE_KEY = 'ms_api_url'

function getBaseUrl() {
  // Electron
  if (typeof window !== 'undefined' && window.electron?.isElectron) {
    return 'http://localhost:8000/api/v1'
  }
  // iOS / Capacitor — user-configured IP
  const stored = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null
  if (stored) return stored
  // Dev fallback
  return import.meta.env?.VITE_API_URL || 'http://localhost:8000/api/v1'
}

export function setApiUrl(url) {
  localStorage.setItem(STORAGE_KEY, url)
}

export function getApiUrl() {
  return getBaseUrl()
}

function getAuthHeaders() {
  const token = localStorage.getItem('ms_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request(method, path, body = null, options = {}) {
  const url = `${getBaseUrl()}${path}`
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
    ...options.headers,
  }

  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    ...options,
  })

  if (res.status === 401) {
    localStorage.removeItem('ms_token')
    localStorage.removeItem('ms_user')
    window.location.href = '/login'
    return
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  get:    (path, opts)       => request('GET', path, null, opts),
  post:   (path, body, opts) => request('POST', path, body, opts),
  patch:  (path, body, opts) => request('PATCH', path, body, opts),
  put:    (path, body, opts) => request('PUT', path, body, opts),
  delete: (path, opts)       => request('DELETE', path, null, opts),

  // Multipart (CSV upload)
  upload: async (path, formData) => {
    const res = await fetch(`${getBaseUrl()}${path}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || `HTTP ${res.status}`)
    }
    return res.json()
  },
}

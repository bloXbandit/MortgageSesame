import { useState, useEffect, createContext, useContext } from 'react'
import { api } from '../utils/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('ms_user')) } catch { return null }
  })
  const [loading, setLoading] = useState(false)

  const login = async (email, password) => {
    setLoading(true)
    try {
      const data = await api.post('/auth/login', { email, password })
      localStorage.setItem('ms_token', data.access_token)
      localStorage.setItem('ms_refresh', data.refresh_token)
      localStorage.setItem('ms_user', JSON.stringify(data.user))
      setUser(data.user)
      return data.user
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('ms_token')
    localStorage.removeItem('ms_refresh')
    localStorage.removeItem('ms_user')
    setUser(null)
  }

  const refreshSession = async () => {
    const refresh = localStorage.getItem('ms_refresh')
    if (!refresh) return
    try {
      const data = await api.post('/auth/refresh', { refresh_token: refresh })
      localStorage.setItem('ms_token', data.access_token)
      localStorage.setItem('ms_user', JSON.stringify(data.user))
      setUser(data.user)
    } catch {
      logout()
    }
  }

  // Refresh token 5 min before expiry (every 50 min for 60-min tokens)
  useEffect(() => {
    if (!user) return
    const interval = setInterval(refreshSession, 50 * 60 * 1000)
    return () => clearInterval(interval)
  }, [user])

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

import { createContext, useContext, useState } from 'react'

/**
 * Auth stub — replace the login/logout functions with real API calls later.
 * The shape (user, login, logout, loading) stays the same so nothing else
 * needs to change when you wire up the real auth layer.
 */
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = sessionStorage.getItem('auth_user')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(false)

  // TODO: replace with real API call e.g. POST /api/auth/login
  async function login(username, password) {
    setLoading(true)
    try {
      // --- STUB: accept any non-empty credentials ---
      await new Promise((r) => setTimeout(r, 600)) // simulate network
      if (!username || !password) throw new Error('Username and password required')
      const userData = { username }
      sessionStorage.setItem('auth_user', JSON.stringify(userData))
      setUser(userData)
      return { ok: true }
    } catch (err) {
      return { ok: false, message: err.message }
    } finally {
      setLoading(false)
    }
  }

  // TODO: replace with real API call e.g. POST /api/auth/reset-password
  async function requestPasswordReset(username) {
    setLoading(true)
    try {
      await new Promise((r) => setTimeout(r, 600))
      if (!username) throw new Error('Username required')
      return { ok: true }
    } catch (err) {
      return { ok: false, message: err.message }
    } finally {
      setLoading(false)
    }
  }

  function logout() {
    sessionStorage.removeItem('auth_user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, requestPasswordReset }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

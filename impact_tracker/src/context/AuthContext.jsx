import { createContext, useContext, useState, useCallback, useEffect } from 'react'

import { authApi } from '@/api/endpoints'



/**

 * Frontend AuthContext — mirrors server AuthAdapter seam.

 * MVP: token login via POST /api/auth/login (alias /api/auth/token)

 * Session cookie is set by the Bridge; withCredentials keeps it alive.

 * Later: swap login() to PubKit SSO without changing ticket pages.

 */

const AuthContext = createContext(null)



const STORAGE_KEY = 'impact_tracker_user'



export function AuthProvider({ children }) {

  const [user, setUser] = useState(() => {

    try {

      const stored = sessionStorage.getItem(STORAGE_KEY)

      return stored ? JSON.parse(stored) : null

    } catch {

      return null

    }

  })

  const [loading, setLoading] = useState(false)

  const [bootstrapping, setBootstrapping] = useState(true)



  // Rehydrate from Bridge session cookie on mount

  useEffect(() => {

    let cancelled = false

    ;(async () => {

      try {

        const { data } = await authApi.me()

        if (cancelled) return

        const userData = data.user || null

        if (userData) {

          sessionStorage.setItem(STORAGE_KEY, JSON.stringify(userData))

          setUser(userData)

        } else {

          sessionStorage.removeItem(STORAGE_KEY)

          setUser(null)

        }

      } catch {

        if (cancelled) return

        sessionStorage.removeItem(STORAGE_KEY)

        setUser(null)

      } finally {

        if (!cancelled) setBootstrapping(false)

      }

    })()

    return () => {

      cancelled = true

    }

  }, [])



  const loginWithToken = useCallback(async (token) => {

    setLoading(true)

    try {

      if (!token?.trim()) throw new Error('API token is required')

      const { data } = await authApi.loginToken(token.trim())

      const userData = data.user || { name: 'Mantis user' }

      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(userData))

      setUser(userData)

      return { ok: true, user: userData }

    } catch (err) {

      const message = err.response?.data?.message || err.message || 'Login failed'

      return { ok: false, message }

    } finally {

      setLoading(false)

    }

  }, [])



  const logout = useCallback(async () => {

    try {

      await authApi.logout()

    } catch {

      // ignore network errors on logout

    }

    sessionStorage.removeItem(STORAGE_KEY)

    setUser(null)

  }, [])



  return (

    <AuthContext.Provider

      value={{

        user,

        loading: loading || bootstrapping,

        isAuthenticated: Boolean(user),

        loginWithToken,

        logout,

        authMode: 'token',

      }}

    >

      {children}

    </AuthContext.Provider>

  )

}



export const useAuth = () => useContext(AuthContext)


import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '@/context/AuthContext'
import { MANTIS_BASE_URL } from '@/config/env'

export default function LoginToken() {
  const { loginWithToken, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [token, setToken] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    const result = await loginWithToken(token)
    if (result.ok) {
      toast.success(`Signed in as ${result.user?.name || 'Mantis user'}`)
      const dest = location.state?.from || '/tickets'
      navigate(dest, { replace: true })
    } else {
      setError(result.message || 'Login failed')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-100 via-white to-blue-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-brand-600 text-white text-xl font-bold mb-3">
            I
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Impact Tracker</h1>
          <p className="text-sm text-slate-500 mt-1">
            Sign in with a Mantis API token
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Mantis API token</label>
              <input
                type="password"
                autoFocus
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Paste token from My Account → API Tokens"
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
              />
              <p className="mt-2 text-xs text-slate-500">
                Create a token in{' '}
                <a
                  href={MANTIS_BASE_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="text-brand-600 hover:underline"
                >
                  Mantis
                </a>
                . PubKit SSO will plug in later without changing ticket screens.
              </p>
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-medium py-2.5 text-sm"
            >
              {loading ? 'Validating…' : 'Continue'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

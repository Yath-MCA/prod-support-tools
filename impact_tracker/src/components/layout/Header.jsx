import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

export default function Header() {
  const { user, logout } = useAuth()
  const location = useLocation()

  const title = location.pathname.startsWith('/tickets/new')
    ? 'Create ticket'
    : location.pathname.startsWith('/tickets/')
      ? 'Ticket detail'
      : location.pathname.startsWith('/settings')
        ? 'Settings'
        : 'Tickets'

  return (
    <header className="flex items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur px-4 py-3">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
        <p className="text-xs text-slate-500">Impact-scoped Mantis tickets</p>
      </div>
      <div className="flex items-center gap-2 md:hidden">
        <Link to="/tickets" className="text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-800">
          List
        </Link>
        <Link to="/tickets/new" className="text-xs px-2 py-1 rounded bg-brand-600 text-white">
          New
        </Link>
        <button type="button" onClick={logout} className="text-xs px-2 py-1 text-red-600">
          Out
        </button>
      </div>
      <div className="hidden md:block text-sm text-slate-500">{user?.name}</div>
    </header>
  )
}

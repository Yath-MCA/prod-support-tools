import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { useSettings } from '@/context/SettingsContext'

const linkClass = ({ isActive }) =>
  `block rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    isActive
      ? 'bg-brand-600 text-white'
      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
  }`

export default function Sidebar() {
  const { user, logout } = useAuth()
  const { toggleDark, dark } = useSettings()

  return (
    <aside className="hidden md:flex w-56 shrink-0 flex-col border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
      <div className="px-4 py-5 border-b border-slate-200 dark:border-slate-800">
        <Link to="/tickets" className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white text-sm font-bold">
            I
          </span>
          <div>
            <div className="text-sm font-semibold">Impact Tracker</div>
            <div className="text-[11px] text-slate-500">Mantis proxy</div>
          </div>
        </Link>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        <NavLink to="/tickets" className={linkClass} end>
          Tickets
        </NavLink>
        <NavLink to="/tickets/new" className={linkClass}>
          Create
        </NavLink>
        <NavLink to="/settings" className={linkClass}>
          Settings
        </NavLink>
      </nav>

      <div className="p-3 border-t border-slate-200 dark:border-slate-800 space-y-2">
        <div className="px-2 text-xs text-slate-500 truncate">{user?.name || user?.email || 'User'}</div>
        <button
          type="button"
          onClick={toggleDark}
          className="w-full rounded-lg px-3 py-2 text-left text-xs text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          {dark ? 'Light mode' : 'Dark mode'}
        </button>
        <button
          type="button"
          onClick={logout}
          className="w-full rounded-lg px-3 py-2 text-left text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
        >
          Sign out
        </button>
      </div>
    </aside>
  )
}

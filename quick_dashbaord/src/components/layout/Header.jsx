import { useTheme } from '@/context/ThemeContext'
import { useAuth } from '@/context/AuthContext'
import { useSettings } from '@/context/SettingsContext'
import { useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import DbStatusBadge from '@/components/ui/DbStatusBadge'
import { useDatabases } from '@/hooks/useDatabases'

const PAGE_TITLES = {
  '/dashboard':    'Dashboard',
  '/files':        'Files List',
  '/doc-history':  'Doc History',
  '/link-sharing': 'Link Sharing',
  '/activity':     'Activity Feed',
  '/settings':     'Settings',
}

export default function Header() {
  const { dark, toggle }           = useTheme()
  const { user, logout }           = useAuth()
  const { settings, updateSettings } = useSettings()
  const { pathname }               = useLocation()
  const navigate                   = useNavigate()
  const queryClient                = useQueryClient()
  const { data: databases = [] }   = useDatabases()
  const title = PAGE_TITLES[pathname] ?? 'Dashboard'

  function handleLogout() {
    logout()
    toast.success('Signed out')
    navigate('/login', { replace: true })
  }

  function handleDbChange(e) {
    const db = e.target.value
    updateSettings({ selectedDb: db })
    queryClient.invalidateQueries()   // refetch everything for the new db
    toast.success(`Switched to ${db}`)
  }

  return (
    <header className="h-14 flex items-center gap-3 px-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shrink-0">
      <h1 className="font-semibold text-gray-800 dark:text-gray-100 text-base whitespace-nowrap">{title}</h1>

      <div className="flex-1 max-w-xs ml-2">
        <input
          type="search"
          placeholder="Search..."
          className="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-gray-50 dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="ml-auto flex items-center gap-3">
        {/* Database switcher */}
        <div className="flex items-center gap-1.5">
          <span className="text-base" title="Database">🗃</span>
          <select
            value={settings.selectedDb}
            onChange={handleDbChange}
            className="border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1 text-xs bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 max-w-[140px]"
            title="Switch database"
          >
            {/* Always show the current selection even if /databases hasn't loaded */}
            {databases.length === 0
              ? <option value={settings.selectedDb}>{settings.selectedDb}</option>
              : databases.map((d) => (
                  <option key={d.name} value={d.name}>{d.name}</option>
                ))
            }
          </select>
        </div>

        <DbStatusBadge />

        <button
          onClick={toggle}
          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400"
          title="Toggle theme"
        >
          {dark ? '☀' : '🌙'}
        </button>

        <div className="relative group">
          <div className="w-8 h-8 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center cursor-pointer select-none">
            {user?.username?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div className="absolute right-0 top-10 w-40 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg py-1 hidden group-hover:block z-50">
            <p className="px-3 py-1.5 text-xs text-gray-500 dark:text-gray-400 truncate border-b border-gray-100 dark:border-gray-800">
              {user?.username}
            </p>
            <button
              onClick={handleLogout}
              className="w-full text-left px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}

import { NavLink } from 'react-router-dom'
import { useState } from 'react'

const NAV = [
  { to: '/dashboard', icon: '▣', label: 'Dashboard' },
  { to: '/files', icon: '📄', label: 'Files List' },
  { to: '/doc-history', icon: '🕐', label: 'Doc History' },
  { to: '/link-sharing', icon: '🔗', label: 'Link Sharing' },
  { to: '/activity',    icon: '⚡', label: 'Activity Feed' },
  { to: '/settings',    icon: '⚙', label: 'Settings' },
]

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={`flex flex-col bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transition-all duration-200 ${collapsed ? 'w-14' : 'w-52'} shrink-0 h-full`}
    >
      <div className="flex items-center justify-between px-3 py-4 border-b border-gray-200 dark:border-gray-800">
        {!collapsed && (
          <span className="font-bold text-blue-600 dark:text-blue-400 truncate text-sm">Prod Dashboard</span>
        )}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="ml-auto p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? '→' : '←'}
        </button>
      </div>

      <nav className="flex-1 py-2 space-y-0.5 overflow-y-auto">
        {NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 mx-1 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`
            }
          >
            <span className="text-base shrink-0">{icon}</span>
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

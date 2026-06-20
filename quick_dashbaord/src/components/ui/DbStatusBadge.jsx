import { useDbStatus } from '@/hooks/useDbStatus'

const CONFIG = {
  connected:    { dot: 'bg-green-500',  ring: 'ring-green-400',  label: 'DB Connected',    text: 'text-green-600 dark:text-green-400' },
  connecting:   { dot: 'bg-yellow-400', ring: 'ring-yellow-300', label: 'DB Connecting…',  text: 'text-yellow-600 dark:text-yellow-400' },
  disconnected: { dot: 'bg-red-500',    ring: 'ring-red-400',    label: 'DB Disconnected', text: 'text-red-600 dark:text-red-400' },
  offline:      { dot: 'bg-gray-400',   ring: 'ring-gray-300',   label: 'Server Offline',  text: 'text-gray-500 dark:text-gray-400' },
}

export default function DbStatusBadge() {
  const { state } = useDbStatus()
  const { dot, ring, label, text } = CONFIG[state]
  const pulse = state === 'connected' || state === 'connecting'

  return (
    <div className="relative group flex items-center gap-1.5 cursor-default select-none">
      {/* Icon */}
      <span className="text-base" title={label}>🗄</span>

      {/* Dot indicator */}
      <span className={`relative flex h-2.5 w-2.5`}>
        {pulse && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${dot} opacity-60`} />
        )}
        <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${dot} ring-2 ${ring}`} />
      </span>

      {/* Tooltip on hover */}
      <div className={`absolute left-1/2 -translate-x-1/2 top-8 whitespace-nowrap bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-2.5 py-1 text-xs font-medium shadow-md hidden group-hover:block z-50 ${text}`}>
        {label}
      </div>
    </div>
  )
}

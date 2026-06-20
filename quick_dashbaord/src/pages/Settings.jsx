import { useState } from 'react'
import toast from 'react-hot-toast'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { useSettings } from '@/context/SettingsContext'
import { useTheme } from '@/context/ThemeContext'

const INTERVALS = [
  { label: '15 seconds', value: 15_000 },
  { label: '30 seconds', value: 30_000 },
  { label: '1 minute', value: 60_000 },
  { label: '5 minutes', value: 300_000 },
  { label: 'Off', value: 0 },
]

export default function Settings() {
  const { settings, updateSettings } = useSettings()
  const { dark, toggle } = useTheme()

  const [apiUrl, setApiUrl] = useState(settings.apiBaseUrl)
  const [interval, setInterval] = useState(settings.refreshInterval)

  function save() {
    updateSettings({ apiBaseUrl: apiUrl, refreshInterval: interval })
    toast.success('Settings saved — reload to apply API URL change')
  }

  return (
    <div className="max-w-lg space-y-4">
      <Card>
        <h2 className="font-semibold text-gray-800 dark:text-gray-100 mb-4">API Configuration</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">API Base URL</label>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Auto-refresh interval</label>
            <select
              value={interval}
              onChange={(e) => setInterval(Number(e.target.value))}
              className="border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-900 w-full"
            >
              {INTERVALS.map((i) => (
                <option key={i.value} value={i.value}>{i.label}</option>
              ))}
            </select>
          </div>
          <Button onClick={save}>Save Settings</Button>
        </div>
      </Card>

      <Card>
        <h2 className="font-semibold text-gray-800 dark:text-gray-100 mb-4">Appearance</h2>
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {dark ? 'Dark mode enabled' : 'Light mode enabled'}
          </span>
          <Button variant="secondary" onClick={toggle}>
            {dark ? '☀ Light' : '🌙 Dark'}
          </Button>
        </div>
      </Card>
    </div>
  )
}

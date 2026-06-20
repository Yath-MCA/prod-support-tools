import { createContext, useContext, useState } from 'react'
import { API_BASE_URL, REFRESH_INTERVAL } from '@/config/env'

const SettingsContext = createContext(null)

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState({
    apiBaseUrl:       localStorage.getItem('apiBaseUrl')       || API_BASE_URL,
    refreshInterval:  Number(localStorage.getItem('refreshInterval')) || REFRESH_INTERVAL,
    selectedDb:       localStorage.getItem('selectedDb')       || 'XMLEDITOR',
  })

  function updateSettings(patch) {
    setSettings((prev) => {
      const next = { ...prev, ...patch }
      localStorage.setItem('apiBaseUrl',      next.apiBaseUrl)
      localStorage.setItem('refreshInterval', String(next.refreshInterval))
      localStorage.setItem('selectedDb',      next.selectedDb)
      return next
    })
  }

  return (
    <SettingsContext.Provider value={{ settings, updateSettings }}>
      {children}
    </SettingsContext.Provider>
  )
}

export const useSettings = () => useContext(SettingsContext)

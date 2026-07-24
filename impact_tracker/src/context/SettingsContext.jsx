import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { configApi } from '@/api/endpoints'

const SettingsContext = createContext(null)
const LOCAL_KEY = 'impact_tracker_settings'

const defaults = {
  projectId: '',
  pageSize: 50,
  dark: false,
  /** Extra Mantis saved filter ids (comma-separated in UI, stored as string[]) */
  savedFilterIds: [],
}

export function SettingsProvider({ children }) {
  const [local, setLocal] = useState(() => {
    try {
      const raw = localStorage.getItem(LOCAL_KEY)
      return raw ? { ...defaults, ...JSON.parse(raw) } : { ...defaults }
    } catch {
      return { ...defaults }
    }
  })
  const [impactConfig, setImpactConfig] = useState(null)
  const [configLoading, setConfigLoading] = useState(true)

  useEffect(() => {
    localStorage.setItem(LOCAL_KEY, JSON.stringify(local))
    if (local.dark) document.documentElement.classList.add('dark')
    else document.documentElement.classList.remove('dark')
  }, [local])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const { data } = await configApi.impact()
        if (!cancelled) {
          setImpactConfig(data)
          setLocal((prev) => {
            if (prev.projectId) return prev
            const first = data?.projects?.[0]?.id
            return first ? { ...prev, projectId: String(first) } : prev
          })
        }
      } catch {
        if (!cancelled) {
          setImpactConfig({
            projects: [{ id: 0, name: 'IMPACT' }],
            defaultFilters: ['assigned', 'unassigned', 'reported'],
            savedFilterIds: [],
            mantisViewUrl: 'https://mantis.newgen.co/view.php?id=',
            statusOptions: [],
            priorityOptions: [],
          })
        }
      } finally {
        if (!cancelled) setConfigLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const update = (patch) => setLocal((prev) => ({ ...prev, ...patch }))
  const toggleDark = () => setLocal((prev) => ({ ...prev, dark: !prev.dark }))

  const value = useMemo(
    () => ({
      ...local,
      impactConfig,
      configLoading,
      update,
      toggleDark,
    }),
    [local, impactConfig, configLoading]
  )

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
}

export const useSettings = () => useContext(SettingsContext)

import { useQuery } from '@tanstack/react-query'
import { fetchRDocViewHistory } from '@/api/endpoints'
import { genRDocViewHistory } from '@/utils/mockData'
import { useSettings } from '@/context/SettingsContext'

const MOCK = genRDocViewHistory(60)

export function useRDocViewHistory(filters = {}) {
  const { settings } = useSettings()
  const params = { ...filters, db: settings.selectedDb }
  return useQuery({
    queryKey: ['rdocviewhistory', params],
    queryFn: () => fetchRDocViewHistory(params),
    refetchInterval: settings.refreshInterval,
    placeholderData: MOCK,
    select: (data) => (Array.isArray(data) ? data : data?.data ?? MOCK),
  })
}

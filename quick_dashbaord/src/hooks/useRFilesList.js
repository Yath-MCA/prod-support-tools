import { useQuery } from '@tanstack/react-query'
import { fetchRFilesList } from '@/api/endpoints'
import { genRFilesList } from '@/utils/mockData'
import { useSettings } from '@/context/SettingsContext'

const MOCK = genRFilesList(80)

export function useRFilesList(filters = {}) {
  const { settings } = useSettings()
  const params = { ...filters, db: settings.selectedDb }
  return useQuery({
    queryKey: ['rFileslist', params],
    queryFn: () => fetchRFilesList(params),
    refetchInterval: settings.refreshInterval,
    placeholderData: MOCK,
    select: (data) => (Array.isArray(data) ? data : data?.data ?? MOCK),
  })
}

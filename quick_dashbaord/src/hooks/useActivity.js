import { useQuery } from '@tanstack/react-query'
import { fetchActivity } from '@/api/endpoints'
import { useSettings } from '@/context/SettingsContext'
import { genRFilesList, genRDocViewHistory, genRLinkSharing } from '@/utils/mockData'

// Combine mock sets and sort by timeiso_c desc as a fallback
const MOCK = [
  ...genRFilesList(80).map((r)   => ({ ...r, _source: 'rFileslist' })),
  ...genRDocViewHistory(60).map((r) => ({ ...r, _source: 'rdocviewhistory' })),
  ...genRLinkSharing(50).map((r)   => ({ ...r, _source: 'rlinksharing' })),
].sort((a, b) => new Date(b.timeiso_c) - new Date(a.timeiso_c))

export function useActivity(filters = {}) {
  const { settings } = useSettings()
  const params = { ...filters, db: settings.selectedDb }
  return useQuery({
    queryKey: ['activity', params],
    queryFn: () => fetchActivity(params),
    refetchInterval: settings.refreshInterval,
    placeholderData: { data: MOCK, total: MOCK.length },
    select: (res) => ({
      data:  Array.isArray(res) ? res : (res?.data ?? MOCK),
      total: res?.total ?? MOCK.length,
    }),
  })
}

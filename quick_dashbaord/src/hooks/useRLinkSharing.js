import { useQuery } from '@tanstack/react-query'
import { fetchRLinkSharing } from '@/api/endpoints'
import { genRLinkSharing } from '@/utils/mockData'
import { useSettings } from '@/context/SettingsContext'

const MOCK = genRLinkSharing(50)

export function useRLinkSharing(filters = {}) {
  const { settings } = useSettings()
  const params = { ...filters, db: settings.selectedDb }
  return useQuery({
    queryKey: ['rlinksharing', params],
    queryFn: () => fetchRLinkSharing(params),
    refetchInterval: settings.refreshInterval,
    placeholderData: MOCK,
    select: (data) => (Array.isArray(data) ? data : data?.data ?? MOCK),
  })
}

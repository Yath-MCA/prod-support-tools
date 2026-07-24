import { useQuery } from '@tanstack/react-query'
import { ticketsApi } from '@/api/endpoints'
import { useAuth } from '@/context/AuthContext'

export function useTickets({ projectId, filterId, page = 1, pageSize = 50 }) {
  const { isAuthenticated } = useAuth()

  return useQuery({
    queryKey: ['tickets', projectId, filterId, page, pageSize],
    enabled: isAuthenticated,
    queryFn: async () => {
      const params = {
        page,
        page_size: pageSize,
      }
      if (projectId && projectId !== '0') params.project_id = projectId
      // 'open' is client-side (exclude closed/resolved); not a Mantis filter_id
      if (filterId && filterId !== 'open') params.filter_id = filterId
      const { data } = await ticketsApi.list(params)
      return data
    },
  })
}

export function useTicket(id) {
  const { isAuthenticated } = useAuth()
  return useQuery({
    queryKey: ['ticket', id],
    enabled: isAuthenticated && Boolean(id),
    queryFn: async () => {
      const { data } = await ticketsApi.get(id)
      return data
    },
  })
}

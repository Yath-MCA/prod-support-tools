import { useQuery } from '@tanstack/react-query'
import { fetchDatabases } from '@/api/endpoints'

export function useDatabases() {
  return useQuery({
    queryKey: ['databases'],
    queryFn: fetchDatabases,
    staleTime: 60_000,
    retry: false,
    select: (data) => (Array.isArray(data) ? data : []),
  })
}

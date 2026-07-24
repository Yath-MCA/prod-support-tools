import { useQuery } from '@tanstack/react-query'
import { lookupApi } from '@/api/endpoints'
import { useAuth } from '@/context/AuthContext'

export function useProjects() {
  const { isAuthenticated } = useAuth()
  return useQuery({
    queryKey: ['projects'],
    enabled: isAuthenticated,
    queryFn: async () => {
      const { data } = await lookupApi.projects()
      return data
    },
  })
}

export function useUsers(projectId) {
  const { isAuthenticated } = useAuth()
  return useQuery({
    queryKey: ['users', projectId],
    enabled: isAuthenticated,
    queryFn: async () => {
      const { data } = await lookupApi.users(projectId)
      return data
    },
  })
}

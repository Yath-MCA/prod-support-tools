import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { API_BASE_URL } from '@/config/env'

// Mongoose readyState: 0=disconnected 1=connected 2=connecting 3=disconnecting
const HEALTH_URL = API_BASE_URL.replace(/\/api$/, '/health')

export function useDbStatus() {
  const { data, isError } = useQuery({
    queryKey: ['db-health'],
    queryFn: () => axios.get(HEALTH_URL, { timeout: 4000 }).then((r) => r.data),
    refetchInterval: 10_000,
    retry: false,
  })

  if (isError || !data)          return { state: 'offline',     readyState: null }
  if (data.db === 1)             return { state: 'connected',   readyState: 1 }
  if (data.db === 2)             return { state: 'connecting',  readyState: 2 }
  return                                { state: 'disconnected', readyState: data.db }
}

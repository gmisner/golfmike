import { useQuery } from '@tanstack/react-query'
import api from '@/api/client'

interface StatusResponse {
  connected: boolean
  flight_count: number
}

export function useLiveStatus() {
  const { data } = useQuery<StatusResponse>({
    queryKey: ['live-status'],
    queryFn: async () => {
      const { data } = await api.get('/status')
      return data
    },
    refetchInterval: 10_000,
    // Don't hard-fail when the endpoint doesn't exist yet
    retry: false,
  })

  return {
    connected: data?.connected ?? false,
    flightCount: data?.flight_count ?? 0,
  }
}

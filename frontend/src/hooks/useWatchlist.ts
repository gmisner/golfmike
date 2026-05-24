import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getWatchlist,
  getWatchlistFlights,
  addToWatchlist,
  removeFromWatchlist,
  updateWatchlistItem,
  type WatchlistItem,
} from '@/api/watchlist'
import { useAuth } from './useAuth'

export function useWatchlist() {
  const { isAuthenticated } = useAuth()
  const qc = useQueryClient()

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: getWatchlist,
    enabled: isAuthenticated,
    staleTime: 30_000,
  })

  const { data: flights = [], isLoading: flightsLoading } = useQuery({
    queryKey: ['watchlist-flights'],
    queryFn: getWatchlistFlights,
    enabled: isAuthenticated && items.length > 0,
    refetchInterval: 20_000,
  })

  const addMutation = useMutation({
    mutationFn: ({ aircraft_id, label }: { aircraft_id: string; label?: string }) =>
      addToWatchlist(aircraft_id, label),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['watchlist'] })
      qc.invalidateQueries({ queryKey: ['watchlist-flights'] })
    },
  })

  const removeMutation = useMutation({
    mutationFn: (id: number) => removeFromWatchlist(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ['watchlist'] })
      const prev = qc.getQueryData<WatchlistItem[]>(['watchlist'])
      qc.setQueryData<WatchlistItem[]>(['watchlist'], (old) => old?.filter((i) => i.id !== id))
      return { prev }
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.prev) qc.setQueryData(['watchlist'], ctx.prev)
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['watchlist'] })
      qc.invalidateQueries({ queryKey: ['watchlist-flights'] })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      updates,
    }: {
      id: number
      updates: Parameters<typeof updateWatchlistItem>[1]
    }) => updateWatchlistItem(id, updates),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  })

  const isWatching = (aircraft_id: string) =>
    items.some((i) => i.aircraft_id === aircraft_id.toUpperCase())

  const watchlistIdFor = (aircraft_id: string) =>
    items.find((i) => i.aircraft_id === aircraft_id.toUpperCase())?.id ?? null

  return {
    items,
    flights,
    isLoading,
    flightsLoading,
    isWatching,
    watchlistIdFor,
    add:    addMutation,
    remove: removeMutation,
    update: updateMutation,
  }
}

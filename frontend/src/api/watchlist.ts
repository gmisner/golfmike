import api from './client'
import type { FlightSummary } from './flights'

export interface WatchlistItem {
  id: number
  aircraft_id: string
  label: string | null
  notify_departure: boolean
  notify_arrival: boolean
  notify_filed: boolean
  created_at: string
}

export interface WatchlistFlight extends FlightSummary {
  watchlist_id: number
  label: string | null
}

export async function getWatchlist(): Promise<WatchlistItem[]> {
  const { data } = await api.get('/watchlist')
  return data.items ?? data
}

export async function addToWatchlist(
  aircraft_id: string,
  label?: string,
): Promise<WatchlistItem> {
  const { data } = await api.post('/watchlist', { aircraft_id, label })
  return data
}

export async function updateWatchlistItem(
  id: number,
  updates: Partial<Pick<WatchlistItem, 'label' | 'notify_departure' | 'notify_arrival' | 'notify_filed'>>,
): Promise<WatchlistItem> {
  const { data } = await api.patch(`/watchlist/${id}`, updates)
  return data
}

export async function removeFromWatchlist(id: number): Promise<void> {
  await api.delete(`/watchlist/${id}`)
}

export async function getWatchlistFlights(): Promise<WatchlistFlight[]> {
  const { data } = await api.get('/watchlist/flights')
  return data.flights ?? data
}

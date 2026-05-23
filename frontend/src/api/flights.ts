import api from './client'

export interface FlightSummary {
  ident: string
  origin: string
  destination: string
  aircraft_type: string | null
  departure_time: string | null
  arrival_time: string | null
  status: string
  latitude: number | null
  longitude: number | null
  altitude: number | null
  ground_speed: number | null
}

export interface FlightDetail extends FlightSummary {
  track: Array<{ lat: number; lon: number; alt: number; ts: string }>
  tbfm: {
    scheduled_time: string | null
    apt: string | null
  } | null
}

export interface SearchResult {
  flights: FlightSummary[]
  total: number
}

export async function searchFlights(q: string): Promise<SearchResult> {
  const { data } = await api.get('/flights/search', { params: { q, limit: 20 } })
  return data
}

export async function getFlightDetail(ident: string): Promise<FlightDetail> {
  const { data } = await api.get(`/flights/${ident}`)
  return data
}

export async function getActiveFlights(limit = 50): Promise<FlightSummary[]> {
  const { data } = await api.get('/flights/active', { params: { limit } })
  return data.flights ?? data
}

export async function getRecentEvents(limit = 30): Promise<Array<{
  id: number
  event_type: string
  ident: string
  airport: string | null
  ts: string
  message: string
}>> {
  const { data } = await api.get('/events/recent', { params: { limit } })
  return data.events ?? data
}

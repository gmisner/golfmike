import api from './client'

export interface AirportRisk {
  icao: string
  iata: string | null
  name: string
  category: 'VFR' | 'MVFR' | 'IFR' | 'LIFR' | 'UNKNOWN'
  ceiling: number | null
  visibility: number | null
  wind_speed: number | null
  wind_dir: number | null
  raw_metar: string | null
  observed: string | null
}

export async function getAirportRisk(icao: string): Promise<AirportRisk> {
  const { data } = await api.get(`/airports/${icao}/risk`)
  return data
}

export async function getAirportList(): Promise<AirportRisk[]> {
  const { data } = await api.get('/airports')
  return data.airports ?? data
}

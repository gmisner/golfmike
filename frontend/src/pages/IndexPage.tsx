import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, Plane, Radio } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { searchFlights, getActiveFlights, getRecentEvents } from '@/api/flights'
import { getAirportList, type AirportRisk } from '@/api/airports'
import FlightCard from '@/components/flights/FlightCard'
import EventFeed from '@/components/flights/EventFeed'
import AirportRiskBadge from '@/components/airports/AirportRiskBadge'

export default function IndexPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Search results (debounced)
  const { data: searchResults, isFetching: searchFetching } = useQuery({
    queryKey: ['flight-search', query],
    queryFn: () => searchFlights(query),
    enabled: query.trim().length >= 2,
  })

  // Active flights grid
  const { data: activeFlights, isLoading: activeFetching } = useQuery({
    queryKey: ['active-flights'],
    queryFn: () => getActiveFlights(48),
    refetchInterval: 15_000,
  })

  // Events feed
  const { data: events } = useQuery({
    queryKey: ['recent-events'],
    queryFn: () => getRecentEvents(30),
    refetchInterval: 10_000,
  })

  // Airport risk sidebar
  const { data: airports } = useQuery({
    queryKey: ['airport-list'],
    queryFn: getAirportList,
    refetchInterval: 60_000,
  })

  // Keyboard shortcut: / to focus search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchResults?.flights?.length === 1) {
      navigate(`/flight/${searchResults.flights[0].ident}`)
    }
  }

  const showResults = searching && query.trim().length >= 2

  return (
    <div className="space-y-6">
      {/* Hero search */}
      <div className="py-8 text-center space-y-4">
        <h1 className="text-3xl font-semibold tracking-tight">
          Track any flight, live.
        </h1>
        <p className="text-muted-foreground text-sm">
          Powered by FAA SWIM — ADS-B, FDPS, weather, and TBFM metering data.
        </p>
        <form
          onSubmit={handleSearch}
          className="relative mx-auto max-w-lg"
          onFocus={() => setSearching(true)}
          onBlur={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget)) setSearching(false)
          }}
        >
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Flight number, tail number, or airport… (/)"
            className="pl-9 pr-4 h-11 text-sm"
            autoComplete="off"
          />
          {showResults && (
            <SearchDropdown
              flights={searchResults?.flights ?? []}
              fetching={searchFetching}
              onSelect={(ident) => {
                setQuery('')
                setSearching(false)
                navigate(`/flight/${ident}`)
              }}
            />
          )}
        </form>
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left — flights + events */}
        <div className="lg:col-span-3 space-y-6">
          {/* Active flights */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-2">
                <Radio className="size-3.5 text-emerald-500" />
                Live Flights
              </h2>
              {activeFlights && (
                <span className="text-xs text-muted-foreground">{activeFlights.length} tracked</span>
              )}
            </div>
            {activeFetching ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                {Array.from({ length: 9 }).map((_, i) => (
                  <Skeleton key={i} className="h-24 rounded-lg" />
                ))}
              </div>
            ) : activeFlights?.length ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                {activeFlights.map((f) => (
                  <FlightCard key={f.ident} flight={f} />
                ))}
              </div>
            ) : (
              <EmptyState icon={<Plane className="size-8" />} message="No active flights right now" />
            )}
          </section>

          {/* Events */}
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
              Recent Events
            </h2>
            <EventFeed events={events ?? []} />
          </section>
        </div>

        {/* Right — airport risk */}
        <aside className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Airport Conditions
          </h2>
          {airports?.length ? (
            airports.slice(0, 15).map((apt) => (
              <AirportRiskCard key={apt.icao} airport={apt} />
            ))
          ) : (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-14 rounded-lg" />
              ))}
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}

/* ── Search dropdown ────────────────────────────────────────────────── */
function SearchDropdown({
  flights,
  fetching,
  onSelect,
}: {
  flights: Awaited<ReturnType<typeof searchFlights>>['flights']
  fetching: boolean
  onSelect: (ident: string) => void
}) {
  return (
    <div className="absolute top-full left-0 right-0 mt-1 bg-popover border border-border rounded-lg shadow-lg z-50 overflow-hidden">
      {fetching ? (
        <div className="p-3 space-y-2">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-9" />)}
        </div>
      ) : flights.length === 0 ? (
        <p className="p-4 text-sm text-muted-foreground text-center">No flights found</p>
      ) : (
        <ul>
          {flights.map((f) => (
            <li key={f.ident}>
              <button
                type="button"
                onMouseDown={() => onSelect(f.ident)}
                className="w-full flex items-center justify-between px-4 py-2.5 text-sm hover:bg-accent transition-colors text-left"
              >
                <div className="flex items-center gap-2">
                  <Plane className="size-3.5 text-muted-foreground shrink-0" />
                  <span className="font-medium">{f.ident}</span>
                  {f.origin && f.destination && (
                    <span className="text-muted-foreground">
                      {f.origin} → {f.destination}
                    </span>
                  )}
                </div>
                <FlightStatusBadge status={f.status} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/* ── Airport risk card ──────────────────────────────────────────────── */
function AirportRiskCard({ airport }: { airport: AirportRisk }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-card hover:bg-accent/50 transition-colors cursor-default">
      <div className="min-w-0">
        <p className="font-mono text-sm font-semibold">{airport.iata ?? airport.icao}</p>
        <p className="text-xs text-muted-foreground truncate">{airport.name}</p>
      </div>
      <AirportRiskBadge category={airport.category} />
    </div>
  )
}

/* ── Flight status badge ─────────────────────────────────────────────── */
export function FlightStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    active: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20',
    landed: 'bg-zinc-500/10 text-zinc-500 border-zinc-500/20',
    scheduled: 'bg-sky-500/10 text-sky-600 border-sky-500/20',
    cancelled: 'bg-red-500/10 text-red-600 border-red-500/20',
  }
  return (
    <Badge
      variant="outline"
      className={cn('text-[10px] px-1.5 capitalize', map[status?.toLowerCase()] ?? '')}
    >
      {status ?? 'unknown'}
    </Badge>
  )
}

/* ── Empty state ─────────────────────────────────────────────────────── */
function EmptyState({ icon, message }: { icon: React.ReactNode; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-3">
      <div className="opacity-30">{icon}</div>
      <p className="text-sm">{message}</p>
    </div>
  )
}

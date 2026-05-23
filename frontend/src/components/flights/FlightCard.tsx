import { Link } from 'react-router-dom'
import { ArrowRight, Gauge, MoveUp } from 'lucide-react'
import type { FlightSummary } from '@/api/flights'
import { FlightStatusBadge } from '@/pages/IndexPage'

export default function FlightCard({ flight }: { flight: FlightSummary }) {
  return (
    <Link
      to={`/flight/${flight.ident}`}
      className="block p-4 rounded-lg border border-border bg-card hover:border-primary/40 hover:shadow-md transition-all group"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-mono font-semibold text-sm truncate group-hover:text-primary transition-colors">
            {flight.ident}
          </p>
          {flight.origin && flight.destination ? (
            <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
              <span>{flight.origin}</span>
              <ArrowRight className="size-3 shrink-0" />
              <span>{flight.destination}</span>
            </p>
          ) : null}
        </div>
        <FlightStatusBadge status={flight.status} />
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
        {flight.altitude != null && (
          <span className="flex items-center gap-1">
            <MoveUp className="size-3" />
            {(flight.altitude / 100).toFixed(0)}FL
          </span>
        )}
        {flight.ground_speed != null && (
          <span className="flex items-center gap-1">
            <Gauge className="size-3" />
            {flight.ground_speed} kt
          </span>
        )}
        {flight.aircraft_type && (
          <span className="font-mono ml-auto">{flight.aircraft_type}</span>
        )}
      </div>
    </Link>
  )
}

import { lazy, Suspense } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, Clock, Gauge, MoveUp, MapPin, AlarmClock } from 'lucide-react'
import { format } from 'date-fns'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { getFlightDetail } from '@/api/flights'
import { FlightStatusBadge } from './IndexPage'
import { cn } from '@/lib/utils'

const FlightMap = lazy(() => import('@/components/map/FlightMap'))

export default function FlightDetailPage() {
  const { ident } = useParams<{ ident: string }>()

  const { data: flight, isLoading, isError } = useQuery({
    queryKey: ['flight', ident],
    queryFn: () => getFlightDetail(ident!),
    enabled: !!ident,
    refetchInterval: 15_000,
  })

  if (isLoading) return <FlightDetailSkeleton />
  if (isError || !flight) {
    return (
      <div className="text-center py-24 space-y-2">
        <p className="text-lg font-semibold">Flight not found</p>
        <p className="text-sm text-muted-foreground">{ident}</p>
        <Link to="/" className="text-sm text-primary hover:underline inline-flex items-center gap-1">
          <ArrowLeft className="size-3.5" /> Back to live
        </Link>
      </div>
    )
  }

  const fmtTime = (ts: string | null) =>
    ts ? format(new Date(ts), 'HH:mm') : '—'

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link to="/" className="hover:text-foreground transition-colors">Live</Link>
        <span>/</span>
        <span className="text-foreground font-medium">{flight.ident}</span>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold font-mono">{flight.ident}</h1>
            <FlightStatusBadge status={flight.status} />
            {flight.aircraft_type && (
              <Badge variant="outline" className="font-mono">{flight.aircraft_type}</Badge>
            )}
          </div>
          {flight.origin && flight.destination && (
            <p className="text-muted-foreground mt-1 flex items-center gap-2">
              <span>{flight.origin}</span>
              <ArrowRight className="size-4" />
              <span>{flight.destination}</span>
            </p>
          )}
        </div>
        <div className="flex gap-4 text-sm text-muted-foreground">
          {flight.departure_time && (
            <Stat icon={<Clock className="size-4" />} label="Depart" value={fmtTime(flight.departure_time)} />
          )}
          {flight.arrival_time && (
            <Stat icon={<Clock className="size-4" />} label="Arrive" value={fmtTime(flight.arrival_time)} />
          )}
        </div>
      </div>

      <Separator />

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left col */}
        <div className="lg:col-span-2 space-y-4">
          {/* Map placeholder */}
          <Card className="overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <MapPin className="size-4" /> Route Map
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Suspense fallback={<div className="h-72 bg-muted animate-pulse rounded-b-lg" />}>
                <FlightMap flight={flight} className="h-72 w-full" />
              </Suspense>
            </CardContent>
          </Card>

          {/* Position */}
          {(flight.latitude != null || flight.altitude != null || flight.ground_speed != null) && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Current Position</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-3 gap-4">
                {flight.latitude != null && flight.longitude != null && (
                  <Stat
                    icon={<MapPin className="size-4" />}
                    label="Position"
                    value={`${flight.latitude.toFixed(3)}, ${flight.longitude.toFixed(3)}`}
                  />
                )}
                {flight.altitude != null && (
                  <Stat
                    icon={<MoveUp className="size-4" />}
                    label="Altitude"
                    value={`FL${(flight.altitude / 100).toFixed(0)}`}
                  />
                )}
                {flight.ground_speed != null && (
                  <Stat
                    icon={<Gauge className="size-4" />}
                    label="Ground Speed"
                    value={`${flight.ground_speed} kt`}
                  />
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right col */}
        <div className="space-y-4">
          {/* TBFM metering */}
          {flight.tbfm && (
            <Card className={cn(flight.tbfm.scheduled_time ? 'border-amber-500/30' : '')}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <AlarmClock className="size-4 text-amber-500" />
                  TBFM Metering
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {flight.tbfm.apt && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Metering Fix</span>
                    <span className="font-mono font-medium">{flight.tbfm.apt}</span>
                  </div>
                )}
                {flight.tbfm.scheduled_time && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Scheduled Time</span>
                    <span className="font-mono font-medium">
                      {format(new Date(flight.tbfm.scheduled_time), 'HH:mm:ss')}
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Track history */}
          {flight.track?.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Track History</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="max-h-64 overflow-y-auto space-y-1">
                  {[...flight.track].reverse().map((pt, i) => (
                    <div key={i} className="flex justify-between text-xs text-muted-foreground py-1 border-b border-border last:border-0">
                      <span>{format(new Date(pt.ts), 'HH:mm:ss')}</span>
                      <span>FL{(pt.alt / 100).toFixed(0)}</span>
                      <span className="font-mono">{pt.lat.toFixed(2)}, {pt.lon.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-muted-foreground flex items-center gap-1">
        {icon}
        {label}
      </span>
      <span className="font-medium text-sm">{value}</span>
    </div>
  )
}

function FlightDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-5 w-32" />
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-4 w-28" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>
      <Skeleton className="h-px" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <Skeleton className="h-80 rounded-lg" />
          <Skeleton className="h-32 rounded-lg" />
        </div>
        <div className="space-y-4">
          <Skeleton className="h-40 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
        </div>
      </div>
    </div>
  )
}

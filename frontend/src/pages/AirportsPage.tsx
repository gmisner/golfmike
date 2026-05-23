import { useQuery } from '@tanstack/react-query'
import { Wind, Eye, Cloud } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { getAirportList } from '@/api/airports'
import AirportRiskBadge from '@/components/airports/AirportRiskBadge'

export default function AirportsPage() {
  const { data: airports, isLoading } = useQuery({
    queryKey: ['airport-list'],
    queryFn: getAirportList,
    refetchInterval: 60_000,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Airport Conditions</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Live METAR-based flight category for tracked airports.
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="h-36 rounded-lg" />
          ))}
        </div>
      ) : airports?.length ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {airports.map((apt) => (
            <Card key={apt.icao} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-1">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-mono">{apt.iata ?? apt.icao}</CardTitle>
                  <AirportRiskBadge category={apt.category} />
                </div>
                <p className="text-xs text-muted-foreground truncate">{apt.name}</p>
              </CardHeader>
              <CardContent className="pt-2 space-y-2 text-sm">
                <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground">
                  {apt.ceiling != null && (
                    <div className="flex flex-col gap-0.5">
                      <span className="flex items-center gap-1"><Cloud className="size-3" />Ceiling</span>
                      <span className="text-foreground font-medium">{apt.ceiling} ft</span>
                    </div>
                  )}
                  {apt.visibility != null && (
                    <div className="flex flex-col gap-0.5">
                      <span className="flex items-center gap-1"><Eye className="size-3" />Vis</span>
                      <span className="text-foreground font-medium">{apt.visibility} sm</span>
                    </div>
                  )}
                  {apt.wind_speed != null && (
                    <div className="flex flex-col gap-0.5">
                      <span className="flex items-center gap-1"><Wind className="size-3" />Wind</span>
                      <span className="text-foreground font-medium">
                        {apt.wind_dir != null ? `${apt.wind_dir}° ` : ''}{apt.wind_speed} kt
                      </span>
                    </div>
                  )}
                </div>
                {apt.raw_metar && (
                  <p className="font-mono text-[10px] text-muted-foreground bg-muted rounded px-2 py-1 truncate">
                    {apt.raw_metar}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <p className="text-center py-16 text-muted-foreground text-sm">No airport data available</p>
      )}
    </div>
  )
}

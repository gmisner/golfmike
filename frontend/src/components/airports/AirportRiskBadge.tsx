import { cn } from '@/lib/utils'
import type { AirportRisk } from '@/api/airports'

const STYLES: Record<AirportRisk['category'], string> = {
  VFR:     'bg-emerald-500/10 text-emerald-600 border-emerald-500/30',
  MVFR:    'bg-sky-500/10 text-sky-600 border-sky-500/30',
  IFR:     'bg-red-500/10 text-red-600 border-red-500/30',
  LIFR:    'bg-violet-500/10 text-violet-600 border-violet-500/30',
  UNKNOWN: 'bg-muted text-muted-foreground border-border',
}

export default function AirportRiskBadge({ category }: { category: AirportRisk['category'] }) {
  return (
    <span
      className={cn(
        'text-[10px] font-mono font-bold px-2 py-0.5 rounded border shrink-0',
        STYLES[category],
      )}
    >
      {category}
    </span>
  )
}

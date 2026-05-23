import { Link } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { cn } from '@/lib/utils'

interface Event {
  id: number
  event_type: string
  ident: string
  airport: string | null
  ts: string
  message: string
}

const TYPE_STYLES: Record<string, string> = {
  departed:  'bg-sky-500/10 text-sky-600 border-sky-500/20',
  arrived:   'bg-emerald-500/10 text-emerald-600 border-emerald-500/20',
  cancelled: 'bg-red-500/10 text-red-600 border-red-500/20',
  diverted:  'bg-amber-500/10 text-amber-600 border-amber-500/20',
  filed:     'bg-violet-500/10 text-violet-600 border-violet-500/20',
}

export default function EventFeed({ events }: { events: Event[] }) {
  if (!events.length) {
    return <p className="text-sm text-muted-foreground py-4 text-center">No recent events</p>
  }

  return (
    <div className="divide-y divide-border border border-border rounded-lg overflow-hidden">
      {events.map((ev) => (
        <div key={ev.id} className="flex items-center gap-3 px-4 py-3 bg-card hover:bg-accent/40 transition-colors">
          {/* Type chip */}
          <span
            className={cn(
              'shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded border capitalize',
              TYPE_STYLES[ev.event_type?.toLowerCase()] ?? 'bg-muted text-muted-foreground border-border',
            )}
          >
            {ev.event_type}
          </span>

          {/* Ident */}
          <Link
            to={`/flight/${ev.ident}`}
            className="font-mono text-sm font-semibold hover:text-primary transition-colors shrink-0"
          >
            {ev.ident}
          </Link>

          {/* Message */}
          <p className="text-sm text-muted-foreground truncate flex-1">{ev.message}</p>

          {/* Time */}
          <time className="text-xs text-muted-foreground shrink-0">
            {formatDistanceToNow(new Date(ev.ts), { addSuffix: true })}
          </time>
        </div>
      ))}
    </div>
  )
}

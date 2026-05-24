import { Star } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { useWatchlist } from '@/hooks/useWatchlist'

interface Props {
  aircraftId: string
  /** 'icon' = just the star, 'full' = star + label text */
  variant?: 'icon' | 'full'
  className?: string
}

export default function WatchButton({ aircraftId, variant = 'icon', className }: Props) {
  const { isAuthenticated } = useAuth()
  const { isWatching, watchlistIdFor, add, remove } = useWatchlist()

  const watching = isWatching(aircraftId)
  const wlId     = watchlistIdFor(aircraftId)
  const pending  = add.isPending || remove.isPending

  if (!isAuthenticated) {
    if (variant === 'icon') return null
    return (
      <Link
        to="/login"
        className={cn(
          'flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors',
          className,
        )}
      >
        <Star className="size-3.5" />
        Sign in to watch
      </Link>
    )
  }

  const toggle = () => {
    if (watching && wlId != null) {
      remove.mutate(wlId)
    } else {
      add.mutate({ aircraft_id: aircraftId })
    }
  }

  if (variant === 'full') {
    return (
      <button
        onClick={toggle}
        disabled={pending}
        className={cn(
          'flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-md border transition-colors',
          watching
            ? 'border-amber-400/40 bg-amber-400/10 text-amber-500 hover:bg-amber-400/20'
            : 'border-border bg-card text-muted-foreground hover:text-foreground hover:border-primary/40',
          pending && 'opacity-50 cursor-not-allowed',
          className,
        )}
      >
        <Star className={cn('size-4', watching && 'fill-amber-400 text-amber-400')} />
        {watching ? 'Watching' : 'Watch'}
      </button>
    )
  }

  return (
    <button
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); toggle() }}
      disabled={pending}
      aria-label={watching ? 'Remove from watchlist' : 'Add to watchlist'}
      className={cn(
        'p-1 rounded transition-colors',
        watching
          ? 'text-amber-400 hover:text-amber-300'
          : 'text-muted-foreground hover:text-foreground',
        pending && 'opacity-50 cursor-not-allowed',
        className,
      )}
    >
      <Star className={cn('size-3.5', watching && 'fill-amber-400')} />
    </button>
  )
}

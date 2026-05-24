import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Star, Plus, Trash2, Pencil, Check, X, ArrowRight, Plane } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { useWatchlist } from '@/hooks/useWatchlist'
import { FlightStatusBadge } from './IndexPage'
import type { WatchlistItem } from '@/api/watchlist'

export default function WatchlistPage() {
  const { isAuthenticated } = useAuth()
  const { items, flights, isLoading, flightsLoading, add, remove, update } = useWatchlist()
  const [addInput, setAddInput]   = useState('')
  const [addLabel, setAddLabel]   = useState('')
  const [showAdd, setShowAdd]     = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editLabel, setEditLabel] = useState('')

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4 text-center">
        <Star className="size-10 text-muted-foreground opacity-30" />
        <h2 className="text-lg font-semibold">Sign in to use your watchlist</h2>
        <p className="text-sm text-muted-foreground max-w-xs">
          Save tail numbers and callsigns to track them across sessions and get notified of events.
        </p>
        <div className="flex gap-2">
          <Link to="/login"><Button variant="outline">Sign in</Button></Link>
          <Link to="/register"><Button>Create account</Button></Link>
        </div>
      </div>
    )
  }

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    const id = addInput.trim().toUpperCase()
    if (!id) return
    add.mutate(
      { aircraft_id: id, label: addLabel.trim() || undefined },
      {
        onSuccess: () => {
          setAddInput('')
          setAddLabel('')
          setShowAdd(false)
        },
      },
    )
  }

  const startEdit = (item: WatchlistItem) => {
    setEditingId(item.id)
    setEditLabel(item.label ?? '')
  }

  const saveEdit = (id: number) => {
    update.mutate(
      { id, updates: { label: editLabel.trim() || null } },
      { onSuccess: () => setEditingId(null) },
    )
  }

  // Build a flight map keyed by aircraft_id for quick lookup
  const flightMap = Object.fromEntries(flights.map((f) => [f.ident, f]))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-2">
            <Star className="size-6 text-amber-400 fill-amber-400" />
            Watchlist
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {items.length} aircraft saved
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => setShowAdd((s) => !s)}
          className="gap-1.5"
        >
          <Plus className="size-4" />
          Add aircraft
        </Button>
      </div>

      {/* Add form */}
      {showAdd && (
        <form
          onSubmit={handleAdd}
          className="flex gap-2 p-4 rounded-lg border border-border bg-card"
        >
          <Input
            value={addInput}
            onChange={(e) => setAddInput(e.target.value)}
            placeholder="Tail or callsign (e.g. N123AB, DAL123)"
            className="font-mono"
            autoFocus
          />
          <Input
            value={addLabel}
            onChange={(e) => setAddLabel(e.target.value)}
            placeholder="Label (optional)"
            className="max-w-40"
          />
          <Button type="submit" disabled={add.isPending || !addInput.trim()}>
            {add.isPending ? 'Adding…' : 'Add'}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => { setShowAdd(false); setAddInput(''); setAddLabel('') }}
          >
            Cancel
          </Button>
        </form>
      )}

      {add.isError && (
        <p className="text-sm text-destructive">
          {(add.error as Error)?.message ?? 'Failed to add'}
        </p>
      )}

      {/* Loading */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-muted-foreground">
          <Star className="size-8 opacity-20" />
          <p className="text-sm">No aircraft yet — add a tail number or callsign above</p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => {
            const flight = flightMap[item.aircraft_id]
            const isEditing = editingId === item.id
            return (
              <div
                key={item.id}
                className="flex items-center gap-3 p-4 rounded-lg border border-border bg-card hover:border-primary/20 transition-colors"
              >
                {/* Aircraft ID + label */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Link
                      to={`/flight/${item.aircraft_id}`}
                      className="font-mono font-semibold text-sm hover:text-primary transition-colors"
                    >
                      {item.aircraft_id}
                    </Link>

                    {isEditing ? (
                      <div className="flex items-center gap-1">
                        <Input
                          value={editLabel}
                          onChange={(e) => setEditLabel(e.target.value)}
                          className="h-6 text-xs w-36"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveEdit(item.id)
                            if (e.key === 'Escape') setEditingId(null)
                          }}
                        />
                        <button onClick={() => saveEdit(item.id)} className="text-emerald-500 hover:text-emerald-400">
                          <Check className="size-3.5" />
                        </button>
                        <button onClick={() => setEditingId(null)} className="text-muted-foreground hover:text-foreground">
                          <X className="size-3.5" />
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => startEdit(item)}
                        className="group flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {item.label
                          ? <span>{item.label}</span>
                          : <span className="opacity-0 group-hover:opacity-60">add label</span>
                        }
                        <Pencil className="size-3 opacity-0 group-hover:opacity-60" />
                      </button>
                    )}
                  </div>

                  {/* Flight status */}
                  {flightsLoading ? (
                    <Skeleton className="h-3 w-40 mt-1.5" />
                  ) : flight ? (
                    <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                      <FlightStatusBadge status={flight.status} />
                      {flight.origin && flight.destination && (
                        <span className="flex items-center gap-1">
                          {flight.origin}
                          <ArrowRight className="size-3" />
                          {flight.destination}
                        </span>
                      )}
                      {flight.altitude != null && (
                        <span>FL{(flight.altitude / 100).toFixed(0)}</span>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                      <Plane className="size-3" />
                      No recent flight
                    </p>
                  )}
                </div>

                {/* Notification toggles */}
                <div className="hidden sm:flex items-center gap-1">
                  <NotifToggle
                    label="DEP"
                    active={item.notify_departure}
                    onToggle={() =>
                      update.mutate({ id: item.id, updates: { notify_departure: !item.notify_departure } })
                    }
                  />
                  <NotifToggle
                    label="ARR"
                    active={item.notify_arrival}
                    onToggle={() =>
                      update.mutate({ id: item.id, updates: { notify_arrival: !item.notify_arrival } })
                    }
                  />
                  <NotifToggle
                    label="FPL"
                    active={item.notify_filed}
                    onToggle={() =>
                      update.mutate({ id: item.id, updates: { notify_filed: !item.notify_filed } })
                    }
                  />
                </div>

                {/* Remove */}
                <button
                  onClick={() => remove.mutate(item.id)}
                  className="p-1.5 text-muted-foreground hover:text-destructive transition-colors rounded"
                  aria-label="Remove"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* Legend */}
      {items.length > 0 && (
        <p className="text-xs text-muted-foreground">
          <span className="font-medium">DEP</span> departure ·{' '}
          <span className="font-medium">ARR</span> arrival ·{' '}
          <span className="font-medium">FPL</span> flight plan filed — notifications coming soon
        </p>
      )}
    </div>
  )
}

function NotifToggle({
  label,
  active,
  onToggle,
}: {
  label: string
  active: boolean
  onToggle: () => void
}) {
  return (
    <button
      onClick={onToggle}
      className={cn(
        'text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border transition-colors',
        active
          ? 'bg-sky-500/10 text-sky-500 border-sky-500/30 hover:bg-sky-500/20'
          : 'bg-muted text-muted-foreground border-border hover:border-primary/30',
      )}
    >
      {label}
    </button>
  )
}

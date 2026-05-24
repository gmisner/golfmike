import { useState } from 'react'
import { Bell, BellOff, Plus, Trash2, ToggleLeft, ToggleRight, Smartphone } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useNotifications } from '@/hooks/useNotifications'

export default function NotificationSettings() {
  const {
    permission,
    pushSubscribed,
    channels,
    channelsLoading,
    enablePush,
    disablePush,
    addChannel,
    toggleChannel,
    deleteChannel,
  } = useNotifications()

  const [showAdd, setShowAdd]   = useState(false)
  const [label, setLabel]       = useState('')
  const [url, setUrl]           = useState('')

  const handleAddChannel = (e: React.FormEvent) => {
    e.preventDefault()
    if (!label.trim() || !url.trim()) return
    addChannel.mutate(
      { label: label.trim(), apprise_url: url.trim() },
      { onSuccess: () => { setLabel(''); setUrl(''); setShowAdd(false) } },
    )
  }

  return (
    <div className="space-y-6">
      {/* Browser push */}
      <section className="space-y-3">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <Bell className="size-4" /> Browser Notifications
        </h3>
        <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-card">
          <div>
            <p className="text-sm font-medium">
              {pushSubscribed ? 'Notifications enabled' : 'Notifications disabled'}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {permission === 'denied'
                ? 'Blocked by your browser — allow in site settings'
                : pushSubscribed
                ? 'You\'ll receive alerts even when the tab is closed'
                : 'Get departure, arrival, and filing alerts in your browser'}
            </p>
          </div>
          {pushSubscribed ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => disablePush.mutate()}
              disabled={disablePush.isPending}
              className="gap-1.5 shrink-0"
            >
              <BellOff className="size-4" />
              Disable
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={() => enablePush.mutate()}
              disabled={enablePush.isPending || permission === 'denied'}
              className="gap-1.5 shrink-0"
            >
              <Bell className="size-4" />
              {enablePush.isPending ? 'Enabling…' : 'Enable'}
            </Button>
          )}
        </div>
        {enablePush.isError && (
          <p className="text-xs text-destructive">{(enablePush.error as Error)?.message}</p>
        )}
      </section>

      {/* Apprise channels */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Smartphone className="size-4" /> Notification Channels
          </h3>
          <Button variant="outline" size="sm" onClick={() => setShowAdd((s) => !s)} className="gap-1.5">
            <Plus className="size-4" />
            Add channel
          </Button>
        </div>

        <p className="text-xs text-muted-foreground">
          Connect SMS, Telegram, ntfy, Discord, Slack, and{' '}
          <a
            href="https://github.com/caronc/apprise/wiki"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-foreground"
          >
            50+ other services
          </a>{' '}
          via Apprise URLs.
        </p>

        {showAdd && (
          <form onSubmit={handleAddChannel} className="space-y-2 p-4 rounded-lg border border-border bg-card">
            <Input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder='Label (e.g. "My Phone")'
              autoFocus
            />
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Apprise URL (e.g. ntfy://mytopic or tgram://bottoken/chatid)"
              className="font-mono text-xs"
            />
            <div className="flex gap-2">
              <Button type="submit" size="sm" disabled={addChannel.isPending || !label || !url}>
                {addChannel.isPending ? 'Adding…' : 'Add'}
              </Button>
              <Button type="button" variant="outline" size="sm"
                onClick={() => { setShowAdd(false); setLabel(''); setUrl('') }}>
                Cancel
              </Button>
            </div>
            {addChannel.isError && (
              <p className="text-xs text-destructive">{(addChannel.error as Error)?.message}</p>
            )}
            <div className="text-xs text-muted-foreground space-y-1 pt-1 border-t border-border">
              <p className="font-medium">Common formats:</p>
              <p><code className="bg-muted px-1 rounded">ntfy://mytopic</code> — ntfy.sh</p>
              <p><code className="bg-muted px-1 rounded">tgram://bottoken/chatid</code> — Telegram</p>
              <p><code className="bg-muted px-1 rounded">twilio://acct:token@+15558675309/+15551234567</code> — SMS</p>
            </div>
          </form>
        )}

        {channelsLoading ? (
          <div className="space-y-2">
            {[1, 2].map((i) => <Skeleton key={i} className="h-14 rounded-lg" />)}
          </div>
        ) : channels.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No channels yet — add one above
          </p>
        ) : (
          <div className="space-y-2">
            {channels.map((ch) => (
              <div key={ch.id} className="flex items-center gap-3 p-3 rounded-lg border border-border bg-card">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{ch.label}</p>
                  <p className="text-xs text-muted-foreground font-mono truncate">{ch.apprise_url}</p>
                </div>
                <button
                  onClick={() => toggleChannel.mutate({ id: ch.id, enabled: !ch.enabled })}
                  className={cn(
                    'shrink-0 transition-colors',
                    ch.enabled ? 'text-sky-500 hover:text-sky-400' : 'text-muted-foreground hover:text-foreground',
                  )}
                  aria-label={ch.enabled ? 'Disable' : 'Enable'}
                >
                  {ch.enabled
                    ? <ToggleRight className="size-6" />
                    : <ToggleLeft className="size-6" />}
                </button>
                <button
                  onClick={() => deleteChannel.mutate(ch.id)}
                  className="shrink-0 text-muted-foreground hover:text-destructive transition-colors"
                  aria-label="Delete"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

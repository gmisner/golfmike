import { Bell, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function AlertsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Alerts</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Get notified when flights depart, land, or conditions change.
          </p>
        </div>
        <Button size="sm" disabled className="gap-1.5">
          <Plus className="size-4" />
          New Alert
        </Button>
      </div>

      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2 text-muted-foreground">
            <Bell className="size-5" />
            No alerts yet
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-1">
          <p>Alerts are coming in a future release.</p>
          <p>You'll be able to watch specific tail numbers, flights, and airports — and get notified via SMS, push, or in-app when events occur.</p>
        </CardContent>
      </Card>
    </div>
  )
}

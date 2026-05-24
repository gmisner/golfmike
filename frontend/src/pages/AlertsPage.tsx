import { Link } from 'react-router-dom'
import { Bell, Star } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { useAuth } from '@/hooks/useAuth'
import NotificationSettings from '@/components/notifications/NotificationSettings'

export default function AlertsPage() {
  const { isAuthenticated } = useAuth()

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <Bell className="size-6" /> Alerts & Notifications
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Get notified when watched aircraft depart, land, or file a flight plan.
        </p>
      </div>

      {!isAuthenticated ? (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle className="text-base text-muted-foreground">Sign in to use alerts</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-3">
            <p>Create an account to save aircraft to your watchlist and receive notifications via browser push, SMS, Telegram, and more.</p>
            <div className="flex gap-2">
              <Link to="/login" className="text-primary hover:underline font-medium">Sign in</Link>
              <span>·</span>
              <Link to="/register" className="text-primary hover:underline font-medium">Create account</Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* How it works */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Star className="size-4 text-amber-400 fill-amber-400" />
                How it works
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-1">
              <p>
                Add aircraft to your{' '}
                <Link to="/watchlist" className="text-primary hover:underline">watchlist</Link>
                {' '}and toggle DEP / ARR / FPL on each one. Notifications fire within 60 seconds of the event.
              </p>
            </CardContent>
          </Card>

          <Separator />

          {/* Notification settings */}
          <NotificationSettings />
        </>
      )}
    </div>
  )
}

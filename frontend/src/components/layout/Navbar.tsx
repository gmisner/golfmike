import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { Plane, Bell, Map, Activity, Sun, Moon, User, LogOut, ChevronDown, Star } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useLiveStatus } from '@/hooks/useLiveStatus'
import { useTheme } from '@/hooks/useTheme'
import { useAuth } from '@/hooks/useAuth'

export default function Navbar() {
  const { connected, flightCount } = useLiveStatus()
  const { theme, toggle } = useTheme()
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 bg-zinc-950 border-b border-zinc-800 text-zinc-100">
      <div className="container mx-auto px-4 max-w-7xl h-14 flex items-center justify-between">
        {/* Logo — goes to /live (app home) from within the app layout */}
        <Link to="/live" className="flex items-center gap-2 font-semibold text-lg tracking-tight hover:text-white transition-colors">
          <Plane className="size-5 text-sky-400" />
          <span>GolfMike</span>
        </Link>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
          <NavItem to="/live" icon={<Activity className="size-4" />} label="Live" />
          <NavItem to="/airports" icon={<Map className="size-4" />} label="Airports" />
          <NavItem to="/alerts" icon={<Bell className="size-4" />} label="Alerts" />
          {user && (
            <NavItem to="/watchlist" icon={<Star className="size-4" />} label="Watchlist" />
          )}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-2">
          {/* Live indicator */}
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-zinc-400 mr-1">
            <span className={cn('size-2 rounded-full', connected ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-600')} />
            {connected
              ? <span><span className="text-emerald-400 font-medium">{flightCount}</span> live</span>
              : <span>offline</span>}
          </div>

          {/* Theme toggle */}
          <button
            onClick={toggle}
            aria-label="Toggle theme"
            className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
          >
            {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>

          {/* Auth */}
          {user ? (
            <div className="relative">
              <button
                onClick={() => setMenuOpen((o) => !o)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors"
              >
                <User className="size-4" />
                <span className="hidden sm:inline max-w-28 truncate">
                  {user.display_name ?? user.email.split('@')[0]}
                </span>
                <ChevronDown className="size-3.5 text-zinc-500" />
              </button>
              {menuOpen && (
                <div
                  className="absolute right-0 mt-1 w-48 bg-popover border border-border rounded-lg shadow-lg overflow-hidden z-50"
                  onBlur={() => setMenuOpen(false)}
                >
                  <div className="px-3 py-2 border-b border-border">
                    <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                  </div>
                  <button
                    onClick={() => { setMenuOpen(false); logout.mutate() }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                  >
                    <LogOut className="size-4" />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-1">
              <Link
                to="/login"
                className="px-3 py-1.5 text-sm text-zinc-400 hover:text-white transition-colors rounded-md hover:bg-zinc-800"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="px-3 py-1.5 text-sm font-medium bg-sky-500 hover:bg-sky-400 text-white rounded-md transition-colors"
              >
                Sign up
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

function NavItem({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        cn(
          'flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors',
          isActive
            ? 'bg-zinc-800 text-white'
            : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50',
        )
      }
    >
      {icon}
      {label}
    </NavLink>
  )
}

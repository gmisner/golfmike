import { Link, NavLink } from 'react-router-dom'
import { Plane, Bell, Map, Activity, Sun, Moon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useLiveStatus } from '@/hooks/useLiveStatus'
import { useTheme } from '@/hooks/useTheme'

export default function Navbar() {
  const { connected, flightCount } = useLiveStatus()
  const { theme, toggle } = useTheme()

  return (
    <header className="sticky top-0 z-50 bg-zinc-950 border-b border-zinc-800 text-zinc-100">
      <div className="container mx-auto px-4 max-w-7xl h-14 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 font-semibold text-lg tracking-tight hover:text-white transition-colors">
          <Plane className="size-5 text-sky-400" />
          <span>GolfMike</span>
        </Link>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
          <NavItem to="/" icon={<Activity className="size-4" />} label="Live" />
          <NavItem to="/airports" icon={<Map className="size-4" />} label="Airports" />
          <NavItem to="/alerts" icon={<Bell className="size-4" />} label="Alerts" />
        </nav>

        {/* Right side: live indicator + theme toggle */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-zinc-400">
            <span
              className={cn(
                'size-2 rounded-full',
                connected ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-600',
              )}
            />
            {connected ? (
              <span>
                <span className="text-emerald-400 font-medium">{flightCount}</span> live
              </span>
            ) : (
              <span>offline</span>
            )}
          </div>
          <button
            onClick={toggle}
            aria-label="Toggle theme"
            className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
          >
            {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
        </div>
      </div>
    </header>
  )
}

function NavItem({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
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

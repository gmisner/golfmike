import { Link } from 'react-router-dom'
import { useInView } from 'react-intersection-observer'
import { Plane, Bell, Map, Star, Radio, Zap, Shield, ChevronRight, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useLiveStatus } from '@/hooks/useLiveStatus'

/* ── Fade-in wrapper ─────────────────────────────────────────────────── */
function FadeIn({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode
  className?: string
  delay?: number
}) {
  const { ref, inView } = useInView({ triggerOnce: true, threshold: 0.1 })
  return (
    <div
      ref={ref}
      className={cn('transition-all duration-700', className, inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6')}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  )
}

/* ── Main page ───────────────────────────────────────────────────────── */
export default function LandingPage() {
  const { connected, flightCount } = useLiveStatus()

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">

      {/* ── Top nav ── */}
      <header className="sticky top-0 z-50 bg-zinc-950/80 backdrop-blur border-b border-zinc-800/60">
        <div className="container mx-auto px-4 max-w-6xl h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 font-semibold text-lg tracking-tight hover:text-white transition-colors">
            <Plane className="size-5 text-sky-400" />
            GolfMike
          </Link>
          <div className="flex items-center gap-2">
            <Link
              to="/live"
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-sm text-zinc-400 hover:text-white transition-colors rounded-md hover:bg-zinc-800"
            >
              <Radio className="size-3.5 text-emerald-400" />
              Live
            </Link>
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
              Sign up free
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="relative overflow-hidden">
        {/* Background grid */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
            backgroundSize: '60px 60px',
          }}
        />
        {/* Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative container mx-auto px-4 max-w-6xl pt-24 pb-20 text-center">
          {/* Live badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-900 border border-zinc-700 text-xs text-zinc-400 mb-8">
            <span className={cn('size-1.5 rounded-full', connected ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-600')} />
            {connected
              ? <><span className="text-emerald-400 font-medium">{flightCount.toLocaleString()}</span> flights tracked live right now</>
              : 'Connecting to live feed…'}
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-white leading-tight mb-6">
            Aviation intelligence,<br />
            <span className="text-sky-400">purpose-built</span> for GA.
          </h1>
          <p className="text-lg text-zinc-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Live flight tracking powered by FAA SWIM — ADS-B positions, FDPS flight plans,
            TBFM metering times, and weather risk, all in one place.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/register"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-sky-500 hover:bg-sky-400 text-white font-semibold transition-colors shadow-lg shadow-sky-500/20"
            >
              Get started free
              <ChevronRight className="size-4" />
            </Link>
            <Link
              to="/live"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium transition-colors"
            >
              <Radio className="size-4 text-emerald-400" />
              View live feed
            </Link>
          </div>
        </div>
      </section>

      {/* ── Stats bar ── */}
      <div className="border-y border-zinc-800 bg-zinc-900/50">
        <div className="container mx-auto px-4 max-w-6xl py-6 grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
          {[
            { label: 'Data source', value: 'FAA SWIM' },
            { label: 'Update interval', value: '< 60 s' },
            { label: 'Notification channels', value: '50+' },
            { label: 'Coverage', value: 'CONUS' },
          ].map((stat) => (
            <div key={stat.label}>
              <p className="text-2xl font-bold text-white">{stat.value}</p>
              <p className="text-xs text-zinc-500 mt-0.5">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Features ── */}
      <section className="container mx-auto px-4 max-w-6xl py-24">
        <FadeIn className="text-center mb-16">
          <h2 className="text-3xl font-bold text-white mb-3">Everything you need to stay informed</h2>
          <p className="text-zinc-400 max-w-xl mx-auto">
            One platform combining live traffic data, smart alerts, and weather risk so you never miss a flight.
          </p>
        </FadeIn>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((f, i) => (
            <FadeIn key={f.title} delay={i * 80}>
              <div className="h-full p-6 rounded-xl bg-zinc-900 border border-zinc-800 hover:border-zinc-700 transition-colors">
                <div className={cn('inline-flex p-2.5 rounded-lg mb-4', f.iconBg)}>
                  <f.Icon className={cn('size-5', f.iconColor)} />
                </div>
                <h3 className="font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-zinc-400 leading-relaxed">{f.description}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="border-t border-zinc-800 bg-zinc-900/30">
        <div className="container mx-auto px-4 max-w-6xl py-24">
          <FadeIn className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-3">Up and running in minutes</h2>
            <p className="text-zinc-400">No hardware, no API keys, no configuration required.</p>
          </FadeIn>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {steps.map((step, i) => (
              <FadeIn key={step.title} delay={i * 100} className="text-center">
                <div className="inline-flex items-center justify-center size-10 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-400 font-bold text-sm mb-5">
                  {i + 1}
                </div>
                <h3 className="font-semibold text-white mb-2">{step.title}</h3>
                <p className="text-sm text-zinc-400 leading-relaxed">{step.description}</p>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── Notifications showcase ── */}
      <section className="container mx-auto px-4 max-w-6xl py-24">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <FadeIn>
            <div className="inline-flex items-center gap-2 text-xs text-sky-400 font-medium uppercase tracking-wider mb-4">
              <Bell className="size-3.5" />
              Smart Alerts
            </div>
            <h2 className="text-3xl font-bold text-white mb-4 leading-snug">
              Get notified the moment<br />something happens
            </h2>
            <p className="text-zinc-400 mb-6 leading-relaxed">
              Watch any aircraft and receive push notifications for departures, arrivals,
              and flight plan filings — delivered within 60 seconds of the event.
            </p>
            <ul className="space-y-3">
              {notifBenefits.map((b) => (
                <li key={b} className="flex items-center gap-3 text-sm text-zinc-300">
                  <span className="shrink-0 size-5 rounded-full bg-sky-500/10 border border-sky-500/30 flex items-center justify-center">
                    <Check className="size-3 text-sky-400" />
                  </span>
                  {b}
                </li>
              ))}
            </ul>
          </FadeIn>

          <FadeIn delay={150}>
            <div className="space-y-3">
              {channelExamples.map((ch) => (
                <div key={ch.name} className="flex items-start gap-3 p-4 rounded-xl bg-zinc-900 border border-zinc-800">
                  <div className="shrink-0 size-9 rounded-lg bg-zinc-800 flex items-center justify-center text-lg">
                    {ch.emoji}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{ch.name}</p>
                    <p className="text-xs text-zinc-400 mt-0.5">{ch.desc}</p>
                    <code className="text-[11px] text-zinc-500 font-mono mt-1 block">{ch.url}</code>
                  </div>
                </div>
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="border-t border-zinc-800 bg-zinc-900/30">
        <FadeIn className="container mx-auto px-4 max-w-6xl py-24 text-center">
          <Plane className="size-10 text-sky-400 mx-auto mb-6" />
          <h2 className="text-3xl font-bold text-white mb-4">Ready to track your fleet?</h2>
          <p className="text-zinc-400 mb-8 max-w-md mx-auto">
            Free account, no credit card required. Start watching flights in under two minutes.
          </p>
          <Link
            to="/register"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-white font-semibold transition-colors shadow-lg shadow-sky-500/20"
          >
            Create free account
            <ChevronRight className="size-4" />
          </Link>
          <p className="mt-6 text-xs text-zinc-600">
            Already have an account?{' '}
            <Link to="/login" className="text-zinc-400 hover:text-white underline transition-colors">Sign in</Link>
          </p>
        </FadeIn>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-zinc-800/60 py-8">
        <div className="container mx-auto px-4 max-w-6xl flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-zinc-600">
          <div className="flex items-center gap-2">
            <Plane className="size-3.5 text-sky-400/60" />
            <span>GolfMike — FAA SWIM flight intelligence</span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/live" className="hover:text-zinc-400 transition-colors">Live</Link>
            <Link to="/airports" className="hover:text-zinc-400 transition-colors">Airports</Link>
            <Link to="/alerts" className="hover:text-zinc-400 transition-colors">Alerts</Link>
            <Link to="/register" className="hover:text-zinc-400 transition-colors">Sign up</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

/* ── Data ────────────────────────────────────────────────────────────── */
const features = [
  {
    title: 'Live Flight Tracking',
    description: 'ADS-B positions updated continuously from FAA SWIM. Search by tail number, flight number, or route.',
    Icon: Radio,
    iconBg: 'bg-emerald-500/10',
    iconColor: 'text-emerald-400',
  },
  {
    title: 'Push Notifications',
    description: 'Browser push alerts fire within 60 seconds of departure, arrival, or flight plan filing.',
    Icon: Bell,
    iconBg: 'bg-sky-500/10',
    iconColor: 'text-sky-400',
  },
  {
    title: 'Watchlist',
    description: 'Save up to 50 aircraft per account. Choose which events trigger alerts for each one.',
    Icon: Star,
    iconBg: 'bg-amber-500/10',
    iconColor: 'text-amber-400',
  },
  {
    title: 'Airport Conditions',
    description: 'At-a-glance risk categories for busy airports: metering, delay, and closure information.',
    Icon: Map,
    iconBg: 'bg-violet-500/10',
    iconColor: 'text-violet-400',
  },
  {
    title: 'Multi-Channel Delivery',
    description: 'Route alerts to SMS, Telegram, ntfy, Discord, Slack, and 50+ services via Apprise.',
    Icon: Zap,
    iconBg: 'bg-orange-500/10',
    iconColor: 'text-orange-400',
  },
  {
    title: 'TBFM Metering',
    description: 'See scheduled crossing and landing times from FAA TBFM — before delays become visible.',
    Icon: Shield,
    iconBg: 'bg-rose-500/10',
    iconColor: 'text-rose-400',
  },
]

const steps = [
  {
    title: 'Create your free account',
    description: 'Sign up with an email address. No credit card, no setup fee — just instant access to the live feed.',
  },
  {
    title: 'Add aircraft to your watchlist',
    description: 'Search any tail number and star it. Toggle departure, arrival, and flight-plan alerts per aircraft.',
  },
  {
    title: 'Receive real-time notifications',
    description: 'Browser push, SMS, Telegram — wherever you are, GolfMike finds you within 60 seconds of an event.',
  },
]

const notifBenefits = [
  'Departure alerts within 60 seconds of wheels-up',
  'Arrival notifications as soon as the aircraft lands',
  'Flight plan filing alerts before the flight even departs',
  'Browser push works even with the tab closed',
  'Route to any Apprise-compatible channel',
]

const channelExamples = [
  {
    emoji: '📱',
    name: 'ntfy (self-hosted or ntfy.sh)',
    desc: 'Free push notifications to any Android or iOS device',
    url: 'ntfy://mytopic',
  },
  {
    emoji: '✈️',
    name: 'Telegram',
    desc: 'Instant messages via your own bot',
    url: 'tgram://bottoken/chatid',
  },
  {
    emoji: '💬',
    name: 'SMS via Twilio',
    desc: 'Text messages to any phone number',
    url: 'twilio://acct:token@+15555550100/+15555550200',
  },
]

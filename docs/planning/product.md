# GolfMike — Product Decision Doc

## Vision

GolfMike is a flight tracking platform built on FAA SWIM data, designed for people who actually care about a specific aircraft — not the whole airspace. It started as a way for Gary's wife to know when he took off and landed; it's becoming the flight tracker that treats users like adults: no ads, clean data, useful notifications, and an accessible API for developers who want to build on the same live FAA feed.

---

## Target Users (in priority order)

1. **Consumer** — Pilots, families of pilots, aviation enthusiasts following specific aircraft. They want a watchlist, smart notifications, and a shareable link they can text to someone. This is the foundation; everything else depends on getting this right.

2. **Developer / Integrator** — Anyone who wants to build something on top of live FAA data without parsing XML soup. GolfMike offers clean JSON endpoints, API keys, and eventually an MCP server. Data includes things FlightAware doesn't expose to developers: TBFM metering, flow probability, raw SWIM-derived events.

3. **Ops / Professional** — Dispatch, GA FBOs, flight departments. Higher value per user but more complex requirements. Not a focus until consumer and developer tiers are solid.

---

## Free Tier

Free should be genuinely useful, not crippled.

- Search and view any flight (live position, route, filed plan, weather)
- Watchlist: up to 5 aircraft
- Basic notifications: departure and arrival alerts via browser push
- Shareable public track link (`/track/N560PB`)
- 90-day position history visible in UI
- API access: rate-limited, no key required for public endpoints (read-only, flight/position/weather data)

---

## Paid Tier(s)

Pricing philosophy: charge for depth and volume, not for basic utility. The free tier should not feel like a demo.

**What gets gated:**
- Watchlist beyond 5 aircraft
- Smart notifications (METAR + flight category + flow alerts + filed plan alerts)
- Historical track access beyond 90 days
- Notification delivery via SMS and Telegram (vs. browser push only on free)
- API key with higher rate limits
- Derived data endpoints: flow probability, delay intelligence, TBFM metering via API

Likely a single paid tier to start. No freemium upsell dark patterns — just a clear line between what the free tier includes and what paid unlocks.

---

## API Product

The API is a product in its own right, not an afterthought.

**What's exposed:**
- `/v1/flights/` — search, lookup by callsign or tail
- `/v1/flights/{id}/positions` — live track
- `/v1/flights/{id}/route` — filed route with waypoint overlay
- `/v1/airports/` — airport info, current METAR, flow status
- `/v1/weather/metar/{icao}` — current and recent METARs
- `/v1/tbfm/{airport}` — TBFM sequence, controlled times, TMA data (paid)
- `/v1/flow/` — flow probability, TMI alerts, delay intelligence (paid)
- Webhook support (Phase 2): `flight.filed`, `flight.departed`, `flight.arrived`, `flight.deviated`

**Free API:** Public read-only endpoints, rate-limited, no key required.

**Paid API:** Higher rate limits, TBFM/flow data, webhook subscriptions, API key management in user dashboard.

**MCP server (Phase 2):** Expose aviation data via MCP so AI assistants can query live flights, weather, and flow data directly. This is a natural fit for the data model and a differentiator — no one else is doing this with SWIM data.

---

## Notifications

Three tiers of notification richness, configurable per aircraft in the watchlist:

**Basic** — Departed / Arrived. That's it. (Free)

**Standard** — Departed / Arrived + current METAR at departure/arrival airport + flight category (VFR/MVFR/IFR/LIFR). (Paid)

**Smart** — Everything in Standard, plus:
- Filed flight plan alert (when a plan is filed for a watched aircraft)
- Flow/delay intelligence (TMI in effect, ground delay program, expected delay)
- TBFM metering (if aircraft is in a TMA sequence)
- Delivery via SMS or Telegram (not just browser push)

Notification channels: browser push (free) → SMS via Apprise (paid) → Telegram (paid, Phase 3) → email (TBD) → iOS push (Phase 3+)

---

## Account Model

- Email + password auth to start (Supabase Auth); Google/Apple OAuth added later
- Each registered user has a watchlist of tail numbers
- Watchlist entries are configurable: notification tier per aircraft, notification channel preferences
- Public shareable track link: `/track/{tail}` — no login required to view, shows live position and recent track
- Profile page: watchlist management, notification preferences, API key management (paid)

---

## Data Retention Policy

| Data type | Retention |
|---|---|
| Position tracks | 90 days rolling |
| Flight plans | 1 year |
| Flight events (departure, arrival) | 1 year |
| TBFM raw messages | 7 days |
| Derived / summarized data | Indefinite |
| Historical access beyond above | Paid feature |

Automated cleanup jobs enforce these limits. Historical data access (e.g., "show me every flight N560PB took in 2025") is a paid feature once we have enough history to make it valuable.

---

## What We Are NOT Building Yet

- **WhatsApp notifications** — Meta's approval process is not worth it right now
- **Full ops/professional dashboard** — Dispatch tools, fleet views, SLA monitoring, audit logs. This is a future product, not Phase 1 or 2
- **iOS app** — React Native is the plan, but it's Phase 3. Web-first for now
- **Historical data portal** — The data is accumulating; we're not building a query UI for it until there's enough of it and enough users who want it

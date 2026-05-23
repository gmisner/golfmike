# GolfMike — Phased Roadmap

---

## Phase 1 — Consumer Foundation

**Goal: Something real people can use and share.**

This phase turns GolfMike from a personal tool into a product a stranger could pick up, understand, and find genuinely useful. Every deliverable here is about core usability — not features, not monetization, not scale.

### Deliverables

**React Frontend Migration**
- Set up Vite + React + shadcn/ui + Tailwind in `/frontend/`
- Port all existing pages in order: index (flight search) → flight-detail → airports → flight-alerts
- Deprecate old Jinja templates as each page is replaced
- Leaflet map integration via react-leaflet (no map logic rewrite)

**User Accounts**
- Supabase Auth integration: email + password signup/login
- Flask JWT middleware for protected endpoints
- `users` table linked to Supabase UIDs
- Basic account page: profile, watchlist, notification preferences

**Aircraft Watchlists**
- `/v1/watchlist/` endpoints (CRUD)
- UI: add/remove tail numbers, configure notification tier per aircraft (basic / standard / smart)
- Free tier cap: 5 aircraft per account

**Shareable Public Track Link**
- `/track/{tail}` route — no login required
- Shows live position, recent track, aircraft info, current METAR
- Linkable and shareable (the "text your wife" use case)

**Basic Notifications**
- Browser push notifications via Web Push API
- SMS delivery via Apprise
- Departure and arrival events for watched aircraft (basic tier)
- Smart notification content: departure/arrival + current METAR + flight category (IFR/VFR/etc.)

**Data Retention Enforcement**
- Automated Celery cleanup jobs:
  - Delete position tracks older than 90 days
  - Delete TBFM raw messages older than 7 days
- Retention policy documented in UI (users understand what they're getting)

**Landing Page**
- Clean public-facing page explaining what GolfMike is
- Who it's for, what it does, how to sign up
- Not a marketing site — just clear and honest

---

## Phase 2 — Developer API

**Goal: Developers can build on GolfMike data.**

The SWIM data GolfMike is already ingesting is genuinely hard to get and harder to parse. Phase 2 makes it accessible. Clean JSON, API keys, documentation, and an MCP server. This also starts the monetization conversation.

### Deliverables

**API Key Issuance and Management**
- `/v1/api-keys/` endpoints: issue, list, revoke
- User dashboard: API key management UI
- Keys tied to user account and tier (free vs. paid rate limits)

**Public API Documentation**
- Full documentation for all existing `/v1/` endpoints
- Auth (API key header), rate limits, response schemas, example requests
- Hosted at `golfmike.app/docs` or similar

**Rate Limiting**
- Per-key rate limiting enforced at Flask middleware level
- Free tier: reasonable but limited (e.g., 100 req/min)
- Paid tier: higher limits
- Clear error responses when rate-limited

**MCP Server**
- MCP server exposing aviation data tools: flights, positions, weather, flow
- Lets AI assistants query live FAA data directly
- Endpoints to expose: flight lookup, position track, METAR, airport flow, TBFM metering
- This is a differentiator — document it prominently

**Simplified SWIM Data Endpoints**
- Clean JSON equivalents for TBFM data (no XML, no raw message parsing required)
- `/v1/tbfm/{airport}` — TMA sequence, controlled times, metering data
- `/v1/flow/` — flow probability, active TMIs, ground delay programs
- `/v1/flights/{id}/metering` — TBFM metering data for a specific flight

**Derived Data Endpoints**
- Flow probability score per airport (already partially computed)
- Delay intelligence: expected departure delay, GDP status
- Route deviation detection

**Webhook Support**
- `/v1/webhooks/` — register endpoint URLs for flight events
- Events: `flight.filed`, `flight.departed`, `flight.arrived`, `flight.deviated`
- Retry logic and delivery logs in user dashboard

**Developer Portal Page**
- API overview, quickstart, link to docs
- Example use cases (flight tracking app, dispatch tool, AI assistant integration)
- Sign up CTA

---

## Phase 3 — Consumer Polish + Notifications v2

**Goal: Clearly better than FlightAware for the target user.**

Phase 3 is about depth, polish, and closing the gap between GolfMike and established players — on the dimensions that matter to our users, not theirs. No ads. Better notifications. iOS app. Historical data.

### Deliverables

**Telegram Notifications**
- Telegram bot integration via Apprise or direct Bot API
- User links Telegram account in notification preferences
- Available for paid users with smart notification tier

**Rich Notification Configuration**
- Per-aircraft notification tier UI: basic / standard / smart
- Per-aircraft channel preferences: browser push, SMS, Telegram (mix and match)
- Notification preview: "here's what a smart notification looks like for this aircraft"

**Filed Flight Plan Alerts**
- Push notification when a flight plan is filed for a watched aircraft
- Includes: filed route summary, departure airport, destination, ETD
- Available on standard and smart tiers

**Flow and Weather Delay Intelligence in Notifications**
- If a watched flight is subject to a GDP, TMI, or EDCT, include that in the notification
- "N560PB is holding for a ground delay program at KORD — current delay ~45 min"
- Smart tier only

**Google and Apple OAuth**
- Supabase Auth already supports this — just enable and wire up the UI
- Login/signup page gets Google and Apple buttons

**React Native iOS App**
- Initial build: flight search, flight detail with map, watchlist, notifications
- Reuse existing React component logic where possible
- Push notifications via APNs (replaces browser push for iOS users)

**Historical Track Access**
- Paid feature: view tracks beyond 90 days
- UI: date picker on flight-detail page, "view historical tracks" for watched aircraft
- Data has been accumulating — by Phase 3 there will be something worth querying

**Public API Pricing + Stripe Billing**
- Define paid tier(s) and pricing publicly
- Stripe integration for subscription management
- Upgrade/downgrade flow in account dashboard
- Billing history and invoices

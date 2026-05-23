# GolfMike — Tech Migration Plan

## The Core Decision

**Flask API stays exactly as-is. React SPA replaces all the static HTML.**

The backend is working. It's ingesting four SWIM feeds live, the DB schema is stable enough, and the `/v1/` API routes are the right abstraction layer. Don't touch what's working.

The frontend is the problem. Vanilla JS + Tabler/Bootstrap is fine for a personal tool; it's not a product. The migration is purely a frontend concern — new `/frontend/` directory, new build, same API.

---

## Frontend Stack

| Concern | Choice | Why |
|---|---|---|
| Framework | React (with Vite) | Industry standard, best ecosystem for shadcn/Tailwind, good React Native path later |
| Build tool | Vite | Fast, zero config for React + TypeScript |
| Component library | shadcn/ui | Components you own, not a dependency. Tailwind-native. No fighting with styles. |
| Styling | Tailwind CSS only | No custom CSS. If you can't express it in Tailwind, reconsider the design. |
| Routing | React Router | Simple, well-understood, no overengineering needed |
| Server state | TanStack Query (React Query) | Perfect fit for this data model — polling flight positions, caching flight plans, background refetches. Write almost zero data fetching code. |
| Language | TypeScript preferred | Not a hard rule on day one, but new components should be `.tsx` |

---

## Auth

**Custom Flask JWT auth, built on our existing Postgres. No new infrastructure.**

Full Supabase self-hosting means ~8 containers (Kong, GoTrue, PostgREST, Realtime, Studio, etc.) for features we mostly don't need. We just need email+password login, JWT tokens, and user records. We already have all of that.

Stack:
- `flask-jwt-extended` — JWT issuance and validation
- `bcrypt` — password hashing
- `users` table in existing Postgres — email, hashed password, created_at, tier

Endpoints:
- `POST /v1/auth/register` — create account
- `POST /v1/auth/login` — returns access + refresh tokens
- `POST /v1/auth/refresh` — exchange refresh token for new access token
- `POST /v1/auth/logout` — revoke refresh token

Protected routes use a `@jwt_required()` decorator. The JWT payload carries the user ID; any endpoint that needs user context pulls from there.

OAuth (Google, Apple) is added later as additional routes that handle the OAuth callback and issue a JWT using the same pipeline. No architectural change needed when that time comes.

New backend work for auth:
- `users` table migration (email, password_hash, tier, created_at)
- The four endpoints above
- `@jwt_required()` middleware applied to watchlist, notification prefs, API key routes

---

## Maps

Keep Leaflet for now. `react-leaflet` is a mature wrapper and the current map code already uses Leaflet. No reason to rewrite working map logic.

**Future consideration:** `deck.gl` for a potential ops view with dense traffic rendering — but that's Phase 3 territory. Don't over-engineer the map layer now.

---

## Directory Structure

```
/frontend/              ← new React app (Vite)
  src/
    components/         ← shared components
    pages/              ← one file per route
    hooks/              ← custom React hooks (API calls, etc.)
    lib/                ← utilities, API client config
  public/
  index.html
  vite.config.ts
  package.json

/static/                ← old vanilla JS pages (deprecated as pages are ported)
/templates/             ← old Jinja templates (deprecated as pages are ported)
```

Build output from Vite goes to `/frontend/dist/`. In production, serve it from Flask (`send_from_directory`) or a CDN. Either works; CDN is better for performance once we care about that.

---

## Build Output / Serving

**Development:** Vite dev server proxies `/v1/` to Flask. Run both in the devcontainer.

**Production option A:** Flask serves the built `/frontend/dist/` as static files. Simple, no new infrastructure.

**Production option B:** CDN (CloudFront, Vercel, etc.) serves the SPA, Flask serves only the API. Better performance, cleaner separation. Either way the API routes don't change.

Start with option A (Flask serves static). Migrate to option B if/when we need the performance or want to split deployments.

---

## Migration Approach

Build the React app alongside the existing vanilla JS pages. Port one page at a time. When a React page is live and working, deprecate the old HTML template. No big bang rewrite.

**Page migration order:**

1. **`/` (flight search / index)** — The front door. Most traffic. Get this right first.
2. **`/flight/{id}` (flight detail)** — The core product page. Position track, route overlay, METAR panel, TBFM data.
3. **`/airports/`** — Airport overview, current flow, METARs.
4. **`/alerts/` (flight alerts)** — Existing alert management page.
5. **`/account/watchlist/`** (new) — Requires auth. Watchlist management, notification preferences.

Each page migration is self-contained. The React page talks to the same `/v1/` endpoints the old JS page called.

---

## What Stays in Flask

Everything that isn't the frontend:

- All `/v1/` API routes
- All SWIM consumers (TFMS, FDPS, ITWS, TBFM)
- Celery workers (position ingestion, notification dispatch, cleanup jobs)
- PostgreSQL schema and migrations
- Redis (Celery broker + any caching)

Flask becomes a pure API server. No more Jinja template rendering once migration is complete.

---

## New Backend Work Required

These don't exist yet and are needed to support the React frontend:

- **`/v1/auth/`** — JWT validation middleware, user provisioning on first login (Supabase UID → internal user record)
- **`/v1/watchlist/`** — CRUD for user watchlist entries
- **`/v1/notifications/preferences/`** — Per-aircraft notification tier and channel settings
- **`/v1/api-keys/`** — Issue, list, revoke API keys (Phase 2)
- **`/v1/webhooks/`** — Webhook endpoint registration (Phase 2)

---

## Code Quality Rules

These are non-negotiable for new frontend code:

1. **No custom CSS.** Tailwind classes only. If you need a one-off style, use a Tailwind arbitrary value, not a `.css` file.
2. **shadcn/ui components for all UI primitives.** Don't write your own button, modal, or input.
3. **TypeScript preferred.** New components in `.tsx`. Don't block progress on strict typing, but don't write new `.jsx` files.
4. **Components in `/frontend/src/components/`.** No ad-hoc component files scattered around the codebase.
5. **API calls via TanStack Query.** No raw `fetch` calls in components. Use a query hook.

# Docker setup

GolfMike runs in Docker for a consistent environment on developer machines and servers (including Portainer).

## Requirements

- Docker with **Compose v2** (`docker compose`, not legacy `docker-compose`)
- Git

## Two stacks

### 1. Devcontainer (`.devcontainer/docker-compose.yml`)

Used by the VS Code / Cursor devcontainer. The **`golfmike-dev`** service keeps the workspace mounted; Celery, web API, consumers, Postgres, and Redis run as sibling services.

```bash
git clone <your-fork-or-repo-url>
cd golfmike
docker compose -f .devcontainer/docker-compose.yml up --build -d
```

Main UI: http://localhost:5500  

Postgres is usually exposed on host port **15432**.

### 2. Root deploy stack (`docker-compose.yml`)

Use this for **Portainer**, bare-metal Docker, or CI-driven deploys. It runs the app from a **container image** (`GOLFMIKE_IMAGE`), not a bind-mounted repo.

**Local** (build from `Dockerfile`):

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build -d
```

**Portainer / GHCR** (pull pre-built image only; do not add `docker-compose.build.yml`):

1. Configure GitHub Actions workflow `.github/workflows/docker-ghcr.yml` (pushes to `ghcr.io/<owner>/<repo>`).
2. Point the Portainer stack at **`docker-compose.yml`** in the repo.
3. Set environment variables (see `.env.example`), especially `GOLFMIKE_IMAGE` and `POSTGRES_PASSWORD`.

### Naming

- Compose **project** name: `golfmike` (via `name: golfmike` in compose files).
- **Container names** use prefix `golfmike-` (e.g. `golfmike-web-api`, `golfmike-redis`, `golfmike-traffic-consumer`).
- **In-network hostnames** remain **`redis`** and **`postgres`** so application URLs in code stay stable.

### Main services (root stack)

| Service | Role |
|---------|------|
| `web_api` | Flask (`app_flask.py`), port `GOLFMIKE_WEB_PORT` (default 5500) |
| `postgres` | PostgreSQL 15 |
| `redis` | Celery broker |
| `celery_worker` | Celery worker |
| `traffic_consumer` / `fdps_tfm_consumer` / `weather_consumer` | Message consumers |
| `db_init` | One-shot schema init |
| `flower` | Celery monitoring UI |

## Environment variables

Copy `.env.example` to `.env` for local `docker compose`, or enter the same keys in Portainer.

`db_config.py` reads `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, and `POSTGRES_DB` (with defaults aligned to the compose Postgres service).

## Operations

```bash
# Status
docker compose -f docker-compose.yml ps

# Logs
docker compose -f docker-compose.yml logs -f web_api

# Stop
docker compose -f docker-compose.yml down

# Reset DB volume (destructive)
docker compose -f docker-compose.yml down -v
```

## GHCR and Portainer webhook

- Image is published on pushes to `main` (and on version tags `v*`).
- Optional: create repository secret **`PORTAINER_WEBHOOK_URL`** with your stack webhook; the workflow triggers redeploy on main after a successful push.

## Further reading

- `DOCKER_SETUP_GUIDE.md` (repository root) — expanded commands and troubleshooting.
- `Dockerfile` — production-oriented runtime image (`/app`, non-root user).

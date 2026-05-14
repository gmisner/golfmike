# Docker Setup Guide for GolfMike

There are two Compose setups:

| Use case | Compose file(s) | Notes |
|----------|-----------------|--------|
| **VS Code / Cursor devcontainer** | `.devcontainer/docker-compose.yml` | Bind-mounts repo, `golfmike-dev` service, watches for Python changes. |
| **Production-style / Portainer** | `docker-compose.yml` (optional `docker-compose.build.yml` locally) | App runs from image `GOLFMIKE_IMAGE` (GHCR or locally built). |

**Container naming:** services `redis` and `postgres` keep short DNS names inside the stack; **container names** use the `golfmike-*` prefix (for example `golfmike-web-api`, `golfmike-redis`, `golfmike-celery-1`, `golfmike-traffic-consumer`).

## Prerequisites

1. Docker Engine 24+ and Docker Compose v2 (plugin: `docker compose`).
2. For the devcontainer stack: Docker Desktop or equivalent with sufficient memory.

## Quick start — devcontainer stack

From the **repository root**:

```bash
docker compose -f .devcontainer/docker-compose.yml up --build -d
docker compose -f .devcontainer/docker-compose.yml ps
docker compose -f .devcontainer/docker-compose.yml logs -f
```

Stop:

```bash
docker compose -f .devcontainer/docker-compose.yml down
# Remove DB volume (destructive):
docker compose -f .devcontainer/docker-compose.yml down -v
```

## Quick start — root stack (local build)

Build the app image from the repo `Dockerfile`, then start all services:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build -d
```

## Quick start — Portainer + GHCR

1. Enable **GitHub Actions** for the repo and allow `GITHUB_TOKEN` **write** for packages (Settings → Actions → General → Workflow permissions → *Read and write permissions*).

2. Push to `main`. Workflow **Publish Docker image to GHCR** builds and pushes to  
   `ghcr.io/<lowercase-github-owner>/<lowercase-repo>` with tags `latest` (on main) and a git-SHA tag.

3. In GitHub → Packages, ensure the package is visible to your Portainer host (public, or add pull credentials).

4. In Portainer: **Stacks** → add stack from **Git**; set Compose path to **`docker-compose.yml`**.

5. Under **Environment**, set at least:

   - `GOLFMIKE_IMAGE=ghcr.io/your-org/your-repo:latest` (use your real lowercase path)
   - `POSTGRES_PASSWORD` (strong value; must match what the app uses — see `db_config.py`)

See `.env.example` for all variables.

**Optional:** add repository secret `PORTAINER_WEBHOOK_URL` (Portainer stack webhook). After each successful push to `main`, the workflow POSTs to it so the stack can redeploy.

**Do not** attach `docker-compose.build.yml` in Portainer when using a pre-built GHCR image.

## Accessing services

### Web API

- URL: http://localhost:5500
- Health: `GET /health`

### Flower (Celery)

- URL: http://localhost:5555 (when Flower service is running)

### PostgreSQL (devcontainer stack)

- Host: localhost  
- Port: **15432** (mapped to container 5432)  
- User / password / DB: see compose `postgres` service (defaults often `postgres` / `password`).

### Redis

- Devcontainer stack exposes **6379** on localhost.

### Root `docker-compose.yml`

- Postgres and Redis are **not** published to the host by default (only app ports from `GOLFMIKE_WEB_PORT` / `GOLFMIKE_FLOWER_PORT`). Access from other containers via hostnames `postgres` and `redis`.

## Useful commands (devcontainer file)

```bash
docker compose -f .devcontainer/docker-compose.yml exec celery_worker celery -A celery_app inspect active
docker compose -f .devcontainer/docker-compose.yml logs -f web_api
docker stats golfmike-web-api
```

## Troubleshooting

- **Build failures:** check `Dockerfile` and `requirements.txt` (root: runtime deps; devcontainer may use `.devcontainer/requirements.txt`).
- **Portainer pull errors:** verify `GOLFMIKE_IMAGE`, registry auth, and package visibility.
- **DB auth errors:** `POSTGRES_*` env vars must match in the `postgres` service and all app services.

## Architecture overview

- **Celery workers:** process background tasks (multiple workers in devcontainer compose).
- **Web API:** Flask app in `app_flask.py`.
- **PostgreSQL / Redis:** data and Celery broker.
- **Consumers:** e.g. `traffic_consumer`, `weather_consumer`, `fdps_tfm_consumer` (see root `docker-compose.yml`).

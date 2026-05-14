# Continuous integration

## GitHub Actions

Workflow `.github/workflows/ci.yml` runs on pull requests and pushes to `main`:

- **unit-tests** — installs dependencies, initializes the database schema against a Postgres service container, runs `python -m unittest discover -s tests -p "test_*.py"`.
- **audit-ingestable** — runs `./tools/audit_ingestable_samples.sh` (strict parser/storer coverage on curated SWIM samples).

Reusable setup lives in `.github/actions/setup-python-deps/` so both jobs stay aligned.

## Branch protection (recommended)

In the GitHub repository: **Settings → Branches → Branch protection rule** for `main` (or your default branch):

1. Require a pull request before merging.
2. Under **Status checks that are required**, enable:
   - `unit-tests`
   - `audit-ingestable`

That way merges are blocked if unit tests fail, DB integration tests fail in CI, or ingestable sample coverage regresses.

## Local database integration tests

`tests/test_integration_swim_samples_db.py` connects using the same environment variables as `db_config.py` (defaults target the `postgres` Docker hostname). If Postgres is not running, those tests are skipped.

To run them locally with Docker Compose, ensure the DB is up and variables match your stack, then:

```bash
python -m unittest tests.test_integration_swim_samples_db -v
```

## HTTP readiness (load balancers later)

- **`GET /health`** — liveness: process is up (Flask: `app_flask.py`; does not require the DB to answer).
- **`GET /health/ready`** — readiness: returns **200** when `SELECT 1` succeeds against the app database, **503** otherwise. Same path exists on Quart entrypoints `app.py` and `app_simple.py` for parity.

The production `docker-compose.yml` **`web_api`** service defines a **container healthcheck** that hits `http://127.0.0.1:5500/health/ready` (no extra `curl` in the image). When you add an external load balancer or orchestrator readiness probes, point them at **`/health/ready`** on the web port; keep **`/health`** for cheap liveness if you split probes.

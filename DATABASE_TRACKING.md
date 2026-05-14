# Database tracking: code map, indexes, and slow queries

## Real-time track pipeline (`trackInformation`)

| Step | Code |
|------|------|
| Message type routing | `parser_storer_registry.py` — `PARSERS["trackInformation"]`, `STORERS["trackInformation"]` |
| XML → model | `parsers/track_information_parser.py` — `parse_track_information` |
| Model → rows | `storers/track_information_to_updates.py` — `convert_and_store_track_updates` |
| Inserts / upserts / status | `storers/track_updates_storer.py` — `store_track_update` |

SQL you see in Postgres logs for this path matches `store_track_update`: `INSERT INTO aircraft … DO NOTHING`, `INSERT INTO flights … ON CONFLICT (gufi) DO UPDATE`, `INSERT INTO track_updates`, `UPDATE flights SET current_status = 'IN_FLIGHT' WHERE … AND current_status = 'PLANNED'`.

## Related writers (same tables, other messages)

| Area | File |
|------|------|
| Flight plan traffic → `flight_plan` + hub `flights` | `storers/flight_plan_traffic_storer.py`, `storers/flight_hub.py` |
| Route assignments | `storers/route_assignment_storer.py` |
| Legacy `track_information` table | `storers/track_information_storer.py` (registry uses `track_updates` path above) |
| TMI list | `storers/tmi_flight_list_storer.py` |

## Indexes

- Baseline hub schema and track indexes: `create_improved_relationships.sql`
- Extra migration (run on existing DBs): `migrations/003_track_path_indexes.sql` — `idx_flights_aircraft_updated_at` for  
  `SELECT gufi FROM flights WHERE aircraft_id = :aircraft_id ORDER BY updated_at DESC LIMIT 1` in `track_updates_storer.py`
- API-style reads over `track_updates` by `gufi` + time: `idx_track_updates_gufi_time` (same SQL file)

## Slow queries: Postgres

1. **Log slow statements**: `ALTER DATABASE yourdb SET log_min_duration_statement = '500ms';` (or set in `postgresql.conf` and reload).
2. **pg_stat_statements** (extension): find top total/time mean queries; reset after deploys when comparing.
3. **EXPLAIN (ANALYZE, BUFFERS)** on suspicious SQL from logs or `simple_api.py` (large joins/subqueries on `track_updates`).

## App-side timing

- `utils/db_metrics.log_db_write_duration` wraps each track write in `track_updates_storer.py`.
- **Env**: `DB_METRICS=0` disables; `DB_SLOW_QUERY_MS` (default `200`) controls when a **warning** is emitted (`slow database write`) with `duration_ms`, `db_operation`, `aircraft_id`, `gufi`.

Typical bottlenecks at scale: growing `track_updates` (insert rate, disk), concurrent upserts on `flights` (usually cheap via PK on `gufi`), and read APIs that aggregate latest position per flight without tight filters.

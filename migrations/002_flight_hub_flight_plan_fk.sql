-- Flight hub enforcement: flight_plan.gufi -> flights(gufi), track_updates.track_data
-- Idempotent sections; run after create_improved_relationships.sql (or equivalent DDL).

-- 1) Optional column used by track_updates_storer (fixes mismatch with older DDL)
ALTER TABLE track_updates
    ADD COLUMN IF NOT EXISTS track_data JSONB;

-- 2) Parent aircraft rows for any tails referenced by flight_plan / track_information
INSERT INTO aircraft (aircraft_id)
SELECT DISTINCT fp.aircraft_id
FROM flight_plan fp
WHERE fp.aircraft_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM aircraft a WHERE a.aircraft_id = fp.aircraft_id);

INSERT INTO aircraft (aircraft_id)
SELECT DISTINCT ti.aircraft_id
FROM track_information ti
WHERE ti.aircraft_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM aircraft a WHERE a.aircraft_id = ti.aircraft_id);

-- 3) Non-null gufi on flight_plan requires aircraft_id for hub row (clear broken rows)
UPDATE flight_plan
SET gufi = NULL
WHERE gufi IS NOT NULL
  AND aircraft_id IS NULL;

-- 4) Backfill hub rows from flight_plan
INSERT INTO flights (
    gufi, aircraft_id, flight_reference, departure_airport, arrival_airport,
    scheduled_departure, current_status, updated_at
)
SELECT
    fp.gufi,
    fp.aircraft_id,
    fp.flight_reference,
    fp.departure_airport,
    fp.arrival_airport,
    fp.igtd,
    'PLANNED',
    NOW()
FROM flight_plan fp
WHERE fp.gufi IS NOT NULL
  AND fp.aircraft_id IS NOT NULL
ON CONFLICT (gufi) DO NOTHING;

-- 5) Backfill from track_information (same gufi may already exist — skip)
INSERT INTO flights (
    gufi, aircraft_id, current_status, updated_at
)
SELECT DISTINCT ON (ti.gufi)
    ti.gufi,
    ti.aircraft_id,
    'IN_FLIGHT',
    NOW()
FROM track_information ti
WHERE ti.gufi IS NOT NULL
  AND ti.aircraft_id IS NOT NULL
ORDER BY ti.gufi, ti.id DESC
ON CONFLICT (gufi) DO NOTHING;

-- 6) Foreign key: non-null flight_plan.gufi must reference flights
ALTER TABLE flight_plan DROP CONSTRAINT IF EXISTS fk_flight_plan_flights;
ALTER TABLE flight_plan
    ADD CONSTRAINT fk_flight_plan_flights
    FOREIGN KEY (gufi) REFERENCES flights (gufi);

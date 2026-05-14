-- Ensure camelCase columns used by SQLAlchemy FlightPlanDBModel and flight_plan_traffic_storer
-- exist with quoted identifiers (PostgreSQL otherwise folds unquoted names to lowercase).
-- Safe to re-run.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'flight_plan' AND c.relkind = 'r'
  ) THEN
    IF NOT EXISTS (
      SELECT 1 FROM pg_attribute a
      JOIN pg_class c ON c.oid = a.attrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public'
        AND c.relname = 'flight_plan'
        AND a.attname = 'flightPlanRoute_10a'
        AND a.attnum > 0 AND NOT a.attisdropped
    ) THEN
      ALTER TABLE public.flight_plan ADD COLUMN "flightPlanRoute_10a" TEXT;
    END IF;

    IF NOT EXISTS (
      SELECT 1 FROM pg_attribute a
      JOIN pg_class c ON c.oid = a.attrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public'
        AND c.relname = 'flight_plan'
        AND a.attname = 'flightId_02a'
        AND a.attnum > 0 AND NOT a.attisdropped
    ) THEN
      ALTER TABLE public.flight_plan ADD COLUMN "flightId_02a" TEXT;
    END IF;
  END IF;
END $$;

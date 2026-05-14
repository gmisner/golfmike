-- Supports: SELECT gufi FROM flights WHERE aircraft_id = ? ORDER BY updated_at DESC LIMIT 1
-- (track_updates_storer GUFI resolution when message has no gufi)
CREATE INDEX IF NOT EXISTS idx_flights_aircraft_updated_at
    ON flights (aircraft_id, updated_at DESC);

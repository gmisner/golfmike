-- Improved Database Relationships Schema
-- This creates tables with proper foreign key relationships using GUFI as the primary linking key

-- 1. Central flights table (using GUFI as primary key)
CREATE TABLE IF NOT EXISTS flights (
    gufi VARCHAR(50) PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    flight_reference VARCHAR(50),
    departure_airport VARCHAR(10),
    arrival_airport VARCHAR(10),
    scheduled_departure TIMESTAMP WITH TIME ZONE,
    scheduled_arrival TIMESTAMP WITH TIME ZONE,
    current_status VARCHAR(50) DEFAULT 'PLANNED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_flights_aircraft FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id)
);

CREATE INDEX IF NOT EXISTS idx_flights_aircraft_id ON flights(aircraft_id);
CREATE INDEX IF NOT EXISTS idx_flights_aircraft_updated_at ON flights(aircraft_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_flights_status ON flights(current_status);
CREATE INDEX IF NOT EXISTS idx_flights_departure_time ON flights(scheduled_departure);

-- 2. Route assignments table (from FlightScheduleActivate messages)
CREATE TABLE IF NOT EXISTS route_assignments (
    id SERIAL PRIMARY KEY,
    gufi VARCHAR(50) NOT NULL,
    assigned_altitude INTEGER,
    assigned_speed INTEGER,
    route_data JSONB, -- Full route with waypoints, fixes, etc.
    etd TIMESTAMP WITH TIME ZONE,
    eta TIMESTAMP WITH TIME ZONE,
    source_facility VARCHAR(50),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_route_assignments_flight FOREIGN KEY (gufi) REFERENCES flights(gufi) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_route_assignments_gufi ON route_assignments(gufi);
CREATE INDEX IF NOT EXISTS idx_route_assignments_assigned_at ON route_assignments(assigned_at);

-- 3. Route waypoints (normalized from route_assignments.route_data)
CREATE TABLE IF NOT EXISTS route_waypoints (
    id SERIAL PRIMARY KEY,
    route_assignment_id INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,
    waypoint_type VARCHAR(20), -- FIX, WAYPOINT
    name VARCHAR(50), -- Fix name or waypoint identifier
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    elapsed_time INTEGER, -- Seconds from departure
    altitude INTEGER,
    
    CONSTRAINT fk_route_waypoints_assignment FOREIGN KEY (route_assignment_id) REFERENCES route_assignments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_route_waypoints_route ON route_waypoints(route_assignment_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_route_waypoints_coords ON route_waypoints(latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- 4. Track updates table (from TrackInformation messages)
CREATE TABLE IF NOT EXISTS track_updates (
    id SERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    gufi VARCHAR(50) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    altitude INTEGER,
    speed INTEGER,
    heading INTEGER,
    time_at_position TIMESTAMP WITH TIME ZONE NOT NULL,
    source_facility VARCHAR(50),
    track_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_track_updates_flight FOREIGN KEY (gufi) REFERENCES flights(gufi) ON DELETE CASCADE,
    CONSTRAINT fk_track_updates_aircraft FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id)
);

CREATE INDEX IF NOT EXISTS idx_track_updates_aircraft_id ON track_updates(aircraft_id);
CREATE INDEX IF NOT EXISTS idx_track_updates_gufi_time ON track_updates(gufi, time_at_position DESC);
CREATE INDEX IF NOT EXISTS idx_track_updates_time ON track_updates(time_at_position DESC);
CREATE INDEX IF NOT EXISTS idx_track_updates_coords ON track_updates(latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- 5. Flight alerts table (for tracking deviations and events)
CREATE TABLE IF NOT EXISTS flight_alerts (
    id SERIAL PRIMARY KEY,
    gufi VARCHAR(50) NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- ROUTE_DEVIATION, ALTITUDE_DEVIATION, SPEED_DEVIATION, ROUTE_ASSIGNED, etc.
    severity VARCHAR(20) DEFAULT 'INFO', -- INFO, WARNING, CRITICAL
    message TEXT,
    alert_data JSONB, -- Additional context (e.g., deviation distance, expected vs actual)
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_flight_alerts_flight FOREIGN KEY (gufi) REFERENCES flights(gufi) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_flight_alerts_gufi ON flight_alerts(gufi);
CREATE INDEX IF NOT EXISTS idx_flight_alerts_type ON flight_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_flight_alerts_acknowledged ON flight_alerts(acknowledged, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_flight_alerts_severity ON flight_alerts(severity, created_at DESC);

-- View: Latest flight status with route and track info
CREATE OR REPLACE VIEW flight_status_view AS
SELECT 
    f.gufi,
    f.aircraft_id,
    f.flight_reference,
    f.departure_airport,
    f.arrival_airport,
    f.scheduled_departure,
    f.scheduled_arrival,
    f.current_status,
    -- Latest route assignment
    ra.assigned_altitude as route_assigned_altitude,
    ra.assigned_speed as route_assigned_speed,
    ra.assigned_at as route_assigned_at,
    -- Latest track update
    tu.latitude as current_latitude,
    tu.longitude as current_longitude,
    tu.altitude as current_altitude,
    tu.speed as current_speed,
    tu.heading as current_heading,
    tu.time_at_position as last_position_time,
    -- Unacknowledged alerts count
    (SELECT COUNT(*) FROM flight_alerts fa WHERE fa.gufi = f.gufi AND fa.acknowledged = FALSE) as unacknowledged_alerts
FROM flights f
LEFT JOIN LATERAL (
    SELECT * FROM route_assignments 
    WHERE gufi = f.gufi 
    ORDER BY assigned_at DESC 
    LIMIT 1
) ra ON true
LEFT JOIN LATERAL (
    SELECT * FROM track_updates 
    WHERE gufi = f.gufi 
    ORDER BY time_at_position DESC 
    LIMIT 1
) tu ON true;

-- Function: Calculate distance from route (for deviation detection)
CREATE OR REPLACE FUNCTION calculate_route_deviation(
    p_gufi VARCHAR(50),
    p_latitude DECIMAL,
    p_longitude DECIMAL
) RETURNS DECIMAL AS $$
DECLARE
    min_distance DECIMAL;
BEGIN
    -- Find minimum distance to any waypoint in the assigned route
    SELECT MIN(
        6371 * acos(
            cos(radians(p_latitude)) * 
            cos(radians(rw.latitude)) * 
            cos(radians(rw.longitude) - radians(p_longitude)) + 
            sin(radians(p_latitude)) * 
            sin(radians(rw.latitude))
        )
    ) INTO min_distance
    FROM route_waypoints rw
    JOIN route_assignments ra ON rw.route_assignment_id = ra.id
    WHERE ra.gufi = p_gufi
    AND ra.assigned_at = (
        SELECT MAX(assigned_at) 
        FROM route_assignments 
        WHERE gufi = p_gufi
    )
    AND rw.latitude IS NOT NULL 
    AND rw.longitude IS NOT NULL;
    
    RETURN COALESCE(min_distance, 0);
END;
$$ LANGUAGE plpgsql;


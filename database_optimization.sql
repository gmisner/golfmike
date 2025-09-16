-- =====================================================
-- GOLFMIKE DATABASE OPTIMIZATION FOR REAL-TIME FLIGHT TRACKING
-- =====================================================

-- 1. FLIGHT EVENTS TABLE - For status notifications (takeoff, landing, etc.)
CREATE TABLE IF NOT EXISTS flight_events (
    id SERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    gufi VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- 'PLANNED', 'DEPARTED', 'IN_FLIGHT', 'ARRIVED', 'DIVERTED', 'CANCELLED'
    event_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    event_data JSONB, -- Store additional event-specific data
    source_facility VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for fast lookups
    INDEX idx_flight_events_aircraft_id (aircraft_id),
    INDEX idx_flight_events_gufi (gufi),
    INDEX idx_flight_events_timestamp (event_timestamp),
    INDEX idx_flight_events_type (event_type)
);

-- 2. OPTIMIZED TRACK INFORMATION TABLE - For real-time position updates
CREATE TABLE IF NOT EXISTS track_updates (
    id SERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    gufi VARCHAR(50) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    altitude INTEGER, -- in feet
    speed INTEGER, -- in knots
    heading INTEGER, -- in degrees
    time_at_position TIMESTAMP WITH TIME ZONE NOT NULL,
    source_facility VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for spatial and temporal queries
    INDEX idx_track_updates_aircraft_id (aircraft_id),
    INDEX idx_track_updates_gufi (gufi),
    INDEX idx_track_updates_timestamp (time_at_position),
    INDEX idx_track_updates_position (latitude, longitude),
    INDEX idx_track_updates_created_at (created_at)
);

-- 3. CURRENT FLIGHT STATUS VIEW - Materialized view for real-time status
CREATE MATERIALIZED VIEW current_flight_status AS
SELECT 
    f.aircraft_id,
    f.gufi,
    f.departure_airport,
    f.arrival_airport,
    f.igtd as scheduled_departure,
    f.eta as scheduled_arrival,
    fe.event_type as current_status,
    fe.event_timestamp as status_timestamp,
    tu.latitude,
    tu.longitude,
    tu.altitude,
    tu.speed,
    tu.heading,
    tu.time_at_position as last_position_time,
    CASE 
        WHEN fe.event_type = 'DEPARTED' THEN 'In Flight'
        WHEN fe.event_type = 'ARRIVED' THEN 'Landed'
        WHEN fe.event_type = 'DIVERTED' THEN 'Diverted'
        WHEN fe.event_type = 'CANCELLED' THEN 'Cancelled'
        ELSE 'Planned'
    END as status_display
FROM flight_plan f
LEFT JOIN LATERAL (
    SELECT event_type, event_timestamp
    FROM flight_events fe2
    WHERE fe2.aircraft_id = f.aircraft_id
    ORDER BY fe2.event_timestamp DESC
    LIMIT 1
) fe ON true
LEFT JOIN LATERAL (
    SELECT latitude, longitude, altitude, speed, heading, time_at_position
    FROM track_updates tu2
    WHERE tu2.aircraft_id = f.aircraft_id
    ORDER BY tu2.time_at_position DESC
    LIMIT 1
) tu ON true;

-- Create index on materialized view
CREATE INDEX idx_current_flight_status_aircraft_id ON current_flight_status (aircraft_id);
CREATE INDEX idx_current_flight_status_status ON current_flight_status (current_status);
CREATE INDEX idx_current_flight_status_position ON current_flight_status (latitude, longitude);

-- 4. AIRCRAFT AVATAR/INFORMATION TABLE - For aircraft details and avatars
CREATE TABLE IF NOT EXISTS aircraft_profiles (
    aircraft_id VARCHAR(50) PRIMARY KEY,
    airline VARCHAR(10),
    aircraft_type VARCHAR(20),
    aircraft_category VARCHAR(20), -- 'JET', 'TURBO', 'PISTON'
    user_category VARCHAR(30), -- 'COMMERCIAL', 'GENERAL AVIATION', 'CARGO', 'AIR TAXI'
    avatar_url VARCHAR(255), -- URL to aircraft avatar/image
    livery_colors JSONB, -- Store airline colors for custom avatars
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. FLIGHT ROUTES TABLE - For storing flight paths and waypoints
CREATE TABLE IF NOT EXISTS flight_routes (
    id SERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    gufi VARCHAR(50) NOT NULL,
    route_name VARCHAR(100),
    waypoints JSONB, -- Array of waypoints with lat/long
    airways JSONB, -- Array of airways
    sectors JSONB, -- Array of ATC sectors
    route_of_flight TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_flight_routes_aircraft_id (aircraft_id),
    INDEX idx_flight_routes_gufi (gufi)
);

-- 6. NOTIFICATION PREFERENCES TABLE - For user notification settings
CREATE TABLE IF NOT EXISTS notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50), -- If you add user management later
    aircraft_id VARCHAR(50),
    notification_types JSONB, -- ['takeoff', 'landing', 'divert', 'delay']
    notification_methods JSONB, -- ['email', 'push', 'webhook']
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. DATA RETENTION POLICIES
-- Keep track updates for 7 days, then archive
CREATE TABLE IF NOT EXISTS track_updates_archive (
    LIKE track_updates INCLUDING ALL
);

-- Keep flight events for 30 days, then archive
CREATE TABLE IF NOT EXISTS flight_events_archive (
    LIKE flight_events INCLUDING ALL
);

-- 8. PERFORMANCE OPTIMIZATIONS
-- Add indexes to existing tables
CREATE INDEX IF NOT EXISTS idx_aircraft_aircraft_id ON aircraft (aircraft_id);
CREATE INDEX IF NOT EXISTS idx_flight_plan_aircraft_id ON flight_plan (aircraft_id);
CREATE INDEX IF NOT EXISTS idx_flight_plan_gufi ON flight_plan (gufi);
CREATE INDEX IF NOT EXISTS idx_flight_plan_departure ON flight_plan (departure_airport);
CREATE INDEX IF NOT EXISTS idx_flight_plan_arrival ON flight_plan (arrival_airport);
CREATE INDEX IF NOT EXISTS idx_flight_plan_igtd ON flight_plan (igtd);

-- 9. FUNCTIONS FOR COMMON QUERIES
-- Function to get current position of an aircraft
CREATE OR REPLACE FUNCTION get_aircraft_position(aircraft_id_param VARCHAR(50))
RETURNS TABLE (
    aircraft_id VARCHAR(50),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    altitude INTEGER,
    speed INTEGER,
    heading INTEGER,
    time_at_position TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tu.aircraft_id,
        tu.latitude,
        tu.longitude,
        tu.altitude,
        tu.speed,
        tu.heading,
        tu.time_at_position
    FROM track_updates tu
    WHERE tu.aircraft_id = aircraft_id_param
    ORDER BY tu.time_at_position DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to get flight status history
CREATE OR REPLACE FUNCTION get_flight_status_history(aircraft_id_param VARCHAR(50), hours_back INTEGER DEFAULT 24)
RETURNS TABLE (
    event_type VARCHAR(50),
    event_timestamp TIMESTAMP WITH TIME ZONE,
    event_data JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        fe.event_type,
        fe.event_timestamp,
        fe.event_data
    FROM flight_events fe
    WHERE fe.aircraft_id = aircraft_id_param
    AND fe.event_timestamp >= NOW() - INTERVAL '1 hour' * hours_back
    ORDER BY fe.event_timestamp DESC;
END;
$$ LANGUAGE plpgsql;

-- 10. TRIGGERS FOR AUTOMATIC UPDATES
-- Update aircraft_profiles when new aircraft data comes in
CREATE OR REPLACE FUNCTION update_aircraft_profile()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO aircraft_profiles (aircraft_id, airline, aircraft_category, user_category)
    VALUES (NEW.aircraft_id, NEW.airline, NEW.aircraft_category, NEW.user_category)
    ON CONFLICT (aircraft_id) 
    DO UPDATE SET
        airline = EXCLUDED.airline,
        aircraft_category = EXCLUDED.aircraft_category,
        user_category = EXCLUDED.user_category,
        updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_aircraft_profile
    AFTER INSERT OR UPDATE ON aircraft
    FOR EACH ROW
    EXECUTE FUNCTION update_aircraft_profile();

-- 11. REFRESH MATERIALIZED VIEW FUNCTION
CREATE OR REPLACE FUNCTION refresh_flight_status()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY current_flight_status;
END;
$$ LANGUAGE plpgsql;

-- 12. DATA CLEANUP FUNCTIONS
-- Function to archive old track updates
CREATE OR REPLACE FUNCTION archive_old_track_updates()
RETURNS VOID AS $$
BEGIN
    -- Move track updates older than 7 days to archive
    INSERT INTO track_updates_archive 
    SELECT * FROM track_updates 
    WHERE created_at < NOW() - INTERVAL '7 days';
    
    -- Delete archived records
    DELETE FROM track_updates 
    WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- Function to archive old flight events
CREATE OR REPLACE FUNCTION archive_old_flight_events()
RETURNS VOID AS $$
BEGIN
    -- Move flight events older than 30 days to archive
    INSERT INTO flight_events_archive 
    SELECT * FROM flight_events 
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    -- Delete archived records
    DELETE FROM flight_events 
    WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;




# Database Relationships Improvement Proposal

## Current Issues

1. **Lack of Centralized Flight Entity**: Data is scattered across multiple tables without a clear primary flight entity
2. **Weak Relationships**: GUFI exists in multiple tables but isn't used as a proper foreign key
3. **No Route Assignment Tracking**: FlightScheduleActivate data (ATC route assignments) isn't properly stored or linked
4. **No Alert System**: No way to track deviations from assigned routes or generate alerts

## Proposed Data Model

### Core Concept: GUFI as Primary Flight Identifier

**GUFI (Globally Unique Flight Identifier)** is the key that links all flight-related data:
- FlightScheduleActivate (route assignments)
- TrackInformation (position updates)
- Flight plans
- Events and alerts

## Proposed Tables

### 1. `flights` (Central Flight Entity)
**Purpose**: Single source of truth for each flight using GUFI as primary key

```sql
CREATE TABLE flights (
    gufi VARCHAR(50) PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    flight_reference VARCHAR(50),
    departure_airport VARCHAR(10),
    arrival_airport VARCHAR(10),
    scheduled_departure TIMESTAMP WITH TIME ZONE,
    scheduled_arrival TIMESTAMP WITH TIME ZONE,
    current_status VARCHAR(50) DEFAULT 'PLANNED', -- PLANNED, ACTIVE, COMPLETED, CANCELLED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id)
);
```

### 2. `route_assignments` (From FlightScheduleActivate)
**Purpose**: Store ATC route assignments with waypoints and fixes

```sql
CREATE TABLE route_assignments (
    id SERIAL PRIMARY KEY,
    gufi VARCHAR(50) NOT NULL,
    assigned_altitude INTEGER,
    assigned_speed INTEGER,
    route_data JSONB, -- Full route with waypoints, fixes, etc.
    etd TIMESTAMP WITH TIME ZONE,
    eta TIMESTAMP WITH TIME ZONE,
    source_facility VARCHAR(50),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (gufi) REFERENCES flights(gufi) ON DELETE CASCADE,
    INDEX idx_route_assignments_gufi (gufi),
    INDEX idx_route_assignments_assigned_at (assigned_at)
);
```

### 3. `track_updates` (From TrackInformation)
**Purpose**: Store real-time position updates

```sql
CREATE TABLE track_updates (
    id SERIAL PRIMARY KEY,
    gufi VARCHAR(50) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    altitude INTEGER,
    speed INTEGER,
    heading INTEGER,
    time_at_position TIMESTAMP WITH TIME ZONE NOT NULL,
    source_facility VARCHAR(50),
    
    FOREIGN KEY (gufi) REFERENCES flights(gufi) ON DELETE CASCADE,
    INDEX idx_track_updates_gufi_time (gufi, time_at_position),
    INDEX idx_track_updates_time (time_at_position)
);
```

### 4. `flight_alerts` (New - For Alert System)
**Purpose**: Track alerts based on route deviations, altitude changes, etc.

```sql
CREATE TABLE flight_alerts (
    id SERIAL PRIMARY KEY,
    gufi VARCHAR(50) NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- ROUTE_DEVIATION, ALTITUDE_DEVIATION, SPEED_DEVIATION, etc.
    severity VARCHAR(20) DEFAULT 'INFO', -- INFO, WARNING, CRITICAL
    message TEXT,
    alert_data JSONB, -- Additional context
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (gufi) REFERENCES flights(gufi) ON DELETE CASCADE,
    INDEX idx_flight_alerts_gufi (gufi),
    INDEX idx_flight_alerts_type (alert_type),
    INDEX idx_flight_alerts_acknowledged (acknowledged, created_at)
);
```

### 5. `route_waypoints` (Normalized Waypoints)
**Purpose**: Store individual waypoints from route assignments for easier querying

```sql
CREATE TABLE route_waypoints (
    id SERIAL PRIMARY KEY,
    route_assignment_id INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,
    waypoint_type VARCHAR(20), -- FIX, WAYPOINT
    name VARCHAR(50), -- Fix name or waypoint identifier
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    elapsed_time INTEGER, -- Seconds from departure
    altitude INTEGER,
    
    FOREIGN KEY (route_assignment_id) REFERENCES route_assignments(id) ON DELETE CASCADE,
    INDEX idx_route_waypoints_route (route_assignment_id, sequence_number)
);
```

## Relationships Diagram

```
flights (gufi PK)
    ├── route_assignments (gufi FK) → route_waypoints (route_assignment_id FK)
    ├── track_updates (gufi FK)
    └── flight_alerts (gufi FK)
    
aircraft (aircraft_id PK)
    └── flights (aircraft_id FK)
```

## Benefits

1. **Single Source of Truth**: `flights` table with GUFI as primary key
2. **Proper Foreign Keys**: All related data properly linked
3. **Route Tracking**: Can compare assigned routes vs actual tracks
4. **Alert System**: Foundation for deviation detection
5. **Query Performance**: Proper indexes for common queries
6. **Data Integrity**: Foreign key constraints ensure consistency

## Migration Strategy

1. Create new tables
2. Migrate existing data:
   - Extract GUFI from existing tables
   - Populate `flights` table
   - Link existing data via GUFI
3. Update parsers/storers to use new schema
4. Add alert detection logic

## Alert Examples

### Route Deviation Alert
```python
# When track_update shows aircraft is off assigned route
if distance_from_route > threshold:
    create_alert(
        gufi=gufi,
        alert_type='ROUTE_DEVIATION',
        severity='WARNING',
        message=f'Aircraft {aircraft_id} is {distance}nm off assigned route'
    )
```

### Altitude Deviation Alert
```python
# When altitude differs significantly from assigned
if abs(current_altitude - assigned_altitude) > threshold:
    create_alert(
        gufi=gufi,
        alert_type='ALTITUDE_DEVIATION',
        severity='INFO',
        message=f'Aircraft at {current_altitude}ft, assigned {assigned_altitude}ft'
    )
```

### New Route Assignment Alert
```python
# When ATC assigns a new route
create_alert(
    gufi=gufi,
    alert_type='ROUTE_ASSIGNED',
    severity='INFO',
    message=f'New route assigned by {source_facility}'
)
```


-- SWIM weather tables (models/sqlalchemy/weather.py)
-- Run against the app database (e.g. psql -f migrations/004_weather_swim_tables.sql).
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS weather_stations (
	id SERIAL NOT NULL,
	station_id VARCHAR(10) NOT NULL,
	station_name VARCHAR(100),
	station_type VARCHAR(20),
	latitude FLOAT,
	longitude FLOAT,
	elevation FLOAT,
	state VARCHAR(2),
	country VARCHAR(2),
	created_at TIMESTAMP WITHOUT TIME ZONE,
	updated_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS metar_data (
	id SERIAL NOT NULL,
	station_id VARCHAR(10) NOT NULL,
	observation_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	raw_text TEXT,
	wind_direction INTEGER,
	wind_speed INTEGER,
	wind_gust INTEGER,
	visibility FLOAT,
	visibility_units VARCHAR(10),
	sky_conditions JSONB,
	temperature FLOAT,
	dewpoint FLOAT,
	altimeter FLOAT,
	weather_phenomena JSONB,
	flight_category VARCHAR(1),
	sea_level_pressure FLOAT,
	pressure_tendency FLOAT,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	updated_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS taf_data (
	id SERIAL NOT NULL,
	station_id VARCHAR(10) NOT NULL,
	issue_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	valid_from TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	valid_to TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	raw_text TEXT,
	forecast_periods JSONB,
	wind_direction INTEGER,
	wind_speed INTEGER,
	wind_gust INTEGER,
	visibility FLOAT,
	visibility_units VARCHAR(10),
	sky_conditions JSONB,
	weather_phenomena JSONB,
	flight_category VARCHAR(1),
	probability INTEGER,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	updated_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS notam_data (
	id SERIAL NOT NULL,
	notam_id VARCHAR(50) NOT NULL,
	notam_number VARCHAR(20),
	location_identifier VARCHAR(10),
	location_type VARCHAR(20),
	affected_airspace JSONB,
	effective_from TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	effective_until TIMESTAMP WITHOUT TIME ZONE,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	raw_text TEXT,
	summary TEXT,
	description TEXT,
	notam_type VARCHAR(20),
	priority VARCHAR(10),
	category VARCHAR(20),
	is_active BOOLEAN,
	is_cancelled BOOLEAN,
	coordinates JSONB,
	altitude_floor INTEGER,
	altitude_ceiling INTEGER,
	updated_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS weather_alerts (
	id SERIAL NOT NULL,
	alert_id VARCHAR(50) NOT NULL,
	alert_type VARCHAR(20) NOT NULL,
	severity VARCHAR(10),
	urgency VARCHAR(10),
	affected_area JSONB,
	affected_airports JSONB,
	valid_from TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	valid_until TIMESTAMP WITHOUT TIME ZONE,
	issued_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	raw_text TEXT,
	summary TEXT,
	description TEXT,
	weather_phenomena JSONB,
	altitude_floor INTEGER,
	altitude_ceiling INTEGER,
	is_active BOOLEAN,
	is_cancelled BOOLEAN,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	updated_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS weather_observations (
	id SERIAL NOT NULL,
	station_id VARCHAR(10) NOT NULL,
	observation_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	temperature FLOAT,
	dewpoint FLOAT,
	humidity FLOAT,
	pressure FLOAT,
	wind_direction INTEGER,
	wind_speed FLOAT,
	wind_gust FLOAT,
	visibility FLOAT,
	ceiling INTEGER,
	ceiling_type VARCHAR(10),
	precipitation_type VARCHAR(20),
	precipitation_rate FLOAT,
	precipitation_accumulation FLOAT,
	raw_data JSONB,
	data_source VARCHAR(20),
	quality_flags JSONB,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_weather_stations_station_id ON weather_stations (station_id);
CREATE INDEX IF NOT EXISTS idx_weather_stations_location ON weather_stations (latitude, longitude);

CREATE INDEX IF NOT EXISTS idx_metar_observation_time ON metar_data (observation_time);
CREATE INDEX IF NOT EXISTS ix_metar_data_observation_time ON metar_data (observation_time);
CREATE INDEX IF NOT EXISTS ix_metar_data_station_id ON metar_data (station_id);
CREATE INDEX IF NOT EXISTS idx_metar_station_time ON metar_data (station_id, observation_time);

CREATE INDEX IF NOT EXISTS ix_taf_data_station_id ON taf_data (station_id);
CREATE INDEX IF NOT EXISTS idx_taf_station_time ON taf_data (station_id, issue_time);
CREATE INDEX IF NOT EXISTS idx_taf_valid_period ON taf_data (valid_from, valid_to);
CREATE INDEX IF NOT EXISTS ix_taf_data_valid_from ON taf_data (valid_from);
CREATE INDEX IF NOT EXISTS ix_taf_data_issue_time ON taf_data (issue_time);
CREATE INDEX IF NOT EXISTS ix_taf_data_valid_to ON taf_data (valid_to);

CREATE INDEX IF NOT EXISTS ix_notam_data_effective_from ON notam_data (effective_from);
CREATE UNIQUE INDEX IF NOT EXISTS ix_notam_data_notam_id ON notam_data (notam_id);
CREATE INDEX IF NOT EXISTS idx_notam_effective_period ON notam_data (effective_from, effective_until);
CREATE INDEX IF NOT EXISTS ix_notam_data_is_active ON notam_data (is_active);
CREATE INDEX IF NOT EXISTS idx_notam_location_time ON notam_data (location_identifier, effective_from);
CREATE INDEX IF NOT EXISTS ix_notam_data_effective_until ON notam_data (effective_until);
CREATE INDEX IF NOT EXISTS ix_notam_data_location_identifier ON notam_data (location_identifier);
CREATE INDEX IF NOT EXISTS idx_notam_active ON notam_data (is_active, effective_until);
CREATE INDEX IF NOT EXISTS ix_notam_data_notam_number ON notam_data (notam_number);

CREATE UNIQUE INDEX IF NOT EXISTS ix_weather_alerts_alert_id ON weather_alerts (alert_id);
CREATE INDEX IF NOT EXISTS idx_weather_alert_valid_period ON weather_alerts (valid_from, valid_until);
CREATE INDEX IF NOT EXISTS ix_weather_alerts_is_active ON weather_alerts (is_active);
CREATE INDEX IF NOT EXISTS idx_weather_alert_type_time ON weather_alerts (alert_type, valid_from);
CREATE INDEX IF NOT EXISTS ix_weather_alerts_valid_until ON weather_alerts (valid_until);
CREATE INDEX IF NOT EXISTS ix_weather_alerts_issued_at ON weather_alerts (issued_at);
CREATE INDEX IF NOT EXISTS idx_weather_alert_active ON weather_alerts (is_active, valid_until);
CREATE INDEX IF NOT EXISTS ix_weather_alerts_valid_from ON weather_alerts (valid_from);
CREATE INDEX IF NOT EXISTS ix_weather_alerts_alert_type ON weather_alerts (alert_type);

CREATE INDEX IF NOT EXISTS idx_weather_obs_station_time ON weather_observations (station_id, observation_time);
CREATE INDEX IF NOT EXISTS ix_weather_observations_station_id ON weather_observations (station_id);
CREATE INDEX IF NOT EXISTS ix_weather_observations_observation_time ON weather_observations (observation_time);
CREATE INDEX IF NOT EXISTS idx_weather_obs_time ON weather_observations (observation_time);

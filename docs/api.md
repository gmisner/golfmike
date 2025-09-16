# API Documentation

## Overview

GolfMike provides a RESTful API for accessing flight data, weather information, and system status. All endpoints return JSON responses.

## Base URL

```
http://localhost:5500
```

## Authentication

Currently, the API does not require authentication. This may change in future versions.

## Endpoints

### Flight Data

#### Get Current Flights
```http
GET /api/flights/current
```

Returns a list of all currently active flights.

**Response:**
```json
{
  "flights": [
    {
      "aircraft_id": "AAL123",
      "callsign": "American 123",
      "departure_airport": "KJFK",
      "arrival_airport": "KLAX",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "altitude": 35000,
      "ground_speed": 450,
      "heading": 270,
      "last_update": "2025-09-15T19:30:00Z"
    }
  ],
  "total": 1,
  "timestamp": "2025-09-15T19:30:00Z"
}
```

#### Get Flight Details
```http
GET /api/flights/{aircraft_id}/detail
```

Returns comprehensive details for a specific flight, including weather data.

**Parameters:**
- `aircraft_id` (string): The aircraft identifier

**Response:**
```json
{
  "aircraft_id": "AAL123",
  "callsign": "American 123",
  "departure_airport": "KJFK",
  "arrival_airport": "KLAX",
  "current_position": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "altitude": 35000,
    "ground_speed": 450,
    "heading": 270
  },
  "flight_plan": {
    "departure_time": "2025-09-15T18:00:00Z",
    "arrival_time": "2025-09-15T21:30:00Z",
    "route": "KJFK DCT KLAX",
    "waypoints": [
      {"name": "KJFK", "latitude": 40.6413, "longitude": -73.7781},
      {"name": "KLAX", "latitude": 33.9425, "longitude": -118.4081}
    ]
  },
  "weather": {
    "departure_metar": {
      "station_id": "KJFK",
      "observation_time": "2025-09-15T19:00:00Z",
      "temperature": 22,
      "dewpoint": 18,
      "wind_direction": 180,
      "wind_speed": 12,
      "visibility": 10,
      "flight_category": "VFR"
    },
    "arrival_metar": {
      "station_id": "KLAX",
      "observation_time": "2025-09-15T19:00:00Z",
      "temperature": 24,
      "dewpoint": 16,
      "wind_direction": 270,
      "wind_speed": 8,
      "visibility": 10,
      "flight_category": "VFR"
    },
    "weather_alerts": []
  }
}
```

#### Get Flight Position
```http
GET /api/flights/{aircraft_id}/position
```

Returns the current position of a specific flight.

**Response:**
```json
{
  "aircraft_id": "AAL123",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "altitude": 35000,
  "ground_speed": 450,
  "heading": 270,
  "vertical_rate": 0,
  "last_update": "2025-09-15T19:30:00Z"
}
```

#### Get Flight Track
```http
GET /api/flights/{aircraft_id}/track
```

Returns the historical track data for a specific flight.

**Response:**
```json
{
  "aircraft_id": "AAL123",
  "track_points": [
    {
      "timestamp": "2025-09-15T18:00:00Z",
      "latitude": 40.6413,
      "longitude": -73.7781,
      "altitude": 0,
      "ground_speed": 0
    },
    {
      "timestamp": "2025-09-15T18:30:00Z",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "altitude": 35000,
      "ground_speed": 450
    }
  ]
}
```

#### Get Flight Plan
```http
GET /api/flights/{aircraft_id}/flightplan
```

Returns the flight plan details for a specific flight.

**Response:**
```json
{
  "aircraft_id": "AAL123",
  "callsign": "American 123",
  "departure_airport": "KJFK",
  "arrival_airport": "KLAX",
  "departure_time": "2025-09-15T18:00:00Z",
  "arrival_time": "2025-09-15T21:30:00Z",
  "route": "KJFK DCT KLAX",
  "waypoints": [
    {
      "name": "KJFK",
      "latitude": 40.6413,
      "longitude": -73.7781,
      "type": "airport"
    },
    {
      "name": "KLAX",
      "latitude": 33.9425,
      "longitude": -118.4081,
      "type": "airport"
    }
  ]
}
```

### System Status

#### Health Check
```http
GET /health
```

Returns the overall system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-15T19:30:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "celery": "healthy",
    "solace": "healthy"
  }
}
```

#### System Status
```http
GET /api/status
```

Returns detailed system status information.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-15T19:30:00Z",
  "database": {
    "status": "connected",
    "flight_count": 150,
    "weather_count": 25
  },
  "services": {
    "celery_workers": 4,
    "active_tasks": 2,
    "solace_connection": "connected"
  },
  "performance": {
    "response_time": "45ms",
    "memory_usage": "512MB",
    "cpu_usage": "15%"
  }
}
```

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "timestamp": "2025-09-15T19:30:00Z"
}
```

### Common Error Codes

- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error
- `503` - Service Unavailable

## Rate Limiting

Currently, there are no rate limits imposed on the API. This may change in future versions.

## Data Formats

### Timestamps
All timestamps are in ISO 8601 format with UTC timezone:
```
2025-09-15T19:30:00Z
```

### Coordinates
- Latitude: Decimal degrees (-90 to 90)
- Longitude: Decimal degrees (-180 to 180)
- Altitude: Feet above sea level

### Airport Codes
- IATA codes (3 letters): JFK, LAX, ORD
- ICAO codes (4 letters): KJFK, KLAX, KORD

## Examples

### cURL Examples

Get current flights:
```bash
curl -X GET http://localhost:5500/api/flights/current
```

Get flight details:
```bash
curl -X GET http://localhost:5500/api/flights/AAL123/detail
```

Check system health:
```bash
curl -X GET http://localhost:5500/health
```

### JavaScript Examples

```javascript
// Get current flights
fetch('/api/flights/current')
  .then(response => response.json())
  .then(data => console.log(data));

// Get flight details
fetch('/api/flights/AAL123/detail')
  .then(response => response.json())
  .then(data => console.log(data));
```

### Python Examples

```python
import requests

# Get current flights
response = requests.get('http://localhost:5500/api/flights/current')
flights = response.json()

# Get flight details
response = requests.get('http://localhost:5500/api/flights/AAL123/detail')
flight_details = response.json()
```


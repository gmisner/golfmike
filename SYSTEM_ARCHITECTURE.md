# GolfMike Flight Tracker - System Architecture

## Overview
The GolfMike Flight Tracker is a comprehensive aviation data processing and visualization system that integrates real-time flight data, weather information, and route tracking capabilities.

## System Components

### 1. Data Sources
- **FAA SWIM (System Wide Information Management)**: Real-time flight data via Solace messaging
- **AviationWeather.gov API**: Standard aviation weather data (METAR, TAF, PIREP, AIRMET/SIGMET)
- **ITWS (Integrated Terminal Weather System)**: Real-time weather alerts via SOLUS queue

### 2. Core Services

#### 2.1 Data Ingestion
- **Solace Consumer** (`solace_consumer.py`): Connects to FAA SWIM for real-time flight data
- **Weather Subscription** (`gm_weather_sub.py`): Connects to ITWS SOLUS queue for weather alerts
- **Aviation Weather Fetcher** (`aviation_weather_fetcher.py`): Fetches data from AviationWeather.gov API

#### 2.2 Data Processing
- **XML Parsers** (`parsers/`): Parse incoming XML messages from various sources
- **Data Storers** (`storers/`): Store processed data in PostgreSQL database
- **Celery Tasks** (`tasks.py`): Background processing and scheduled data fetching

#### 2.3 API Layer
- **Flask Application** (`app_flask.py`): Main web application
- **Simple API** (`simple_api.py`): RESTful API endpoints for frontend
- **Flight Detail API**: Enhanced with weather data integration

#### 2.4 Frontend
- **Flight Tracker Dashboard** (`static/index.html`): Main flight tracking interface
- **Flight Detail Page** (`static/flight-detail.html`): Detailed flight information with weather
- **Flight Plan Lookup** (`static/flight-plan.html`): Search and view flight plans

## Database Architecture

### Core Flight Data Tables
- `aircraft`: Aircraft information and metadata
- `flight_plan`: Flight plan data and routes
- `track_information`: Real-time position and tracking data
- `status_updates`: Flight status changes (OOOI times)
- `flight_routes`: Normalized route information
- `route_waypoints`: Individual waypoints for routes

### Weather Data Tables

#### ITWS Real-time Weather (Original Tables)
- `weather_stations`: Weather station metadata
- `metar_data`: METAR observations
- `taf_data`: TAF forecasts
- `notam_data`: NOTAMs
- `weather_alert`: Weather alerts and warnings
- `weather_observation`: General weather observations

#### AviationWeather.gov API (Separate Tables)
- `weather_stations_api`: API weather station information
- `metar_data_api`: API METAR observations
- `taf_data_api`: API TAF forecasts
- `pirep_data_api`: Pilot reports
- `weather_alerts_api`: API weather alerts (AIRMET/SIGMET)
- `weather_observations_api`: API weather observations

## Data Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FAA SWIM      │    │ AviationWeather  │    │   ITWS SOLUS    │
│   (Flight Data) │    │      .gov API    │    │   (Weather)     │
│                 │    │  (Standard Data) │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Solace Consumer │    │ Weather Fetcher  │    │ Weather Sub     │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ XML Parsers     │    │ API Data         │    │ Weather Parser  │
│ (Flight Data)   │    │ Processing       │    │ (ITWS Data)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Data Storers    │    │ API Storers      │    │ Weather Storers │
│ (Flight Data)   │    │ (Standard Data)  │    │ (ITWS Data)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  ▼
                    ┌─────────────────────────┐
                    │   PostgreSQL Database   │
                    │                         │
                    │ • Flight Data Tables    │
                    │ • ITWS Weather Tables   │
                    │ • API Weather Tables    │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   Flask API Layer       │
                    │                         │
                    │ • Flight Detail API     │
                    │ • Weather Integration   │
                    │ • Real-time Updates     │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   Frontend Interface    │
                    │                         │
                    │ • Flight Tracker        │
                    │ • Flight Detail Pages   │
                    │ • Weather Display       │
                    │ • Interactive Maps      │
                    └─────────────────────────┘
```

## Technology Stack

### Backend
- **Python 3.x**: Core application language
- **Flask**: Web framework and API
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL**: Primary database
- **Celery**: Background task processing
- **Redis**: Message broker for Celery
- **Solace**: Message broker for FAA SWIM data

### Frontend
- **HTML5/CSS3**: Structure and styling
- **JavaScript (ES6+)**: Interactive functionality
- **Tabler.io**: UI framework and components
- **Leaflet.js**: Interactive maps
- **Bootstrap**: Responsive design

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Nginx**: Reverse proxy (if needed)

## Key Features

### 1. Real-time Flight Tracking
- Live aircraft positions
- Flight status updates
- Route visualization
- Historical track data

### 2. Weather Integration
- **Real-time ITWS Alerts**: Lightning, tornado, precipitation warnings
- **Standard Aviation Weather**: METAR, TAF, PIREP, AIRMET/SIGMET
- **Route-specific Weather**: Weather data for departure/arrival airports
- **Weather Alerts**: Active weather warnings and advisories

### 3. Flight Detail Pages
- Comprehensive flight information
- Weather data display
- OOOI (Out, Off, On, In) times
- Aircraft details
- Route information with waypoints

### 4. Data Processing
- **XML Parsing**: Robust parsing of various XML message formats
- **Data Validation**: Pydantic models for data validation
- **Error Handling**: Comprehensive error handling and logging
- **Data Deduplication**: Prevents duplicate data storage

## API Endpoints

### Flight Data
- `GET /api/flights` - Get current flights
- `GET /api/flights/<aircraft_id>/detail` - Get detailed flight information
- `GET /api/flights/<aircraft_id>/position` - Get current position
- `GET /api/flights/<aircraft_id>/track` - Get flight track
- `GET /api/flights/<aircraft_id>/flightplan` - Get flight plan
- `GET /api/flights/<aircraft_id>/recent` - Get recent flights

### Weather Data (Integrated)
- Weather data is integrated into flight detail endpoints
- Includes METAR, TAF, and weather alerts
- Combines both ITWS and API weather sources

## Scheduled Tasks

### Celery Beat Schedule
- **Weather Data Fetch**: Every 15 minutes
  - Fetches METAR, TAF, PIREP, AIRMET/SIGMET data
  - Updates weather database tables
- **Data Cleanup**: Daily
  - Removes old weather data
  - Maintains database performance

## Security & Performance

### Security
- Database connection pooling
- Input validation and sanitization
- Error handling without information disclosure

### Performance
- Database indexing for fast queries
- Connection pooling for database access
- Asynchronous processing with Celery
- Efficient data structures and algorithms

## Monitoring & Logging

### Logging
- Comprehensive logging throughout the system
- Structured logging with context
- Error tracking and debugging information

### Monitoring
- Connection status monitoring
- Data flow monitoring
- Performance metrics
- Health checks

## Deployment

### Docker Containers
- `golfmike-api`: Main Flask application
- `postgres`: PostgreSQL database
- `redis`: Redis message broker
- `celery-worker`: Background task processing
- `celery-beat`: Scheduled task management

### Environment Configuration
- Database connection settings
- Solace connection parameters
- API keys and credentials
- Logging configuration

## Future Enhancements

### Planned Features
- Historical data analysis
- Flight performance metrics
- Advanced weather routing
- Mobile application
- API rate limiting
- User authentication
- Data export capabilities

### Scalability Considerations
- Horizontal scaling with multiple workers
- Database sharding for large datasets
- Caching layer for frequently accessed data
- Load balancing for high availability

## Maintenance

### Regular Tasks
- Database maintenance and optimization
- Log rotation and cleanup
- Security updates
- Performance monitoring
- Data backup and recovery

### Troubleshooting
- Connection monitoring and auto-restart
- Error detection and recovery
- Data validation and integrity checks
- System health monitoring

---

*Last Updated: January 2025*
*Version: 1.0*



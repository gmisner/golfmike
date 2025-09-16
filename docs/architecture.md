# System Architecture

## Overview

GolfMike is built as a microservices architecture using Docker containers, providing scalability, maintainability, and easy deployment.

## Architecture Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   Mobile App    │    │   API Clients   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      Flask Web API        │
                    │     (Port 5500)           │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │     PostgreSQL DB         │
                    │   (Flight & Weather)      │
                    └─────────────┬─────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
┌─────────▼─────────┐    ┌─────────▼─────────┐    ┌─────────▼─────────┐
│  Celery Workers   │    │  Solace Consumer  │    │  Weather Services │
│  (Background)     │    │  (FAA SWIM)       │    │  (AviationWeather)│
└───────────────────┘    └───────────────────┘    └───────────────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │        Redis              │
                    │    (Message Broker)       │
                    └───────────────────────────┘
```

## Core Components

### 1. Flask Web API
- **File**: `app_flask.py`
- **Port**: 5500
- **Purpose**: Main web server and API endpoints
- **Features**:
  - RESTful API endpoints
  - Static file serving
  - Request routing and handling

### 2. PostgreSQL Database
- **Purpose**: Primary data storage
- **Tables**:
  - Flight data: `flight_plan`, `track_information`, `status_updates`
  - Weather data: `metar_data_api`, `taf_data_api`, `weather_alerts_api`
  - System data: `weather_alerts`, `weather_observations`

### 3. Celery Workers
- **Purpose**: Background task processing
- **Tasks**:
  - Data parsing and processing
  - Weather data fetching
  - Database operations
  - System maintenance

### 4. Solace Consumer
- **Purpose**: Real-time data ingestion from FAA SWIM
- **Features**:
  - Message queue processing
  - XML data parsing
  - Real-time flight data updates

### 5. Weather Services
- **Purpose**: Weather data collection and processing
- **Sources**:
  - AviationWeather.gov API
  - ITWS weather alerts
  - METAR/TAF data

### 6. Redis
- **Purpose**: Message broker for Celery
- **Features**:
  - Task queue management
  - Result storage
  - Caching

## Data Flow

1. **Real-time Data Ingestion**:
   - Solace Consumer receives FAA SWIM data
   - Data is parsed and validated
   - Processed data is stored in PostgreSQL

2. **Weather Data Collection**:
   - Weather services fetch data from external APIs
   - Data is processed and stored
   - Updates are triggered by Celery tasks

3. **API Requests**:
   - Web API receives requests from clients
   - Data is retrieved from PostgreSQL
   - Responses are formatted and returned

4. **Background Processing**:
   - Celery workers process queued tasks
   - Data parsing, validation, and storage
   - System maintenance and cleanup

## Technology Stack

### Backend
- **Python 3.10+**: Core programming language
- **Flask**: Web framework
- **SQLAlchemy**: ORM and database abstraction
- **Celery**: Distributed task queue
- **PostgreSQL**: Primary database
- **Redis**: Message broker and caching

### Frontend
- **HTML5/CSS3**: Web interface
- **JavaScript**: Interactive functionality
- **Bootstrap/Tabler.io**: UI framework
- **Leaflet**: Interactive maps

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Orchestration
- **Git**: Version control
- **GitHub**: Repository hosting

## Scalability Considerations

### Horizontal Scaling
- Multiple Celery workers can be deployed
- Database read replicas for read-heavy workloads
- Load balancing for web API instances

### Performance Optimization
- Database query optimization
- Caching strategies
- Background processing for heavy operations
- Efficient data parsing and storage

## Security

### Data Protection
- Environment variable configuration
- Database connection security
- API endpoint protection
- Input validation and sanitization

### Monitoring
- Comprehensive logging
- Error tracking and recovery
- System health monitoring
- Performance metrics

## Deployment

### Docker Configuration
- Multi-container setup
- Environment variable management
- Volume mounting for data persistence
- Network configuration for service communication

### Environment Setup
- Development environment with hot reloading
- Production environment with optimization
- Testing environment with isolated data


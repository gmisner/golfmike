# GolfMike - Flight Tracking Application

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A comprehensive flight tracking and weather monitoring system that integrates with FAA SWIM (System Wide Information Management) to provide real-time flight data, weather information, and aviation alerts.

## Features

- **Real-time Flight Tracking**: Live flight data from FAA SWIM
- **Weather Integration**: METAR, TAF, and weather alerts from AviationWeather.gov
- **ITWS Weather Alerts**: Real-time weather warnings and advisories
- **Interactive Web Interface**: Modern dashboard with flight search and details
- **Docker Support**: Easy deployment with Docker Compose
- **Database Integration**: PostgreSQL with optimized schemas
- **Background Processing**: Celery workers for data processing
- **Monitoring**: System health checks and logging

## System Architecture

The system consists of several key components:

- **Flask API**: RESTful API for flight and weather data
- **PostgreSQL Database**: Stores flight plans, tracks, and weather data
- **Celery Workers**: Background processing for data ingestion
- **Solace Consumer**: Real-time data from FAA SWIM
- **Weather Services**: METAR/TAF data and ITWS alerts
- **Web Interface**: Bootstrap/Tabler.io frontend

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/gmisner/golfmike.git
cd golfmike
```

2. Start the system:
```bash
docker-compose up -d
```

3. Access the web interface:
- Main Dashboard: http://localhost:5500
- Flight Details: http://localhost:5500/flight-detail.html
- API Health: http://localhost:5500/health

### Configuration

The system uses environment variables for configuration. Key settings:

- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `SOLACE_HOST`: Solace message broker host
- `SOLACE_USERNAME`: Solace username
- `SOLACE_PASSWORD`: Solace password

## API Endpoints

- `GET /api/flights/current` - Get current flights
- `GET /api/flights/{aircraft_id}/detail` - Get flight details with weather
- `GET /api/flights/{aircraft_id}/position` - Get current position
- `GET /api/flights/{aircraft_id}/track` - Get flight track
- `GET /api/flights/{aircraft_id}/flightplan` - Get flight plan
- `GET /health` - System health check

## Weather Data

The system provides comprehensive weather information:

- **METAR**: Current weather conditions at airports
- **TAF**: Terminal aerodrome forecasts
- **Weather Alerts**: AIRMET, SIGMET, and ITWS alerts
- **Real-time Updates**: Automatic data refresh from multiple sources

## Development

### Project Structure

```
golfmike/
├── .devcontainer/          # Docker configuration
├── models/                 # Database models
├── parsers/               # XML data parsers
├── storers/               # Data storage handlers
├── static/                # Web interface files
├── utils/                 # Utility functions
├── app_flask.py           # Flask application
├── simple_api.py          # API endpoints
└── docker-compose.yml     # Container orchestration
```

### Running Tests

```bash
# Run system health check
python check_system_status.py

# Test weather API
python test_weather_api.py
```

### Database Management

```bash
# Create weather tables
python create_weather_api_tables.py

# Check database status
docker exec postgres psql -U postgres -d postgres -c "SELECT COUNT(*) FROM track_information;"
```

## Monitoring

The system includes comprehensive monitoring:

- **Health Checks**: API endpoint monitoring
- **Logging**: Structured logging with timestamps
- **Error Handling**: Graceful error recovery
- **Performance Metrics**: Database query optimization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the system logs: `docker-compose logs`
- Review the documentation in the `docs/` directory

## Roadmap

- [ ] Enhanced weather visualization
- [ ] Mobile-responsive interface
- [ ] Historical data analysis
- [ ] Performance optimizations
- [ ] Additional data sources
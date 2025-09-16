# Docker Setup Guide

## Overview

GolfMike is designed to run in Docker containers for easy deployment and consistency across different environments.

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- Git

## Quick Start

1. **Clone the repository:**
```bash
git clone https://github.com/gmisner/golfmike.git
cd golfmike
```

2. **Start the system:**
```bash
docker-compose up -d
```

3. **Access the web interface:**
- Main Dashboard: http://localhost:5500
- Flight Details: http://localhost:5500/flight-detail.html
- API Health: http://localhost:5500/health

## Docker Services

### Web API (`web_api`)
- **Image**: Custom Flask application
- **Port**: 5500
- **Purpose**: Main web server and API endpoints
- **Dependencies**: PostgreSQL, Redis

### PostgreSQL (`postgres`)
- **Image**: `postgres:15`
- **Port**: 5432
- **Purpose**: Primary database
- **Volumes**: Data persistence
- **Environment Variables**:
  - `POSTGRES_DB`: Database name
  - `POSTGRES_USER`: Database user
  - `POSTGRES_PASSWORD`: Database password

### Redis (`redis`)
- **Image**: `redis:7-alpine`
- **Port**: 6379
- **Purpose**: Message broker for Celery
- **Volumes**: Data persistence

### Celery Workers (`celery_worker`, `celery_worker_2`, etc.)
- **Image**: Custom Python application
- **Purpose**: Background task processing
- **Dependencies**: Redis, PostgreSQL
- **Scaling**: Multiple worker instances

### Solace Consumer (`bigtitties`)
- **Image**: Custom Python application
- **Purpose**: Real-time data ingestion from FAA SWIM
- **Dependencies**: PostgreSQL, Redis

### Flower (`flower`)
- **Image**: Custom Python application
- **Port**: 5555
- **Purpose**: Celery monitoring and management
- **Dependencies**: Redis

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database Configuration
POSTGRES_DB=golfmike
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Solace Configuration
SOLACE_HOST=your_solace_host
SOLACE_USERNAME=your_username
SOLACE_PASSWORD=your_password

# Weather API Configuration
AVIATION_WEATHER_API_KEY=your_api_key

# Application Configuration
FLASK_ENV=production
FLASK_DEBUG=False
```

### Docker Compose Configuration

The `docker-compose.yml` file defines all services:

```yaml
version: '3.8'

services:
  web_api:
    build: .
    ports:
      - "5500:5500"
    depends_on:
      - postgres
      - redis
    environment:
      - FLASK_ENV=production
    volumes:
      - ./static:/app/static

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  celery_worker:
    build: .
    command: celery -A celery_app worker --loglevel=info
    depends_on:
      - postgres
      - redis
    volumes:
      - .:/app

  bigtitties:
    build: .
    command: python solace_consumer.py
    depends_on:
      - postgres
      - redis
    volumes:
      - .:/app

  flower:
    build: .
    command: celery -A celery_app flower
    ports:
      - "5555:5555"
    depends_on:
      - redis

volumes:
  postgres_data:
  redis_data:
```

## Deployment Commands

### Start Services
```bash
# Start all services in background
docker-compose up -d

# Start with logs
docker-compose up

# Start specific service
docker-compose up web_api
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop specific service
docker-compose stop web_api
```

### View Logs
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs web_api

# Follow logs in real-time
docker-compose logs -f web_api
```

### Scale Services
```bash
# Scale Celery workers
docker-compose up -d --scale celery_worker=4

# Scale web API (with load balancer)
docker-compose up -d --scale web_api=3
```

## Database Management

### Initialize Database
```bash
# Run database initialization
docker-compose exec web_api python create_weather_api_tables.py

# Check database status
docker-compose exec postgres psql -U postgres -d postgres -c "SELECT COUNT(*) FROM track_information;"
```

### Database Backup
```bash
# Create backup
docker-compose exec postgres pg_dump -U postgres postgres > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U postgres postgres < backup.sql
```

### Database Access
```bash
# Connect to database
docker-compose exec postgres psql -U postgres -d postgres

# Run SQL commands
docker-compose exec postgres psql -U postgres -d postgres -c "SELECT * FROM flight_plan LIMIT 5;"
```

## Monitoring

### Service Status
```bash
# Check service status
docker-compose ps

# Check resource usage
docker stats

# Check service health
curl http://localhost:5500/health
```

### Celery Monitoring
- **Flower Interface**: http://localhost:5555
- **View active tasks**
- **Monitor worker status**
- **Check task history**

### Log Monitoring
```bash
# View application logs
docker-compose logs web_api

# View database logs
docker-compose logs postgres

# View Redis logs
docker-compose logs redis
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   - Check if ports 5500, 5432, 6379, 5555 are available
   - Modify ports in `docker-compose.yml` if needed

2. **Database Connection Issues**
   - Verify PostgreSQL is running: `docker-compose ps postgres`
   - Check database logs: `docker-compose logs postgres`
   - Verify environment variables

3. **Service Startup Issues**
   - Check service logs: `docker-compose logs [service_name]`
   - Verify dependencies are running
   - Check resource availability

4. **Data Persistence Issues**
   - Verify volumes are mounted correctly
   - Check volume permissions
   - Ensure data directory exists

### Debug Commands

```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs [service_name]

# Execute commands in container
docker-compose exec web_api bash

# Check resource usage
docker stats

# View network configuration
docker network ls
docker network inspect golfmike_default
```

### Performance Tuning

1. **Database Optimization**
   - Increase PostgreSQL memory settings
   - Optimize query performance
   - Add database indexes

2. **Celery Optimization**
   - Increase worker count
   - Optimize task processing
   - Configure task routing

3. **Resource Allocation**
   - Increase container memory limits
   - Optimize CPU usage
   - Configure swap space

## Production Deployment

### Security Considerations
- Use strong passwords
- Enable SSL/TLS
- Configure firewall rules
- Regular security updates

### Backup Strategy
- Regular database backups
- Configuration backup
- Log retention policy
- Disaster recovery plan

### Monitoring
- Health check endpoints
- Log aggregation
- Performance metrics
- Alert configuration

### Scaling
- Horizontal scaling with load balancer
- Database read replicas
- Caching strategies
- CDN for static assets


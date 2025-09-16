# Docker Setup Guide for GolfMike

## Prerequisites
1. Docker Desktop must be running
2. All dependencies are configured in the Docker containers

## Quick Start

### 1. Start Docker Desktop
- Open Docker Desktop from Applications
- Wait for it to fully start (you'll see the Docker icon in your menu bar)
- Make sure it shows "Docker Desktop is running"

### 2. Build and Run the System
```bash
# Navigate to your project directory
cd /Users/gmisner/Documents/GolfMike

# Build and start all services
docker-compose -f .devcontainer/docker-compose.yml up --build -d

# Check if all containers are running
docker-compose -f .devcontainer/docker-compose.yml ps

# View logs
docker-compose -f .devcontainer/docker-compose.yml logs -f
```

### 3. Access the Services

#### Web API
- **URL**: http://localhost:5500
- **Endpoints**:
  - `GET /health` - System health check
  - `GET /metrics` - System metrics
  - `GET /stats` - Processing statistics
  - `POST /process` - Process XML data
  - `GET /result/<task_id>` - Get task result

#### Flower (Celery Monitoring)
- **URL**: http://localhost:5555
- **Purpose**: Monitor Celery tasks and workers

#### Database
- **Host**: localhost
- **Port**: 15432
- **Database**: postgres
- **Username**: postgres
- **Password**: password

#### Redis
- **Host**: localhost
- **Port**: 6379

### 4. Test the System

#### Test the API
```bash
# Health check
curl http://localhost:5500/health

# Get metrics
curl http://localhost:5500/metrics

# Get stats
curl http://localhost:5500/stats
```

#### Test Celery Workers
```bash
# Check worker status
docker-compose -f .devcontainer/docker-compose.yml exec celery_worker celery -A celery_app inspect active

# Check queues
docker-compose -f .devcontainer/docker-compose.yml exec celery_worker celery -A celery_app inspect stats
```

### 5. Monitor the System

#### View Logs
```bash
# All services
docker-compose -f .devcontainer/docker-compose.yml logs -f

# Specific service
docker-compose -f .devcontainer/docker-compose.yml logs -f celery_worker

# Web API
docker-compose -f .devcontainer/docker-compose.yml logs -f web_api
```

#### Check Resource Usage
```bash
# Container stats
docker stats

# Specific container
docker stats golfmike-api
```

### 6. Stop the System
```bash
# Stop all services
docker-compose -f .devcontainer/docker-compose.yml down

# Stop and remove volumes (WARNING: This will delete database data)
docker-compose -f .devcontainer/docker-compose.yml down -v
```

## Troubleshooting

### Docker Desktop Issues
1. **Docker not starting**: Restart Docker Desktop
2. **Permission issues**: Make sure Docker Desktop has proper permissions
3. **Resource issues**: Increase Docker Desktop memory allocation in settings

### Container Issues
1. **Build failures**: Check Dockerfile and requirements.txt
2. **Connection issues**: Ensure all services are running
3. **Database issues**: Check PostgreSQL container logs

### Common Commands
```bash
# Rebuild specific service
docker-compose -f .devcontainer/docker-compose.yml up --build celery_worker

# Restart specific service
docker-compose -f .devcontainer/docker-compose.yml restart celery_worker

# Execute command in running container
docker-compose -f .devcontainer/docker-compose.yml exec celery_worker bash

# View container logs
docker logs <container_name>
```

## Architecture Overview

The system consists of:
- **4 Celery Workers**: Process XML messages from FAA SWIM
- **1 Web API**: Provides REST endpoints for monitoring and task management
- **1 PostgreSQL Database**: Stores processed flight data
- **1 Redis**: Message broker for Celery
- **1 Flower**: Web UI for monitoring Celery tasks

## Performance Optimizations Applied

1. **Database Connection Pooling**: Optimized for 4 workers
2. **Celery Configuration**: Enhanced for better throughput
3. **XML Parsing**: Cached parsers and optimized parsing
4. **Error Handling**: Circuit breakers and retry mechanisms
5. **Monitoring**: Comprehensive health checks and metrics
6. **Resource Limits**: Proper memory and CPU limits for containers

## Next Steps

1. Start Docker Desktop
2. Run the build command
3. Test the health endpoint
4. Monitor the Flower dashboard
5. Start processing FAA SWIM data




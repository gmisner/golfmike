# Centralized Logging Setup

## Overview

All services in GolfMike use **loguru** for consistent, structured logging. Logs are centralized through Docker's logging driver for easy troubleshooting.

## Logging Standards

### Using Loguru

**Always import:**
```python
from utils.logger import main_logger as logger
```

**Never use:**
```python
import logging  # ❌ Don't use standard logging
```

The `utils/logger.py` automatically intercepts standard Python logging and routes it through loguru, so even third-party libraries will use loguru.

### Log Levels

- `logger.debug()` - Detailed debugging information
- `logger.info()` - General informational messages
- `logger.success()` - Successful operations
- `logger.warning()` - Warning messages
- `logger.error()` - Error messages
- `logger.exception()` - Exception with full traceback

### Structured Logging

```python
# With context
logger.bind(aircraft_id="N12345", gufi="ABC123").info("Processing flight plan")

# With exception
try:
    process_data()
except Exception as e:
    logger.opt(exception=True).error("Failed to process data")
```

## Docker Logging

### Configuration

All services use centralized logging via `docker-compose.yml`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"    # Max log file size
    max-file: "5"      # Number of rotated files to keep
    labels: "service,environment"
    tag: "{{.Name}}"   # Tag with container name
```

### Viewing Logs

Use the centralized log viewer script:

```bash
# View all services
./view_logs.sh all

# View specific service
./view_logs.sh traffic_consumer

# Follow logs in real-time
./view_logs.sh traffic_consumer --follow

# View last N lines
./view_logs.sh web_api --tail 200
```

### Direct Docker Commands

```bash
# View logs for all services
docker-compose -f .devcontainer/docker-compose.yml logs

# View logs for specific service
docker-compose -f .devcontainer/docker-compose.yml logs traffic_consumer

# Follow logs
docker-compose -f .devcontainer/docker-compose.yml logs -f traffic_consumer

# View last 100 lines
docker-compose -f .devcontainer/docker-compose.yml logs --tail=100 traffic_consumer

# View logs with timestamps
docker-compose -f .devcontainer/docker-compose.yml logs -t traffic_consumer
```

### Log Locations

Docker stores logs in:
- Linux: `/var/lib/docker/containers/<container-id>/<container-id>-json.log`
- macOS/Windows: Managed by Docker Desktop

Access via Docker commands (recommended) rather than direct file access.

## Log Format

Loguru format (configured in `utils/logger.py`):
```
{time:MMMM D, YYYY > HH:mm:ss!UTC} | {level} | {message}
```

Example:
```
December 5, 2025 > 17:30:08 | INFO | Processing flight plan for N2115B
```

## Troubleshooting

### Check if service is logging
```bash
docker-compose -f .devcontainer/docker-compose.yml logs --tail=50 <service_name>
```

### Search logs for specific text
```bash
docker-compose -f .devcontainer/docker-compose.yml logs | grep "N2115B"
```

### View logs from specific time
```bash
docker-compose -f .devcontainer/docker-compose.yml logs --since 10m traffic_consumer
```

### Clear old logs (restart containers)
```bash
docker-compose -f .devcontainer/docker-compose.yml down
docker-compose -f .devcontainer/docker-compose.yml up -d
```

## Best Practices

1. **Always use loguru** - Never import `logging` directly
2. **Use appropriate log levels** - Don't log everything as INFO
3. **Include context** - Use `logger.bind()` for structured data
4. **Log exceptions properly** - Use `logger.opt(exception=True)` or `logger.exception()`
5. **Don't log sensitive data** - Never log passwords, API keys, etc.
6. **Use descriptive messages** - Make logs searchable and meaningful

## Migration Notes

If you find code using standard `logging`:

1. Replace `import logging` with `from utils.logger import main_logger as logger`
2. Replace `logging.info()` with `logger.info()`
3. Replace `logging.getLogger()` with direct `logger` usage
4. The intercept handler will catch any remaining standard logging calls


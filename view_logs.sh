#!/bin/bash
# Centralized log viewer for all Docker services
# Usage: ./view_logs.sh [service_name] [--follow] [--tail N]

SERVICE="${1:-}"
FOLLOW="${2:-}"
TAIL="${3:-100}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== GolfMike Docker Logs Viewer ===${NC}\n"

if [ -z "$SERVICE" ]; then
    echo -e "${YELLOW}Available services:${NC}"
    echo "  - traffic_consumer"
    echo "  - weather_consumer"
    echo "  - celery_worker"
    echo "  - web_api"
    echo "  - redis"
    echo "  - postgres"
    echo ""
    echo -e "${GREEN}Usage:${NC}"
    echo "  ./view_logs.sh [service_name] [--follow] [--tail N]"
    echo ""
    echo -e "${GREEN}Examples:${NC}"
    echo "  ./view_logs.sh traffic_consumer --follow"
    echo "  ./view_logs.sh web_api --tail 50"
    echo "  ./view_logs.sh all  # View all services"
    exit 0
fi

if [ "$SERVICE" == "all" ]; then
    echo -e "${GREEN}Viewing logs from all services...${NC}\n"
    docker-compose -f .devcontainer/docker-compose.yml logs --tail=$TAIL $FOLLOW
else
    echo -e "${GREEN}Viewing logs for: $SERVICE${NC}\n"
    if [ "$FOLLOW" == "--follow" ] || [ "$FOLLOW" == "-f" ]; then
        docker-compose -f .devcontainer/docker-compose.yml logs --tail=$TAIL --follow $SERVICE
    else
        docker-compose -f .devcontainer/docker-compose.yml logs --tail=$TAIL $SERVICE
    fi
fi

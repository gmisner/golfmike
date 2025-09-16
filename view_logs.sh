#!/bin/bash

# Centralized Log Viewer for GolfMike Application
# This script provides different ways to view logs from all services

echo "🔍 GolfMike Centralized Log Viewer"
echo "=================================="
echo ""

# Function to show all logs
show_all_logs() {
    echo "📋 All Services Logs (last 50 lines):"
    echo "-------------------------------------"
    docker-compose -f .devcontainer/docker-compose.yml logs --tail=50
}

# Function to show logs by service
show_service_logs() {
    local service=$1
    echo "📋 $service Logs (last 30 lines):"
    echo "--------------------------------"
    docker-compose -f .devcontainer/docker-compose.yml logs --tail=30 $service
}

# Function to show flight plan specific logs
show_flight_plan_logs() {
    echo "✈️  Flight Plan Related Logs:"
    echo "-----------------------------"
    docker-compose -f .devcontainer/docker-compose.yml logs --tail=100 | grep -E "(FLIGHT PLAN|📋|🔄|✅|process_flight_plan_xml|Celery task.*started)"
}

# Function to show weather specific logs
show_weather_logs() {
    echo "🌤️  Weather Related Logs:"
    echo "-------------------------"
    docker-compose -f .devcontainer/docker-compose.yml logs --tail=100 | grep -E "(WEATHER|🌤️|weather|WeatherXMLParser|WeatherDataStorer)"
}

# Function to show all consumer logs
show_consumer_logs() {
    echo "📡 All Solace Consumer Logs:"
    echo "----------------------------"
    docker-compose -f .devcontainer/docker-compose.yml logs --tail=50 traffic_consumer weather_consumer flight_plan_consumer
}

# Function to show enhanced consumer monitoring
show_enhanced_monitoring() {
    echo "🔍 Enhanced Consumer Monitoring:"
    echo "--------------------------------"
    echo "Checking consumer processes..."
    docker-compose -f .devcontainer/docker-compose.yml exec web_api ps aux | grep -E "(traffic_consumer|weather_consumer|flight_plan_consumer)" | grep -v grep
    echo ""
    echo "Recent connection events:"
    docker-compose -f .devcontainer/docker-compose.yml logs --tail=20 web_api | grep -E "(connected|disconnected|reconnected|retry|error|Error)" | tail -10
}

# Function to show error logs
show_error_logs() {
    echo "❌ Error Logs (last 50 lines):"
    echo "------------------------------"
    docker-compose -f .devcontainer/docker-compose.yml logs --tail=100 | grep -E "(ERROR|Exception|Traceback|FAILED)"
}

# Function to follow logs in real-time
follow_logs() {
    echo "👀 Following All Logs (Press Ctrl+C to stop):"
    echo "---------------------------------------------"
    docker-compose -f .devcontainer/docker-compose.yml logs -f
}

# Main menu
case "${1:-menu}" in
    "all")
        show_all_logs
        ;;
    "web")
        show_service_logs "web_api"
        ;;
    "worker")
        show_service_logs "celery_worker"
        ;;
    "workers")
        echo "📋 All Celery Workers Logs:"
        echo "---------------------------"
        docker-compose -f .devcontainer/docker-compose.yml logs --tail=30 celery_worker celery_worker_2 celery_worker_3 celery_worker_4
        ;;
    "flight")
        show_flight_plan_logs
        ;;
        "weather")
            show_weather_logs
            ;;
        "consumers")
            show_consumer_logs
            ;;
        "monitor")
            show_enhanced_monitoring
            ;;
    "errors")
        show_error_logs
        ;;
    "follow")
        follow_logs
        ;;
    "menu"|*)
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  all       - Show logs from all services (last 50 lines)"
        echo "  web       - Show web API logs"
        echo "  worker    - Show main Celery worker logs"
        echo "  workers   - Show all Celery worker logs"
        echo "  flight    - Show flight plan related logs"
        echo "  weather   - Show weather related logs"
        echo "  consumers - Show all Solace consumer logs"
        echo "  monitor   - Show enhanced consumer monitoring"
        echo "  errors    - Show error logs only"
        echo "  follow   - Follow all logs in real-time"
        echo "  menu     - Show this help menu"
        echo ""
        echo "Examples:"
        echo "  $0 all"
        echo "  $0 flight"
        echo "  $0 follow"
        ;;
esac

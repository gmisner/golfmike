#!/bin/bash

# Docker Compose Configuration Switcher
# Usage: ./docker-switch.sh [original|optimized]

set -e

ORIGINAL_CONFIG=".devcontainer/docker-compose.yml"
OPTIMIZED_CONFIG=".devcontainer/docker-compose.optimized.yml"

function show_usage() {
    echo "Usage: $0 [original|optimized]"
    echo ""
    echo "  original  - Use the original Docker Compose configuration"
    echo "  optimized - Use the optimized Docker Compose configuration"
    echo ""
    echo "Current configuration: $(get_current_config)"
}

function get_current_config() {
    if docker-compose -f "$OPTIMIZED_CONFIG" ps >/dev/null 2>&1; then
        echo "optimized"
    elif docker-compose -f "$ORIGINAL_CONFIG" ps >/dev/null 2>&1; then
        echo "original"
    else
        echo "none"
    fi
}

function stop_all_services() {
    echo "Stopping all services..."
    docker-compose -f "$ORIGINAL_CONFIG" down 2>/dev/null || true
    docker-compose -f "$OPTIMIZED_CONFIG" down 2>/dev/null || true
}

function start_services() {
    local config=$1
    echo "Starting services with $config configuration..."
    
    if [ "$config" = "optimized" ]; then
        docker-compose -f "$OPTIMIZED_CONFIG" up -d
    else
        docker-compose -f "$ORIGINAL_CONFIG" up -d
    fi
    
    echo "Services started successfully!"
    echo ""
    echo "Service Status:"
    if [ "$config" = "optimized" ]; then
        docker-compose -f "$OPTIMIZED_CONFIG" ps
    else
        docker-compose -f "$ORIGINAL_CONFIG" ps
    fi
}

function show_status() {
    echo "Current configuration: $(get_current_config)"
    echo ""
    echo "Available configurations:"
    echo "  - original:  Standard configuration with basic resource limits"
    echo "  - optimized: Optimized configuration with better resource management"
    echo ""
    echo "To switch configurations:"
    echo "  $0 original   # Switch to original configuration"
    echo "  $0 optimized  # Switch to optimized configuration"
}

# Main script logic
case "${1:-}" in
    "original")
        stop_all_services
        start_services "original"
        ;;
    "optimized")
        stop_all_services
        start_services "optimized"
        ;;
    "status"|"")
        show_status
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        echo "Error: Unknown option '$1'"
        echo ""
        show_usage
        exit 1
        ;;
esac


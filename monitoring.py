# monitoring.py
import time
import psutil
from typing import Dict, Any
from utils.logger import main_logger as logger
from celery_app import app as celery_app
from db_config import SessionLocal
from sqlalchemy import text
from error_handling import error_tracker


class SystemMonitor:
    """System monitoring utilities for GolfMike application."""

    @staticmethod
    def get_system_metrics() -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            # CPU and Memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            # Database connection pool status
            db_metrics = SystemMonitor._get_database_metrics()

            # Celery worker status
            celery_metrics = SystemMonitor._get_celery_metrics()

            # Error tracking metrics
            error_metrics = error_tracker.get_error_summary()

            return {
                "timestamp": time.time(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "memory_used_gb": round(memory.used / (1024**3), 2),
                },
                "database": db_metrics,
                "celery": celery_metrics,
                "errors": error_metrics,
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {"error": str(e)}

    @staticmethod
    def _get_database_metrics() -> Dict[str, Any]:
        """Get database connection pool metrics."""
        try:
            with SessionLocal() as session:
                # Get connection pool status
                pool = session.bind.pool
                return {
                    "pool_size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid(),
                }
        except Exception as e:
            logger.error(f"Error getting database metrics: {e}")
            return {"error": str(e)}

    @staticmethod
    def _get_celery_metrics() -> Dict[str, Any]:
        """Get Celery worker and task metrics."""
        try:
            inspect = celery_app.control.inspect()

            # Get active tasks
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()
            reserved_tasks = inspect.reserved()

            # Count tasks by queue
            task_counts = {}
            if active_tasks:
                for worker, tasks in active_tasks.items():
                    for task in tasks:
                        queue = task.get("delivery_info", {}).get(
                            "routing_key", "unknown"
                        )
                        task_counts[queue] = task_counts.get(queue, 0) + 1

            return {
                "active_workers": len(active_tasks) if active_tasks else 0,
                "active_tasks": sum(
                    len(tasks) for tasks in (active_tasks or {}).values()
                ),
                "scheduled_tasks": sum(
                    len(tasks) for tasks in (scheduled_tasks or {}).values()
                ),
                "reserved_tasks": sum(
                    len(tasks) for tasks in (reserved_tasks or {}).values()
                ),
                "task_counts_by_queue": task_counts,
            }
        except Exception as e:
            logger.error(f"Error getting Celery metrics: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_processing_stats() -> Dict[str, Any]:
        """Get message processing statistics."""
        try:
            with SessionLocal() as session:
                # Get counts from different tables (adjust table names as needed)
                stats = {}

                # Example queries - adjust based on your actual table structure
                tables_to_check = [
                    "tmi_flight_list",
                    "flight_sectors",
                    "track_information",
                    "status",
                ]

                for table in tables_to_check:
                    try:
                        result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        stats[f"{table}_count"] = count
                    except Exception as e:
                        logger.debug(f"Could not get count for table {table}: {e}")
                        stats[f"{table}_count"] = 0

                return stats
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {"error": str(e)}


def log_system_health():
    """Log system health metrics."""
    metrics = SystemMonitor.get_system_metrics()
    logger.info(f"System Health: {metrics}")


def get_health_status() -> Dict[str, Any]:
    """Get overall health status of the system."""
    metrics = SystemMonitor.get_system_metrics()
    processing_stats = SystemMonitor.get_processing_stats()

    # Determine health status
    health_status = "healthy"
    issues = []

    # Check CPU usage
    if metrics.get("system", {}).get("cpu_percent", 0) > 80:
        health_status = "warning"
        issues.append("High CPU usage")

    # Check memory usage
    if metrics.get("system", {}).get("memory_percent", 0) > 85:
        health_status = "warning"
        issues.append("High memory usage")

    # Check database pool
    db_metrics = metrics.get("database", {})
    if db_metrics.get("checked_out", 0) > db_metrics.get("pool_size", 0) * 0.8:
        health_status = "warning"
        issues.append("High database connection usage")

    return {
        "status": health_status,
        "issues": issues,
        "metrics": metrics,
        "processing_stats": processing_stats,
        "timestamp": time.time(),
    }

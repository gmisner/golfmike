# error_handling.py
import time
from typing import Callable, Any, Optional
from functools import wraps
from utils.logger import main_logger as logger
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError


class CircuitBreaker:
    """Circuit breaker pattern implementation for handling failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN state")
            else:
                time_remaining = self.recovery_timeout - (time.time() - self.last_failure_time)
                raise Exception(f"Circuit breaker is OPEN - service unavailable (recovery in {time_remaining:.1f}s)")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("Circuit breaker reset to CLOSED state")
            # Reset failure count on success
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )

            raise e
    
    def reset(self):
        """Manually reset the circuit breaker to CLOSED state."""
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker manually reset to CLOSED state")
    
    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "recovery_timeout": self.recovery_timeout,
        }


# Global circuit breakers for different services
db_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
solace_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
):
    """Decorator for retrying functions with exponential backoff."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise e

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base**attempt), max_delay)

                    # Add jitter to prevent thundering herd
                    if jitter:
                        import random

                        delay *= 0.5 + random.random() * 0.5

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


def handle_database_errors(func: Callable) -> Callable:
    """Decorator for handling database-specific errors."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DisconnectionError as e:
            logger.error(f"Database connection lost: {e}")
            raise Exception(
                "Database connection lost - service temporarily unavailable"
            )
        except OperationalError as e:
            logger.error(f"Database operational error: {e}")
            raise Exception(
                "Database operational error - service temporarily unavailable"
            )
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy error: {e}")
            raise Exception("Database error occurred")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise e

    return wrapper


def safe_execute(func: Callable, *args, **kwargs) -> tuple[bool, Any]:
    """Safely execute a function and return success status with result."""
    try:
        result = func(*args, **kwargs)
        return True, result
    except Exception as e:
        logger.error(f"Error in safe_execute for {func.__name__}: {e}")
        return False, e


class ErrorTracker:
    """Track and analyze error patterns."""

    def __init__(self, max_errors: int = 1000):
        self.max_errors = max_errors
        self.errors = []
        self.error_counts = {}

    def record_error(
        self, error_type: str, error_message: str, context: Optional[dict] = None
    ):
        """Record an error for analysis."""
        error_record = {
            "timestamp": time.time(),
            "type": error_type,
            "message": error_message,
            "context": context or {},
        }

        self.errors.append(error_record)
        if len(self.errors) > self.max_errors:
            self.errors.pop(0)

        # Count error types
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

    def get_error_summary(self) -> dict:
        """Get summary of recent errors."""
        recent_errors = [
            e for e in self.errors if time.time() - e["timestamp"] < 3600
        ]  # Last hour

        return {
            "total_errors": len(self.errors),
            "recent_errors": len(recent_errors),
            "error_counts": self.error_counts,
            "most_common_error": (
                max(self.error_counts.items(), key=lambda x: x[1])
                if self.error_counts
                else None
            ),
        }


# Global error tracker
error_tracker = ErrorTracker()


def track_errors(error_type: str):
    """Decorator to track errors."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_tracker.record_error(
                    error_type, str(e), {"function": func.__name__}
                )
                raise e

        return wrapper

    return decorator




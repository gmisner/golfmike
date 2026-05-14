"""Timing helpers for database write paths (structured loguru logs)."""

import os
import time
from contextlib import contextmanager
from typing import Any, Iterator

from utils.logger import main_logger as logger

_SLOW_MS = float(os.environ.get("DB_SLOW_QUERY_MS", "200"))
_ENABLED = os.environ.get("DB_METRICS", "1").lower() in ("1", "true", "yes")


@contextmanager
def log_db_write_duration(operation: str, **context: Any) -> Iterator[None]:
    """
    Log wall time for a block of DB work. Warnings when duration >= DB_SLOW_QUERY_MS.

    Env:
        DB_METRICS: set to 0/false/no to disable.
        DB_SLOW_QUERY_MS: threshold in ms for warning (default 200).
    """
    if not _ENABLED:
        yield
        return
    t0 = time.perf_counter()
    try:
        yield
    finally:
        ms = (time.perf_counter() - t0) * 1000
        bound = logger.bind(db_operation=operation, duration_ms=round(ms, 2), **context)
        if ms >= _SLOW_MS:
            bound.warning("slow database write")
        else:
            bound.debug("database write completed")

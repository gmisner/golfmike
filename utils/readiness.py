"""Shared readiness checks for HTTP probes (load balancers, orchestrators)."""

from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


def database_connection_ok() -> Tuple[bool, Optional[str]]:
    """
    Return ``(True, None)`` if the configured SQLAlchemy engine can run ``SELECT 1``.

    On failure returns ``(False, error_message)``.
    """
    try:
        from db_config import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except SQLAlchemyError as e:
        return False, str(e)
    except Exception as e:  # pylint: disable=broad-except
        return False, str(e)

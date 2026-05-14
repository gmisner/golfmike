#!/usr/bin/env python3
"""
Apply migrations/002_flight_hub_flight_plan_fk.sql.

Prerequisites: `flights` and related hub tables exist (e.g. run create_improved_relationships.sql first).
Uses db_config engine (same as the app).
"""

from pathlib import Path

from sqlalchemy import text

from db_config import engine
from utils.logger import main_logger as logger


def _sql_statements(sql: str) -> list[str]:
    """Split DDL file on semicolon-terminated lines (no functions in this migration)."""
    statements: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            buf = []
            if stmt:
                statements.append(stmt)
    if buf:
        stmt = "\n".join(buf).strip().rstrip(";").strip()
        if stmt:
            statements.append(stmt)
    return statements


def main() -> None:
    sql_path = Path(__file__).resolve().parent / "migrations" / "002_flight_hub_flight_plan_fk.sql"
    if not sql_path.is_file():
        logger.error("Migration file not found: {}", sql_path)
        raise SystemExit(1)

    sql = sql_path.read_text(encoding="utf-8")
    logger.info("Applying flight hub migration from {}", sql_path)

    stmts = _sql_statements(sql)
    with engine.begin() as conn:
        for i, stmt in enumerate(stmts, 1):
            logger.debug("Executing statement {}/{}", i, len(stmts))
            conn.execute(text(stmt))

    logger.success("Flight hub migration completed.")


if __name__ == "__main__":
    main()

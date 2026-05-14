"""Helpers for normalizing aircraft identifiers from upstream feeds."""

from __future__ import annotations

import re


def normalize_aircraft_id(raw: str | None) -> str | None:
    """
    Normalize aircraft IDs for storage.

    - Always trims and uppercases.
    - For US registrations (N-numbers), removes separators like '-' and spaces.
      Example: ``N121-JS`` -> ``N121JS``.
    - Leaves non-US callsigns/IDs unchanged except trim+uppercase.
    """
    if raw is None:
        return None
    s = str(raw).strip().upper()
    if not s:
        return None

    if s.startswith("N"):
        compact = re.sub(r"[^A-Z0-9]", "", s)
        if len(compact) >= 2:
            return compact

    return s

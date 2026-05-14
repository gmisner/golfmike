"""
NAS / SWIM altitude: nxce:simpleAltitude under assignedAltitude is flight level
in hundreds of feet (e.g. 360 → FL360 → 36,000 ft), not feet.
"""


def simple_altitude_hundreds_to_feet(fl_hundreds: int) -> int:
    """Convert NAS simpleAltitude integer to feet (360 → 36000)."""
    return int(fl_hundreds) * 100


def normalize_altitude_to_feet_maybe_legacy(value) -> int | None:
    """
    For stored/API values that may still be FL hundreds (360) instead of feet (36000).
    Leaves values that already look like feet (e.g. >= 10000) unchanged.
    Skips 500 alone (often 500 ft pattern altitude; FL500 is uncommon).
    """
    if value is None:
        return None
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return None
    if n >= 10000:
        return n
    if 10 <= n <= 99:
        return n * 100
    if 100 <= n <= 600 and n != 500:
        return n * 100
    return n

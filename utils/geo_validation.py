"""
WGS-84 validation helpers for parsed latitude/longitude strings or floats.
"""

from __future__ import annotations

from typing import Optional, Tuple, Union


def validate_wgs84_lat_lon(
    lat: Optional[Union[str, int, float]],
    lon: Optional[Union[str, int, float]],
) -> Tuple[bool, str]:
    """
    Return (ok, error_message). error_message is empty when ok is True.
    """
    if lat is None or lon is None:
        return False, "latitude or longitude is None"
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return False, f"not numeric: lat={lat!r} lon={lon!r}"
    if not -90.0 <= lat_f <= 90.0:
        return False, f"latitude {lat_f} out of WGS-84 range [-90, 90]"
    if not -180.0 <= lon_f <= 180.0:
        return False, f"longitude {lon_f} out of WGS-84 range [-180, 180]"
    return True, ""

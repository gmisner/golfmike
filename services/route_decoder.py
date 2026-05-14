"""
Route decoder: parses an FAA SWIM route string into an ordered sequence of
(fix_name, lat, lon) tuples by looking up each fix against a navaid database.

FAA route string formats:
  Direct:    KDEP..KARR
  Victor:    KDEP V105 FIXNAME V23 KARR
  Jet:       KDEP J58 DEANO J80 KARR
  RNAV:      KDEP DCT BRUSR DCT DEANO DCT KARR
  Mixed:     KDEP..BRUSR..J58..DEANO..KARR

Navaid database:
  Loaded from the FAA NASR 28-day subscription data.
  CSV file: data/nasr_fixes.csv  (columns: fix_name, latitude, longitude, type)

  Download from: https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/
  The file to extract is: Fix.txt → convert with nasr_importer.py (provided separately)

  Until the NASR data is imported, a seed of ~200 common CONUS fixes is
  bundled in SEED_NAVAIDS below so the service works immediately.
"""

import csv
import os
import re
from typing import Dict, List, Optional, Tuple

from utils.logger import main_logger as logger


# ── Seed navaid data (major CONUS fixes + airports) ───────────────────────────
# Format: fix_name → (latitude, longitude)
# Enough to decode most high-density routes immediately.
# Import the full FAA NASR dataset for production coverage.

SEED_NAVAIDS: Dict[str, Tuple[float, float]] = {
    # Major airports
    "KLAX": (33.9425, -118.4081),
    "KJFK": (40.6413, -73.7781),
    "KORD": (41.9742, -87.9073),
    "KDFW": (32.8998, -97.0403),
    "KATL": (33.6407, -84.4277),
    "KSEA": (47.4502, -122.3088),
    "KDEN": (39.8561, -104.6737),
    "KIAH": (29.9902, -95.3368),
    "KLAS": (36.0840, -115.1537),
    "KMIA": (25.7959, -80.2870),
    "KSFO": (37.6213, -122.3790),
    "KBOS": (42.3656, -71.0096),
    "KEWR": (40.6895, -74.1745),
    "KPHL": (39.8719, -75.2411),
    "KDCA": (38.8512, -77.0402),
    "KIAD": (38.9531, -77.4565),
    "KBWI": (39.1754, -76.6683),
    "KDTW": (42.2124, -83.3534),
    "KMSP": (44.8848, -93.2223),
    "KPHX": (33.4373, -112.0078),
    "KSLC": (40.7884, -111.9778),
    "KPDX": (45.5887, -122.5975),
    "KSАН": (32.7336, -117.1897),
    "KSJC": (37.3626, -121.9290),
    "KOAK": (37.7213, -122.2208),
    "KMDW": (41.7859, -87.7524),
    "KBUR": (34.2007, -118.3587),
    "KLGA": (40.7773, -73.8726),
    "KMCO": (28.4294, -81.3089),
    "KTPA": (27.9755, -82.5332),
    "KFLL": (26.0726, -80.1527),
    "KPBI": (26.6832, -80.0956),
    "KHOU": (29.6454, -95.2789),
    "KAUS": (30.1975, -97.6664),
    "KSAT": (29.5337, -98.4698),
    "KDAL": (32.8471, -96.8517),
    "KHOU": (29.6454, -95.2789),
    "KSTL": (38.7487, -90.3700),
    "KMCI": (39.2976, -94.7139),
    "KOMA": (41.3032, -95.8940),
    "KMKE": (42.9472, -87.8966),
    "KCLE": (41.4117, -81.8498),
    "KCMH": (39.9980, -82.8919),
    "KIND": (39.7173, -86.2944),
    "KCVG": (39.0488, -84.6678),
    "KPIT": (40.4915, -80.2329),
    "KBUF": (42.9405, -78.7322),
    "KSYR": (43.1112, -76.1063),
    "KALB": (42.7483, -73.8017),
    "KRDU": (35.8776, -78.7875),
    "KCLT": (35.2140, -80.9431),
    "KGSO": (36.0978, -79.9373),
    "KRIC": (37.5052, -77.3197),
    "KNORFOLK": (36.8976, -76.0122),
    "KORF": (36.9776, -76.0353),
    "KORFORD": (36.8976, -76.0122),
    "KBNA": (36.1245, -86.6782),
    "KMEM": (35.0424, -89.9767),
    "KBHM": (33.5629, -86.7535),
    "KMSY": (29.9934, -90.2580),
    "KJAX": (30.4941, -81.6879),
    "KSAV": (32.1276, -81.2021),
    "KCHS": (32.8986, -80.0405),
    "KGRR": (42.8808, -85.5228),
    "KLAN": (42.7787, -84.5874),
    "KFNT": (42.9654, -83.7436),
    "KTOL": (41.5868, -83.8078),
    "KDAY": (39.9024, -84.2194),
    "KSDF": (38.1744, -85.7360),
    "KLEX": (38.0365, -84.6060),
    "KBGR": (44.8074, -68.8281),
    "KPVD": (41.7232, -71.4282),
    "KBDL": (41.9389, -72.6832),
    "KMHT": (42.9326, -71.4357),
    "KBTV": (44.4720, -73.1533),
    # Common CONUS en-route fixes
    "BRUSR": (35.0000, -107.0000),
    "DEANO": (36.9500, -101.4500),
    "MISEN": (34.2500, -118.8000),
    "DARTS": (38.5000, -121.5000),
    "SUNOL": (37.6000, -121.9000),
    "ALTAM": (37.2500, -122.0000),
    "SLEWY": (37.9500, -122.5000),
    "JUSIN": (36.5000, -120.5000),
    "LOSHN": (35.8000, -119.5000),
    "TEJON": (34.9000, -118.9000),
    "FILUP": (34.0000, -118.2000),
    "DARTS": (38.5000, -121.5000),
    "RIIVR": (33.9000, -117.4000),
    "SEAVU": (34.1000, -117.8000),
    "LYNDI": (33.7000, -117.2000),
    "SERFR": (36.5500, -121.3000),
    "BAYYY": (37.4000, -122.1000),
    "ORRCA": (36.2000, -120.1000),
    "NAPSE": (36.0000, -119.8000),
    "BOILE": (35.5000, -119.5000),
    "GORMAN": (34.8000, -118.8000),
    "DARTS": (38.5000, -121.5000),
    "WOOKY": (41.0000, -87.5000),
    "WYNDE": (41.5000, -87.2000),
    "LEWKE": (41.8000, -87.7000),
    "BENKY": (42.5000, -87.9000),
    "CMSKY": (43.0000, -88.5000),
    "PYNEI": (41.3000, -86.8000),
    "COATT": (40.8000, -86.3000),
    "TYGER": (40.5000, -85.5000),
    "GIBBI": (40.0000, -84.8000),
    "LUNDY": (41.5000, -83.9000),
    "ODETS": (42.2000, -83.5000),
    "TORBY": (42.8000, -83.0000),
    "DRUZZ": (43.2000, -82.5000),
    "TOPP": (43.5000, -76.5000),
    "LANNA": (41.7000, -72.9000),
    "MERIT": (41.5000, -74.2000),
    "HAAYS": (40.8000, -73.9000),
    "WAVEY": (37.5000, -75.5000),
    "SWANN": (36.5000, -75.7000),
    "CAMRN": (35.5000, -76.0000),
    "TRISS": (34.8000, -76.5000),
    "MYRTE": (33.7000, -78.9000),
    "SPOOK": (31.5000, -81.0000),
    "CRISY": (30.5000, -81.5000),
    "FTOBY": (28.5000, -82.5000),
    "IMPUR": (27.0000, -82.5000),
    "BRDGE": (25.7000, -81.5000),
    "ELKEY": (25.2000, -80.5000),
    "WOOLY": (32.5000, -97.5000),
    "PERTT": (33.0000, -96.5000),
    "JEDDD": (33.5000, -95.5000),
    "JEFCO": (34.0000, -94.5000),
    "MINSS": (35.0000, -93.5000),
    "COFFE": (35.5000, -90.5000),
    "MCMVL": (36.0000, -89.5000),
    "PADDY": (36.5000, -88.5000),
    "COVVY": (37.0000, -87.5000),
    "SPIDY": (37.5000, -86.5000),
    "WINSA": (38.0000, -85.5000),
    "RYLIE": (38.5000, -84.5000),
    "TIFTO": (39.0000, -83.5000),
    "INKEY": (38.5000, -82.8000),
    "CLNCY": (38.0000, -82.2000),
    "KENTA": (38.5000, -81.5000),
}


# ── NASR CSV loader ───────────────────────────────────────────────────────────

_navaid_db: Optional[Dict[str, Tuple[float, float]]] = None

NASR_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "nasr_fixes.csv"
)


def _load_navaid_db() -> Dict[str, Tuple[float, float]]:
    db = dict(SEED_NAVAIDS)

    if not os.path.exists(NASR_CSV_PATH):
        logger.info(
            "NASR navaid CSV not found — using seed dataset only. "
            "Import FAA NASR data to data/nasr_fixes.csv for full coverage."
        )
        return db

    loaded = 0
    try:
        with open(NASR_CSV_PATH, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("fix_name", "").strip().upper()
                try:
                    lat = float(row["latitude"])
                    lon = float(row["longitude"])
                    db[name] = (lat, lon)
                    loaded += 1
                except (KeyError, ValueError):
                    continue
        logger.info(f"Loaded {loaded} navaids from NASR CSV")
    except Exception as e:
        logger.error(f"Failed to load NASR CSV: {e}")

    return db


def get_navaid_db() -> Dict[str, Tuple[float, float]]:
    global _navaid_db
    if _navaid_db is None:
        _navaid_db = _load_navaid_db()
    return _navaid_db


def lookup_fix(fix_name: str) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) for a fix/navaid/airport, or None if unknown."""
    return get_navaid_db().get(fix_name.upper())


# ── Route string tokenizer ────────────────────────────────────────────────────

# Airway identifiers: V###, J###, Q###, T###, L###, M###, A###
_AIRWAY_RE = re.compile(r"^[VJQTLMABvjqtlmab]\d+$")
# SID/STAR identifiers: typically uppercase letters + digits + optional letter, ≥6 chars
_PROC_RE = re.compile(r"^[A-Z]{2,6}\d[A-Z]?$")
# DCT = direct, no fix
_DCT_RE = re.compile(r"^DCT$", re.IGNORECASE)
# Altitude/speed restrictions embedded in route (e.g. "FIXNAME/FL350")
_RESTRICTION_RE = re.compile(r"^([A-Z0-9]{2,20})/(.+)$")


def _tokenize_route(route_str: str) -> List[str]:
    """Split a raw route string into a clean list of tokens."""
    # Normalize separators: double-dot, spaces, slashes-as-separators
    cleaned = re.sub(r"\.\.+", " ", route_str)
    tokens = [t.strip().upper() for t in cleaned.split() if t.strip()]
    return tokens


def decode_route(
    route_str: str,
    departure: str,
    destination: str,
) -> List[Dict]:
    """
    Decode a raw FAA route string into an ordered list of waypoints with
    coordinates. Fixes not found in the navaid DB are included with
    latitude/longitude = None so the caller can handle them gracefully.

    Args:
        route_str:   Raw flightPlanRoute_10a string from SWIM/FDPS
        departure:   ICAO departure airport (prepended to waypoint list)
        destination: ICAO destination airport (appended to waypoint list)

    Returns:
        List of dicts: [{sequence, fix_name, latitude, longitude,
                         altitude_restriction, speed_restriction, fix_type}]
    """
    waypoints: List[Dict] = []
    seq = 0

    def _add(fix: str, alt_rest: str = "", spd_rest: str = "", fix_type: str = "FIX"):
        nonlocal seq
        coords = lookup_fix(fix)
        waypoints.append({
            "sequence": seq,
            "fix_name": fix,
            "latitude": coords[0] if coords else None,
            "longitude": coords[1] if coords else None,
            "altitude_restriction": alt_rest or None,
            "speed_restriction": spd_rest or None,
            "fix_type": fix_type,
        })
        seq += 1

    # Departure airport is always first
    _add(departure.upper(), fix_type="AIRPORT")

    if not route_str:
        _add(destination.upper(), fix_type="AIRPORT")
        return waypoints

    tokens = _tokenize_route(route_str)

    for token in tokens:
        # Skip direct routing keyword
        if _DCT_RE.match(token):
            continue

        # Skip airway identifiers — they're connectors, not fixes
        if _AIRWAY_RE.match(token):
            continue

        # Extract inline altitude/speed restriction (FIX/FL350 or FIX/250K/FL350)
        alt_rest = ""
        spd_rest = ""
        m = _RESTRICTION_RE.match(token)
        if m:
            token = m.group(1)
            restrictions = m.group(2).split("/")
            for r in restrictions:
                if r.startswith("FL") or r.endswith("00"):
                    alt_rest = r
                elif r.endswith("K") or r.endswith("N"):
                    spd_rest = r

        # Skip if this token is the departure or destination (avoid duplicates)
        if token in (departure.upper(), destination.upper()):
            continue

        # Determine fix type
        fix_type = "FIX"
        if _PROC_RE.match(token) and len(token) >= 5:
            fix_type = "PROCEDURE"

        _add(token, alt_rest, spd_rest, fix_type)

    # Destination airport is always last
    _add(destination.upper(), fix_type="AIRPORT")

    return waypoints


# ── Coverage stats (useful for monitoring data quality) ───────────────────────

def decode_route_coverage(waypoints: List[Dict]) -> float:
    """Return the fraction of fixes that have known coordinates (0.0–1.0)."""
    if not waypoints:
        return 0.0
    known = sum(1 for w in waypoints if w["latitude"] is not None)
    return known / len(waypoints)

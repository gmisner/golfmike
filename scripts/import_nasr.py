#!/usr/bin/env python3
"""
FAA NASR navaid importer.

Reads FIX_BASE.csv, NAV_BASE.csv, and APT_BASE.csv from the FAA 28-day
NASR subscription and produces data/nasr_fixes.csv for the route decoder.

Priority when the same fix_name appears in multiple sources:
  1. FIX_BASE  (named intersections — most accurate for en-route route strings)
  2. NAV_BASE  (VORs, NDBs, TACANs)
  3. APT_BASE  (airports by ICAO_ID)

Usage:
  python scripts/import_nasr.py --nasr-dir /path/to/14_May_2026_CSV
  python scripts/import_nasr.py  # uses NASR_DIR env var or prompts
"""

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Dict, Tuple

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "nasr_fixes.csv"


def _signed_lon(lon_decimal: str, lon_hemis: str) -> float:
    """NASR LONG_DECIMAL is already negative for W — return as-is."""
    val = float(lon_decimal)
    # Defensive: if somehow a positive value slips through for a W fix, negate it.
    if lon_hemis.strip().upper() == "W" and val > 0:
        val = -val
    return val


def _signed_lat(lat_decimal: str, lat_hemis: str) -> float:
    val = float(lat_decimal)
    if lat_hemis.strip().upper() == "S" and val > 0:
        val = -val
    return val


def load_fixes(nasr_dir: Path) -> Dict[str, Tuple[float, float, str]]:
    """Load FIX_BASE.csv — named intersections and en-route waypoints."""
    fixes: Dict[str, Tuple[float, float, str]] = {}
    path = nasr_dir / "FIX_BASE.csv"
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fix_id = row["FIX_ID"].strip().upper()
            if not fix_id:
                continue
            try:
                lat = _signed_lat(row["LAT_DECIMAL"], row["LAT_HEMIS"])
                lon = _signed_lon(row["LONG_DECIMAL"], row["LONG_HEMIS"])
            except (ValueError, KeyError):
                continue
            fixes[fix_id] = (lat, lon, "FIX")
    print(f"  Loaded {len(fixes):,} fixes from FIX_BASE.csv")
    return fixes


def load_navaids(nasr_dir: Path) -> Dict[str, Tuple[float, float, str]]:
    """Load NAV_BASE.csv — VORs, NDBs, TACANs, DMEs."""
    navaids: Dict[str, Tuple[float, float, str]] = {}
    path = nasr_dir / "NAV_BASE.csv"
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nav_id = row["NAV_ID"].strip().upper()
            if not nav_id:
                continue
            status = row.get("NAV_STATUS", "").upper()
            # Skip decommissioned navaids
            if "DECOMM" in status or "RESTRICTED" in status:
                continue
            try:
                lat = _signed_lat(row["LAT_DECIMAL"], row["LAT_HEMIS"])
                lon = _signed_lon(row["LONG_DECIMAL"], row["LONG_HEMIS"])
            except (ValueError, KeyError):
                continue
            nav_type = row.get("NAV_TYPE", "NAV").strip()
            navaids[nav_id] = (lat, lon, nav_type)
    print(f"  Loaded {len(navaids):,} navaids from NAV_BASE.csv")
    return navaids


def load_airports(nasr_dir: Path) -> Dict[str, Tuple[float, float, str]]:
    """
    Load APT_BASE.csv — airports indexed by ICAO_ID (4-letter, e.g. KLAX).
    Also adds a K-prefixed entry for 3-char FAA LIDs (e.g. LAX → KLAX)
    in case route strings omit the leading K.
    """
    airports: Dict[str, Tuple[float, float, str]] = {}
    path = nasr_dir / "APT_BASE.csv"
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip closed airports
            if row.get("ARPT_STATUS", "").strip().upper() not in ("O", ""):
                continue
            try:
                lat = _signed_lat(row["LAT_DECIMAL"], row["LAT_HEMIS"])
                lon = _signed_lon(row["LONG_DECIMAL"], row["LONG_HEMIS"])
            except (ValueError, KeyError):
                continue

            icao_id = row.get("ICAO_ID", "").strip().upper()
            arpt_id = row.get("ARPT_ID", "").strip().upper()

            # Index by ICAO 4-letter code (primary key for flight plans)
            if icao_id and len(icao_id) == 4:
                airports[icao_id] = (lat, lon, "AIRPORT")

            # Also index by FAA LID (for domestic routes that omit the K)
            if arpt_id and len(arpt_id) <= 4:
                airports[arpt_id] = (lat, lon, "AIRPORT")

                # Synthesise ICAO code for US 3-char LIDs (e.g. LAX → KLAX)
                if len(arpt_id) == 3 and icao_id and icao_id not in airports:
                    airports[icao_id] = (lat, lon, "AIRPORT")

    print(f"  Loaded {len(airports):,} airport entries from APT_BASE.csv")
    return airports


def main(nasr_dir: str) -> None:
    base = Path(nasr_dir)
    if not base.is_dir():
        sys.exit(f"ERROR: NASR directory not found: {nasr_dir}")

    print(f"Importing FAA NASR data from: {base}")

    # Load in priority order — later dicts do NOT overwrite earlier ones
    combined: Dict[str, Tuple[float, float, str]] = {}

    airports = load_airports(base)
    combined.update(airports)

    navaids = load_navaids(base)
    for k, v in navaids.items():
        combined.setdefault(k, v)  # FIX wins over NAV, NAV wins over APT

    fixes = load_fixes(base)
    for k, v in fixes.items():
        combined[k] = v  # FIX always wins

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["fix_name", "latitude", "longitude", "type"])
        for fix_name, (lat, lon, fix_type) in sorted(combined.items()):
            writer.writerow([fix_name, round(lat, 8), round(lon, 8), fix_type])

    print(f"\nWrote {len(combined):,} entries → {OUTPUT_PATH}")
    print("Route decoder will load this file automatically on next startup.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import FAA NASR data into nasr_fixes.csv")
    parser.add_argument(
        "--nasr-dir",
        default=os.environ.get("NASR_DIR", ""),
        help="Path to the NASR CSV directory (e.g. /path/to/14_May_2026_CSV)",
    )
    args = parser.parse_args()

    if not args.nasr_dir:
        args.nasr_dir = input("Enter path to NASR CSV directory: ").strip()

    main(args.nasr_dir)

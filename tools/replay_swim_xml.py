#!/usr/bin/env python3
"""
Replay saved SWIM XML through parse_and_store_to_database() so updated parsers (e.g. lat/lon)
apply to the database.

You cannot "fix" wrong coordinates with SQL alone: the database only has whatever was stored.
You need either archived XML (this script), a broker replay (Solace), or new live messages.

Replaying may append new track_information / track_updates rows. To avoid duplicates for a
given period, delete or trim old rows for those aircraft/times before replay, or rely on
downstream queries that pick the latest point.

Usage:
  python tools/replay_swim_xml.py "Sample XML/trackinformation.xml"
  python tools/replay_swim_xml.py --dir "Sample XML"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from swim_data_processor import parse_and_store_to_database
from utils.logger import main_logger as logger


def _collect_xml_files(path: Path, recursive: bool) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() == ".xml" else []
    if not path.is_dir():
        return []
    pattern = "**/*.xml" if recursive else "*.xml"
    return sorted(path.glob(pattern))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay SWIM XML files into the database."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="XML files or directories (default: none; use --dir)",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Directory of XML files",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="With --dir, include subdirectories",
    )
    args = parser.parse_args()

    files: list[Path] = []
    for p in args.paths:
        files.extend(_collect_xml_files(p, args.recursive))
    if args.dir:
        files.extend(_collect_xml_files(args.dir, args.recursive))

    if not files:
        logger.error("No .xml files found. Pass file paths or --dir.")
        return 1

    ok = 0
    fail = 0
    for path in files:
        try:
            xml = path.read_text(encoding="utf-8")
        except OSError as e:
            logger.error("Cannot read {}: {}", path, e)
            fail += 1
            continue
        if parse_and_store_to_database(xml):
            ok += 1
            logger.info("Replayed OK: {}", path)
        else:
            fail += 1
            logger.warning("Replay skipped or failed (no parse/store): {}", path)

    logger.info("Done. success={} failed={} total={}", ok, fail, len(files))
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())

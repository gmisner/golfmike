#!/usr/bin/env python3
"""
Scan saved SWIM/TFM XML files: list msgType coverage vs parser_storer_registry.

Examples:
  python tools/audit_swim_messages.py "Sample XML/trackinformation.xml"
  python tools/audit_swim_messages.py "Sample XML" --strict
  python tools/audit_swim_messages.py "Sample XML" --strict --fail-on-unroutable
  python tools/audit_swim_messages.py . --xsd-gaps
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.logger import main_logger as logger
from utils.swim_message_audit import (  # noqa: E402
    SwimPayloadAudit,
    audit_swim_payload,
    format_audit_report,
    registry_gap_summary,
)
from parser_storer_registry import PARSERS, STORERS  # noqa: E402


def _iter_xml_files(path: Path):
    if path.is_file():
        if path.suffix.lower() in (".xml",) or "xml" in path.name.lower():
            yield path
        return
    for p in sorted(path.rglob("*")):
        if p.is_file() and p.suffix.lower() == ".xml":
            yield p


def _audit_path(path: Path) -> tuple[SwimPayloadAudit, bool]:
    text = path.read_text(encoding="utf-8", errors="replace")
    a = audit_swim_payload(text)
    if a.parse_error:
        return a, True
    has_gap = bool(a.type_coverage) and any(
        not (row.has_parser and row.has_storer) for row in a.type_coverage
    )
    if a.processor_would_use_msg_type and not a.processor_routing_has_full_pipeline:
        has_gap = True
    return a, has_gap


def _is_unroutable(audit: SwimPayloadAudit) -> bool:
    """
    True when XML parses but has no processor key to route through registry.
    """
    return audit.parse_error is None and not audit.processor_would_use_msg_type


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit SWIM XML message types against parser_storer_registry."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Single .xml file or directory to scan recursively",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON lines (one object per file)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any file has a missing parser/storer or bad XML",
    )
    parser.add_argument(
        "--fail-on-unroutable",
        action="store_true",
        help="Treat files with no routable processor key as failures",
    )
    parser.add_argument(
        "--xsd-gaps",
        action="store_true",
        help="Print FlightData.xsd messageType values missing from PARSERS, then exit",
    )
    parser.add_argument(
        "--list-registry",
        action="store_true",
        help="Print registered msgType keys (PARSERS) and exit",
    )
    args = parser.parse_args()

    if args.list_registry:
        for k in sorted(PARSERS.keys()):
            p = "yes" if PARSERS.get(k) else "no"
            s = "yes" if STORERS.get(k) else "no"
            print(f"{k}\tparser={p}\tstorer={s}")
        return 0

    if args.xsd_gaps:
        extra, missing = registry_gap_summary()
        print("FlightData messageType not in PARSERS (add parser when you need these):")
        for x in extra:
            print(f"  {x}")
        print("PARSERS keys not in FlightData messageType (often expected):")
        for m in missing:
            print(f"  {m}")
        return 0

    root = args.path
    if not root.exists():
        logger.error("Path does not exist: {}", root)
        return 2

    any_gap = False
    any_unroutable = False
    files = list(_iter_xml_files(root))
    if not files:
        logger.warning("No XML files under {}", root)
        return 0

    for fp in files:
        a, gap = _audit_path(fp)
        unroutable = _is_unroutable(a)
        if gap:
            any_gap = True
        if unroutable:
            any_unroutable = True
        if args.json:
            row = {
                "file": str(fp),
                "parse_error": a.parse_error,
                "is_nas_message_collection": a.is_nas_message_collection,
                "root_tag": a.root_tag,
                "fltd_message_types": a.fltd_message_types,
                "unique_fltd_message_types": a.unique_fltd_message_types,
                "first_msgtype_attr_in_tree": a.first_msgtype_attr_in_tree,
                "processor_would_use_msg_type": a.processor_would_use_msg_type,
                "processor_routing_has_full_pipeline": a.processor_routing_has_full_pipeline,
                "is_unroutable": unroutable,
                "type_coverage": [
                    {
                        "msg_type": r.msg_type,
                        "has_parser": r.has_parser,
                        "has_storer": r.has_storer,
                    }
                    for r in a.type_coverage
                ],
                "has_coverage_gap": gap,
            }
            print(json.dumps(row, ensure_ascii=False))
        else:
            print("---", fp, "---")
            print(format_audit_report(a))
            if unroutable:
                print("  NOTE: No routable processor key found for this XML.")
            print()

    if args.strict and any_gap:
        return 1
    if args.fail_on_unroutable and any_unroutable:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

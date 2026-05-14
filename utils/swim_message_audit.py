"""
Inspect SWIM / TFM XML payloads: message types present vs parser_storer registry.

Use this to find unhandled msgType values before relying on the DB layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from lxml import etree

from parsers.xml_namespaces import SWIM_NAMESPACES, parse_swim_xml_root
from parser_storer_registry import PARSERS, get_parser, get_storer

# Same as swim_data_processor.NAS_MESSAGE_COLLECTION_NS
NAS_MESSAGE_COLLECTION_NS = "http://www.faa.aero/nas/3.0"


@dataclass
class TypeCoverageRow:
    """Registry coverage for one msgType string."""

    msg_type: str
    has_parser: bool
    has_storer: bool


@dataclass
class SwimPayloadAudit:
    """
    What is in the XML and how it maps to the current routing + registry.
    """

    is_nas_message_collection: bool
    root_tag: str
    root_ns: str
    #: Every fltdMessage @msgType in document order (empty if none)
    fltd_message_types: List[str] = field(default_factory=list)
    #: Deduplicated fltdMessage types, order preserved
    unique_fltd_message_types: List[str] = field(default_factory=list)
    #: First //*[@msgType] in document order (mirrors parse_xml_to_pydantic's xpath)
    first_msgtype_attr_in_tree: Optional[str] = None
    #: Message type string the swim processor would use to look up parser/storer
    processor_would_use_msg_type: Optional[str] = None
    #: Whether that key has both parser and storer
    processor_routing_has_full_pipeline: bool = False
    #: One row per unique fltdMessage msgType
    type_coverage: List[TypeCoverageRow] = field(default_factory=list)
    parse_error: Optional[str] = None


def _all_fltd_message_types(root: etree._Element) -> List[str]:
    out: List[str] = []
    for m in root.xpath(".//*[local-name()='fltdMessage']"):
        if not isinstance(m, etree._Element):
            continue
        mt = m.get("msgType")
        if mt:
            out.append(mt)
    return out


def _first_msgtype_attr_in_tree(root: etree._Element) -> Optional[str]:
    # Mirror swim_data_processor: root.xpath("//@msgType", namespaces=SWIM_NAMESPACES)
    found = root.xpath("//@msgType", namespaces=SWIM_NAMESPACES)
    if not found:
        return None
    return found[0]


def audit_swim_payload(xml_string: str) -> SwimPayloadAudit:
    """
    Parse XML and report message types and registry coverage.

    Does not call parsers or the database.
    """
    try:
        root = parse_swim_xml_root(xml_string)
    except etree.XMLSyntaxError as e:
        return SwimPayloadAudit(
            is_nas_message_collection=False,
            root_tag="",
            root_ns="",
            parse_error=str(e),
        )

    q = etree.QName(root)
    root_tag = q.localname or ""
    root_ns = q.namespace or ""

    is_nas = q.localname == "MessageCollection" and root_q_namespace_matches_nas(
        q.namespace
    )
    fltd_types = _all_fltd_message_types(root)
    unique: List[str] = []
    seen = set()
    for t in fltd_types:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    first_attr = _first_msgtype_attr_in_tree(root)

    processor_key: Optional[str] = None
    if is_nas:
        processor_key = "NAS_MessageCollection"
    else:
        processor_key = first_attr

    full_pipeline = False
    if processor_key:
        p = get_parser(processor_key)
        s = get_storer(processor_key)
        full_pipeline = p is not None and s is not None

    coverage: List[TypeCoverageRow] = []
    for mt in unique:
        coverage.append(
            TypeCoverageRow(
                msg_type=mt,
                has_parser=get_parser(mt) is not None,
                has_storer=get_storer(mt) is not None,
            )
        )
    if is_nas and not coverage:
        k = "NAS_MessageCollection"
        coverage.append(
            TypeCoverageRow(
                msg_type=processor_key or k,
                has_parser=get_parser(k) is not None,
                has_storer=get_storer(k) is not None,
            )
        )

    return SwimPayloadAudit(
        is_nas_message_collection=is_nas,
        root_tag=root_tag,
        root_ns=root_ns,
        fltd_message_types=fltd_types,
        unique_fltd_message_types=unique,
        first_msgtype_attr_in_tree=first_attr,
        processor_would_use_msg_type=processor_key,
        processor_routing_has_full_pipeline=full_pipeline,
        type_coverage=coverage,
    )


def root_q_namespace_matches_nas(ns: Optional[str]) -> bool:
    return ns in (NAS_MESSAGE_COLLECTION_NS, None, "")


def _xsd_flightdata_message_type_values() -> List[str]:
    """Enumeration values for FlightData.xsd / messageType (TFM fltdMessage)."""
    from pathlib import Path
    import xml.etree.ElementTree as ET

    p = Path(__file__).resolve().parents[1] / "XML Schema" / "FlightData.xsd"
    if not p.is_file():
        return []
    xsd = "http://www.w3.org/2001/XMLSchema"
    tree = ET.parse(p)
    root = tree.getroot()
    out: List[str] = []
    for st in root.findall(f"{{{xsd}}}simpleType"):
        if st.get("name") != "messageType":
            continue
        for rest in st.findall(f"{{{xsd}}}restriction"):
            for en in rest.findall(f"{{{xsd}}}enumeration"):
                v = en.get("value")
                if v:
                    out.append(v)
        break
    return out


def registry_gap_summary() -> Tuple[List[str], List[str]]:
    """
    Compare FlightData.xsd messageType enum to registered PARSERS keys (best-effort).

    Returns (types_in_xsd_not_in_parsers, parser_keys_not_in_xsd) — informational only;
    the registry also contains non-FDM keys (e.g. NAS_MessageCollection, TMI).
    """
    enum_values = _xsd_flightdata_message_type_values()
    if not enum_values:
        return [], list(PARSERS.keys())

    xsd_set = set(enum_values)
    parser_set = set(PARSERS.keys())
    extra = sorted(xsd_set - parser_set)
    missing = sorted(parser_set - xsd_set)
    return extra, missing


def format_audit_report(a: SwimPayloadAudit) -> str:
    lines: List[str] = []
    if a.parse_error:
        return f"XML parse error: {a.parse_error}"
    lines.append(f"root: {{{a.root_ns}}}{a.root_tag}")
    lines.append(f"NAS MessageCollection: {a.is_nas_message_collection!s}")
    if a.fltd_message_types:
        lines.append(
            f"fltdMessage msgType sequence ({len(a.fltd_message_types)}): {a.fltd_message_types!r}"
        )
    if a.unique_fltd_message_types and not a.is_nas_message_collection:
        lines.append(f"unique fltdMessage msgTypes: {a.unique_fltd_message_types!r}")
    lines.append(
        f"first //@msgType in document (current processor key when not NAS): {a.first_msgtype_attr_in_tree!r}"
    )
    lines.append(
        f"processor would use: {a.processor_would_use_msg_type!r}  "
        f"full parser+storer: {a.processor_routing_has_full_pipeline!s}"
    )
    for row in a.type_coverage:
        lines.append(
            f"  {row.msg_type}: parser={row.has_parser!s} storer={row.has_storer!s}"
        )
    if (
        not a.is_nas_message_collection
        and a.unique_fltd_message_types
        and len(set(a.unique_fltd_message_types)) > 1
    ):
        lines.append(
            "  NOTE: Multiple fltdMessage msgType values. swim_data_processor iterates every "
            "fltdMessage and runs the matching parser+storer when registered (TMI / fiOutput "
            "feeds with no fltdMessage still use the first //@msgType only)."
        )
    return "\n".join(lines)

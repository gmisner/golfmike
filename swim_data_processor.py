# swim_data_processor.py
from lxml import etree
from parser_storer_registry import get_parser, get_storer
from parsers.xml_namespaces import SWIM_NAMESPACES, SWIM_XML_PARSER
from parsers.nas_message_collection_parser import parse_nas_message_collection
from utils.tfm_fragment import build_minimal_tfm_data_service
from typing import Any, List, Optional, Tuple
from utils.logger import main_logger as logger

NAS_MESSAGE_COLLECTION_NS = "http://www.faa.aero/nas/3.0"
from sqlalchemy.exc import SQLAlchemyError
from error_handling import (
    retry_with_backoff,
    handle_database_errors,
    track_errors,
)


def _fltd_message_elements(root: etree._Element) -> list:
    return list(root.xpath(".//*[local-name()='fltdMessage']"))


def _data_is_non_empty(data: Any) -> bool:
    if data is None:
        return False
    if isinstance(data, (list, tuple, dict, str, bytes)) and len(data) == 0:
        return False
    return True


def parse_xml_to_pydantic(
    xml_string: str,
) -> Optional[List[Tuple[str, Any]]]:
    """
    Parse SWIM/TFM XML into one or more (msgType, parsed_payload) items.

    - MessageCollection (NAS) → a single (NAS_MessageCollection, rows) entry.
    - TFM with ``fltdMessage`` children: one entry per child with a registered parser
      (each message parsed against a single-message fragment, so the whole batch is ingested).
    - Otherwise: legacy single dispatch using the first ``//@msgType`` (TMI, fiOutput, etc.).
    """
    try:
        xml_bytes = xml_string.encode("utf-8")
        root = etree.fromstring(xml_bytes, parser=SWIM_XML_PARSER)

        root_q = etree.QName(root)
        if root_q.localname == "MessageCollection" and root_q.namespace in (
            NAS_MESSAGE_COLLECTION_NS,
            None,
        ):
            parsed = parse_nas_message_collection(root)
            if not parsed:
                logger.debug("NAS MessageCollection produced no track rows")
                return None
            return [("NAS_MessageCollection", parsed)]

        fltds = _fltd_message_elements(root)
        if fltds:
            out: List[Tuple[str, Any]] = []
            for fltd in fltds:
                mt = fltd.get("msgType")
                if not mt:
                    continue
                p = get_parser(mt)
                if not p:
                    logger.debug("No parser registered for msgType: {}", mt)
                    continue
                subroot = build_minimal_tfm_data_service(root, fltd)
                try:
                    parsed = p(subroot)
                except Exception as e:
                    logger.error(
                        "Parser failed for msgType={}: {} (excerpt: {})",
                        mt,
                        e,
                        str(etree.tostring(subroot)[:200]),
                    )
                    continue
                if not _data_is_non_empty(parsed):
                    continue
                out.append((mt, parsed))
            return out or None

        # Legacy: no fltdMessage (e.g. TMI in fiOutput) — one dispatch on first @msgType
        msg_type_elements = root.xpath("//@msgType", namespaces=SWIM_NAMESPACES)
        if not msg_type_elements:
            logger.debug("No msgType attribute found in XML")
            return None

        msg_type = msg_type_elements[0]
        parser_func = get_parser(msg_type)
        if not parser_func:
            logger.debug("No parser registered for message type: {}", msg_type)
            return None

        parsed_data = parser_func(root)
        if not _data_is_non_empty(parsed_data):
            return None
        return [(msg_type, parsed_data)]

    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error: {e}")
        logger.error(f"Problematic XML (excerpt): {xml_string[:500]}")
        return None
    except Exception as e:
        logger.error(f"Error parsing XML to Pydantic: {e}", exc_info=True)
        logger.error(f"Problematic XML (excerpt): {xml_string[:500]}")
        return None


@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
@handle_database_errors
@track_errors("database_operation")
def parse_and_store_to_database(xml_string: str) -> bool:
    """Parse XML and store each (msgType, data) with the matching storer (own DB session)."""
    try:
        parsed_list = parse_xml_to_pydantic(xml_string)
        if not parsed_list:
            logger.debug(
                "Failed to parse XML data (may be expected for some message types)"
            )
            return False

        any_ok = False
        for msg_type, data in parsed_list:
            storer_func = get_storer(msg_type)
            if not storer_func:
                logger.debug("No storer registered for message type: {}", msg_type)
                continue
            if not _data_is_non_empty(data):
                continue
            try:
                storer_func(data, session=None)
                logger.info("Successfully stored {} (batch part)", msg_type)
                any_ok = True
            except SQLAlchemyError as e:
                logger.error(
                    f"Database error storing {msg_type} message: {e}", exc_info=True
                )
            except Exception as e:
                logger.error(f"Error storing {msg_type} message: {e}", exc_info=True)

        return any_ok

    except Exception as e:
        logger.error(f"Error in parse_and_store_to_database: {e}", exc_info=True)
        return False

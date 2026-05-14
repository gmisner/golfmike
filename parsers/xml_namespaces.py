"""
Shared TFM / SWIM XML namespace map and parser for lxml.

Single source of truth for xmlns prefixes used across XSD message types.
"""

from __future__ import annotations

from typing import Union

from lxml import etree

# Full prefix map for XPath (find/findall); extra prefixes are harmless.
SWIM_NAMESPACES = {
    "ds": "urn:us:gov:dot:faa:atm:tfm:tfmdataservice",
    "fdm": "urn:us:gov:dot:faa:atm:tfm:flightdata",
    "nxce": "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements",
    "nxcm": "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages",
    "ns2": "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages",
    "ns4": "urn:us:gov:dot:faa:atm:tfm:ficommondatatypes",
    "ns3": "urn:us:gov:dot:faa:atm:tfm:flightdata",
    "ns6": "http://www.fixm.aero/tfm/3.1",
    "ns5": "urn:us:gov:dot:faa:atm:tfm:tfmdataservice",
    "ns8": "http://www.faa.aero/nas/3.1",
    "ns7": "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements",
    "ns13": "urn:us:gov:dot:faa:atm:tfm:rapttimeline",
    "ns9": "urn:us:gov:dot:faa:atm:tfm:ficommonmessages2",
    "ns12": "urn:us:gov:dot:faa:atm:tfm:flowinformation",
    "ns11": "urn:us:gov:dot:faa:atm:tfm:ficommondmessages",
    "ns10": "urn:us:gov:dot:faa:atm:tfm:tfmrequestreplytypes",
    "ns16": "http://www.fixm.aero/flight/3.0",
    "ns15": "http://www.fixm.aero/foundation/3.0",
    "ns14": "http://www.fixm.aero/base/3.0",
}

# Reused for all SWIM parses (thread-safe for read-only parsing).
SWIM_XML_PARSER = etree.XMLParser(recover=True, huge_tree=True)


def parse_swim_xml_root(xml: Union[str, bytes]):
    """Parse XML once; use this for tests or tools outside the main consumer path."""
    data = xml if isinstance(xml, bytes) else xml.encode("utf-8")
    return etree.fromstring(data, parser=SWIM_XML_PARSER)

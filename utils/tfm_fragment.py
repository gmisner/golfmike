"""
Build a minimal tfmDataService + fltdOutput + one fltdMessage tree for per-message parsing.
"""

from __future__ import annotations

from copy import deepcopy

from lxml import etree

FDM_NS = "urn:us:gov:dot:faa:atm:tfm:flightdata"


def build_minimal_tfm_data_service(
    original_root: etree._Element, fltd_message: etree._Element
) -> etree._Element:
    """
    Wrap a single fltdMessage in the same root element class as ``original_root``,
    with a single ``fltdOutput`` parent (TFM / tfmDataService pattern).
    """
    root = etree.Element(original_root.tag, nsmap=original_root.nsmap)
    fltd_out = etree.SubElement(root, f"{{{FDM_NS}}}fltdOutput")
    fltd_out.append(deepcopy(fltd_message))
    return root

"""
Registry wiring: parser_storer_registry is the single source of truth.

This module re-exports the same API so older references to setup_registry continue to work.
"""

from parser_storer_registry import (  # noqa: F401
    PARSERS,
    STORERS,
    get_parser,
    get_storer,
    register_parser,
    register_storer,
)


def setup_registry() -> None:
    """
    No-op: parsers and storers are registered in parser_storer_registry at import time.
    """
    return None

from .uno_bridge import LibreOfficeBridge
from .cell_inspector import CellInspector
from .cell_manipulator import CellManipulator
from .sheet_analyzer import SheetAnalyzer
from .error_detector import ErrorDetector
from .address_utils import (
    parse_address,
    parse_range_string,
    column_to_index,
    index_to_column,
    format_address,
)

__all__ = [
    "LibreOfficeBridge",
    "CellInspector",
    "CellManipulator",
    "SheetAnalyzer",
    "ErrorDetector",
    "parse_address",
    "parse_range_string",
    "column_to_index",
    "index_to_column",
    "format_address",
]


def get_event_listener_class():
    """Lazy import to avoid importing PyQt5 in non-UI contexts."""
    from .event_listener import LibreOfficeEventListener
    return LibreOfficeEventListener

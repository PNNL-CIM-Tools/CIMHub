"""CIMHub core: the thin shared layer every converter spoke builds on.

Core only holds what no upstream library provides (invariant I9). Units, bases,
terminals and CIM construction belong to cimtables / cimbuilder / cimprofiles.

Public API:
    FormatReader, FormatWriter     native file <-> native GraphModel (only these touch the disk)
    FormatImporter, CimtblImporter native GraphModel -> .cimtbl documents -> CIM (cimhub_core.cimtbl)
    FormatExporter                 CIM -> native GraphModel
    GraphModel                     indexed store for native LinkML dataclasses
    ConverterRegistry              decorator-based class -> function dispatch
    AnnotationSerializer & co.     LinkML-annotation-driven native text formatting
    clean_cim_name                 export-side naming only (never for mRIDs)
    get_mermaid, download_mermaid  diagrams of native dataclasses
    scaffold_package               generate a new spoke package
"""

__version__ = "3.0.0a0"

from cimhub_core.base import CimtblImporter, FormatExporter, FormatImporter, FormatReader, FormatWriter
from cimhub_core.graph_model import GraphModel
from cimhub_core.mermaid import download_mermaid, get_mermaid
from cimhub_core.names import clean_cim_name
from cimhub_core.registry import ConverterRegistry
from cimhub_core.scaffold import scaffold_package
from cimhub_core.serialization import (
    AnnotationSerializer,
    format_by_spec,
    get_field_order,
    get_native_name,
    get_schema_annotations,
)

__all__ = [
    "FormatReader",
    "FormatWriter",
    "FormatImporter",
    "CimtblImporter",
    "FormatExporter",
    "GraphModel",
    "ConverterRegistry",
    "AnnotationSerializer",
    "format_by_spec",
    "get_field_order",
    "get_native_name",
    "get_schema_annotations",
    "clean_cim_name",
    "get_mermaid",
    "download_mermaid",
    "scaffold_package",
]

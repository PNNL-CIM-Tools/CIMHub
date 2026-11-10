"""Export-side atom helpers (EXPORT_MAPPING.md S6a tests): an atom deck through import and export, and the
exported deck's golden."""
from __future__ import annotations

import os
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.cimtbl_testing import UPDATE_GOLDENS
from cimhub_core.names import export_name
from cimhub_opendss import DssImporter, DssReader
from cimhub_opendss.exporter.cim_to_dss import cim_to_dss


def export_atom(atom: Path, directory: Path, *, name_source: str) -> Path:
    """``atom`` -> ``DssImporter.to_cim`` -> ``cim_to_dss``; the written deck."""
    return export_network(atom, directory, name_source=name_source)[0]


def export_network(atom: Path, directory: Path, *, name_source: str):
    """``(written deck, network)``: ``atom`` -> ``DssImporter.to_cim`` -> ``cim_to_dss``."""
    network = DssImporter(atom.stem).to_cim(DssReader(atom).read_all())
    written = directory / name_source / f"{atom.stem}.dss"
    cim_to_dss(network, written, name_source=name_source)
    return written, network


def bus_names(network, name_source: str) -> dict[str, str]:
    """``{CIM name: exported name}`` of every ConnectivityNode, lowercased (the importer names nodes by DSS bus)."""
    return {str(node.name).lower(): export_name(node, name_source).lower()
            for node in network.graph.get(cim.ConnectivityNode, {}).values()}


def assert_matches_dss_golden(written: Path, golden: Path) -> None:
    """The exported deck equals its reviewed golden (``CIMHUB_UPDATE_GOLDENS=1`` rewrites it; review it in git)."""
    text = written.read_text(encoding="utf-8")
    if os.environ.get(UPDATE_GOLDENS):
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(text, encoding="utf-8")
    assert golden.exists(), f"{golden}: no golden; run with {UPDATE_GOLDENS}=1 and review it"
    assert text == golden.read_text(encoding="utf-8"), f"{golden.name}: the export differs from its golden"

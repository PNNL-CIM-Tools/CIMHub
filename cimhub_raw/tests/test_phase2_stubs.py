"""Phase-2 stub mappers: empty without records, fail fast with them (RAW_REWRITE_PLAN.md §4.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cimhub_core import GraphModel
from cimhub_raw.importer.cimtbl import (
    facts_device,
    gne_device,
    induction_machine,
    multi_terminal_dc,
    two_terminal_dc,
    vsc_dc,
)
from cimhub_raw.raw34_reader import Raw34Reader

IEEE14 = Path(__file__).parent / "cases" / "IEEE14" / "IEEE_14_bus.raw"

STUBS = [
    (two_terminal_dc, two_terminal_dc.map_two_terminal_dc),
    (vsc_dc, vsc_dc.map_vsc_dc),
    (multi_terminal_dc, multi_terminal_dc.map_multi_terminal_dc),
    (facts_device, facts_device.map_facts_device),
    (gne_device, gne_device.map_gne_device),
    (induction_machine, induction_machine.map_induction_machine),
]


@pytest.mark.parametrize(("module", "mapper"), STUBS, ids=[m.__name__.rsplit(".", 1)[1] for m, _ in STUBS])
def test_a_case_without_the_table_gives_an_empty_document(module, mapper):
    document = mapper(Raw34Reader(IEEE14).read_all())
    assert document.statements == []
    assert document.name == module.__name__.rsplit(".", 1)[1]


@pytest.mark.parametrize(("module", "mapper"), STUBS, ids=[m.__name__.rsplit(".", 1)[1] for m, _ in STUBS])
def test_a_populated_table_raises(module, mapper):
    record = module.NATIVE_CLASS.__new__(module.NATIVE_CLASS)
    native = GraphModel(graph={module.NATIVE_CLASS: {"x": record}})
    with pytest.raises(NotImplementedError, match="phase 2"):
        mapper(native)

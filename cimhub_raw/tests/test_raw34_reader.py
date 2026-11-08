"""Seed reader and writer on the committed cases (R0 baseline, before the reader fixes)."""

from __future__ import annotations

from pathlib import Path

import pytest

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.raw34_reader import Raw34Reader
from cimhub_raw.raw34_writer import Raw34Writer

CASES = Path(__file__).parent / "cases"
IEEE14 = CASES / "IEEE14" / "IEEE_14_bus.raw"
WECC240 = CASES / "WECC240" / "240busWECC_2018_PSS.raw"
NODE_BREAKER = Path(__file__).parent / "atoms" / "substation" / "two_bus_node_breaker.raw"


def _differences(first, second) -> list[tuple[str, str, str]]:
    """(class, record key, field) for every record field that differs between two graphs."""
    differences = []
    for cls, records in first.graph.items():
        other = second.graph.get(cls, {})
        assert set(records) == set(other), f"{cls.__name__}: record keys differ"
        for key, record in records.items():
            for name, value in vars(record).items():
                if getattr(other[key], name, None) != value:
                    differences.append((cls.__name__, key, name))
    return differences


@pytest.mark.parametrize(
    ("case", "counts"),
    [
        (IEEE14, {schema.BusRecord: 14, schema.LoadRecord: 11, schema.GeneratorRecord: 5,
                  schema.BranchRecord: 17, schema.TransformerRecord: 3}),
        (WECC240, {schema.BusRecord: 243, schema.LoadRecord: 139, schema.GeneratorRecord: 146,
                   schema.BranchRecord: 329, schema.TransformerRecord: 122, schema.SwitchedShuntRecord: 7}),
    ],
    ids=["IEEE14", "WECC240"],
)
def test_reads_every_record(case, counts):
    model = Raw34Reader(case).read_all()
    assert {cls: model.count(cls) for cls in counts} == counts


@pytest.mark.parametrize(
    "case",
    [
        IEEE14,
        pytest.param(WECC240, marks=pytest.mark.xfail(
            strict=True, reason="writer precision: 1e-7 is written as 0.00000 (RAW_REWRITE_PLAN.md §4.1)")),
    ],
    ids=["IEEE14", "WECC240"],
)
def test_read_write_read_is_lossless(case, tmp_path):
    """Reading what the writer wrote gives the same records."""
    model = Raw34Reader(case).read_all()
    out = tmp_path / "out.raw"
    Raw34Writer().write(model, str(out))
    assert _differences(model, Raw34Reader(out).read_all()) == []


@pytest.mark.xfail(strict=True, reason="extended bus names and the SUBSTATION section are R0 reader work")
def test_reads_the_node_breaker_atom():
    model = Raw34Reader(NODE_BREAKER).read_all()
    assert model.count(schema.BranchRecord) == 2

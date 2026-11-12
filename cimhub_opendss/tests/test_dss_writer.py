"""DssWriter: a deck read, written and read again is the same model (DSS_REWRITE_PLAN.md section 8.2, S6a).

This pins the writer before any exporter depends on it. The written deck must also compile in the engine with the
same elements and the same solved bus voltages as the original.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cimhub_opendss import DssReader, DssWriter
from cimhub_opendss.dss_writer import WRITE_ORDER, format_float
from cimhub_opendss.schema import opendss_schema as schema

from conftest import deck
from engine_compare import assert_same_engine_state

ATOMS = Path(__file__).parent / "atoms"
ATOM_DECKS = sorted(ATOMS.glob("*/*.dss"))

#: Vendored decks whose classes are all in the writer's WRITE_ORDER (no LoadShape, Monitor, EnergyMeter).
WRITER_DECKS = [
    "IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss",
    "IEEE/IEEE123/IEEE123Master.dss",
    "IEEE/IEEE4_xfmrs/4bus-OYOD-UnBal.dss",
]


def _records(model) -> dict:
    """``{class: {lowered name: slots}}`` of every class, ``history`` excluded, floats at the writer's precision
    (``FLOAT_DIGITS``: IEEE8500's ``X=14.798306633595042`` is written ``14.798306633595``). ``like`` is dropped: the
    reader has resolved it into the slots, and the writer does not write it."""
    return {cls: {str(obj.name).lower(): {name: _at_writer_precision(value)
                                          for name, value in {**vars(obj), "like": None}.items()}
                  for obj in model.list_by_class(cls)}
            for cls in model.graph}


def _at_writer_precision(value):
    if isinstance(value, float):
        return float(format_float(value))
    if isinstance(value, list):
        return [_at_writer_precision(item) for item in value]
    return value


def _round_trip(source: Path, tmp_path: Path) -> tuple[Path, object, object]:
    original = DssReader(source).read_all()
    written = tmp_path / "deck.dss"
    DssWriter().write(original, written)
    return written, original, DssReader(written).read_all()


@pytest.mark.parametrize("source", ATOM_DECKS, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_atom_deck_reads_back_the_same(source, tmp_path):
    _, original, reread = _round_trip(source, tmp_path)
    assert _records(reread) == _records(original)


@pytest.mark.parametrize("relative", WRITER_DECKS)
def test_deck_reads_back_the_same_and_solves_the_same(relative, tmp_path):
    source = deck(relative)
    written, original, reread = _round_trip(source, tmp_path)
    assert _records(reread) == _records(original)
    assert_same_engine_state(source, written)


def test_deck_layout(tmp_path):
    """Clear, the base frequency, the circuit, the objects, voltage bases, opens, coordinates: in that order."""
    model = DssReader(ATOMS / "buscoords" / "local.dss").read_all()
    options = model.list_by_class(schema.Options)[0]
    options.defaultbasefreq, options.voltagebases, options.open_terminals = 50.0, [4.16, 0.208], ["Line.l1 1"]
    written = tmp_path / "deck.dss"
    DssWriter().write(model, written)
    lines = written.read_text().splitlines()
    assert lines[:2] == ["Clear", "Set defaultbasefreq=50"]
    assert lines[2].startswith("New Circuit.atom ")
    assert lines[-4:] == ["Set voltagebases=[4.16 0.208]", "CalcVoltageBases", "Open Line.l1 1",
                          "Buscoords deck_buscoords.csv"]
    assert (tmp_path / "deck_buscoords.csv").exists()
    assert not any(line.lower().startswith("new vsource.source") for line in lines)


def test_circuit_name_without_its_source_raises(tmp_path):
    model = DssReader(ATOMS / "vsource" / "mvasc.dss").read_all()
    del model.graph[schema.Vsource]
    with pytest.raises(ValueError, match="only Options.circuit"):
        DssWriter().write(model, tmp_path / "deck.dss")


def test_class_without_a_write_order_raises(tmp_path):
    model = DssReader(ATOMS / "vsource" / "mvasc.dss").read_all()
    model.add_to_graph(schema.Monitor(name="m1"))
    with pytest.raises(ValueError, match=r"no write order for \['Monitor'\]"):
        DssWriter().write(model, tmp_path / "deck.dss")


def test_deck_records_are_not_new_commands():
    with pytest.raises(ValueError, match="Options is not a New command"):
        DssWriter().serialize(schema.Options(name="options"))


@pytest.mark.parametrize("relative", WRITER_DECKS)
def test_per_class_deck_reads_back_the_same_and_solves_the_same(relative, tmp_path):
    source = deck(relative)
    original = DssReader(source).read_all()
    written = tmp_path / "master.dss"
    DssWriter().write(original, written, per_class=True)
    assert _records(DssReader(written).read_all()) == _records(original)
    assert_same_engine_state(source, written)


def test_per_class_layout(tmp_path):
    """The master redirects one file per class, in WRITE_ORDER, between the circuit and the voltage bases."""
    model = DssReader(ATOMS / "buscoords" / "local.dss").read_all()
    written = tmp_path / "master.dss"
    DssWriter().write(model, written, per_class=True)
    redirects = [line for line in written.read_text().splitlines() if line.startswith("Redirect ")]
    files = [line.removeprefix("Redirect ") for line in redirects]
    order = [cls.__name__.lower() + ".dss" for cls in WRITE_ORDER]
    assert files == sorted(files, key=order.index)
    assert sorted(path.name for path in tmp_path.glob("*.dss")) == sorted([*files, "master.dss"])
    assert [line.split()[1] for line in written.read_text().splitlines() if line.lower().startswith("new ")] == ["Circuit.atom"]
    assert all(line.startswith("new ") for name in files for line in (tmp_path / name).read_text().splitlines())


def test_master_named_as_a_class_file_raises(tmp_path):
    model = DssReader(ATOMS / "buscoords" / "local.dss").read_all()
    with pytest.raises(ValueError, match="master Line.dss would be overwritten"):
        DssWriter().write(model, tmp_path / "Line.dss", per_class=True)

"""DssWriter: a deck read, written and read again is the same model (DSS_REWRITE_PLAN.md section 8.2, S6a).

This pins the writer before any exporter depends on it. The written deck must also compile in the engine with the
same elements and the same solved bus voltages as the original.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from cimhub_opendss import DssReader, DssWriter
from cimhub_opendss.dss_writer import WRITE_ORDER, dss_safe_name, format_float
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
    assert_same_engine_state(source, written, exported=False)


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


def test_empty_circuit_name_without_its_source_names_the_circuit(tmp_path):
    model = DssReader(ATOMS / "vsource" / "mvasc.dss").read_all()
    del model.graph[schema.Vsource]
    model.list_by_class(schema.Options)[0].circuit = ""
    with pytest.raises(ValueError, match="only Options.circuit"):
        DssWriter().write(model, tmp_path / "deck.dss")


def test_class_without_a_write_order_raises(tmp_path):
    model = DssReader(ATOMS / "vsource" / "mvasc.dss").read_all()
    model.add_to_graph(schema.Monitor(name="m1"))
    with pytest.raises(ValueError, match=r"no write order for \['Monitor'\]"):
        DssWriter().write(model, tmp_path / "deck.dss")


def test_names_one_once_sanitized_raise(tmp_path):
    """DSS would apply the second as an edit of the first."""
    model = DssReader(ATOMS / "vsource" / "mvasc.dss").read_all()
    model.add_to_graph(schema.Load(name="a b", bus1="sourcebus", kW=1.0))
    model.add_to_graph(schema.Load(name="A_B", bus1="sourcebus", kW=2.0))
    with pytest.raises(ValueError, match=r"DssWriter: Load '(a b|A_B)' and '(a b|A_B)' are both named '(a_b|A_B)'"):
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
    assert_same_engine_state(source, written, exported=False)


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


def test_rdcohms_is_written_per_winding_last():
    """DSS has no RdcOhms array: one wdg= block per winding, after every other slot, so no slot follows a wdg=."""
    transformer = schema.Transformer(name="t", phases=1, windings=2, buses=["a.1", "b.1"], kVs=[7.2, 0.24],
                                     kVAs=[25, 25], RdcOhms=[2.1, 0.004], Seasons=2, Ratings=[30, 35])
    assert DssWriter().serialize(transformer) == (
        "new Transformer.t phases=1 windings=2 buses=[a.1 b.1] kVs=[7.2 0.24] kVAs=[25 25] Seasons=2 Ratings=[30 35] "
        "wdg=1 RdcOhms=2.1 wdg=2 RdcOhms=0.004")


@pytest.mark.parametrize("name, safe", [("a!b", "a_b"), ("c//d", "c_d"), ("http://x", "http:_x"), ("e/f", "e/f")])
def test_comment_starts_are_unsafe(name, safe):
    """The engine reads ``!`` and ``//`` as the start of a comment: ``New Load.a!b bus1=x`` defines Load.a."""
    assert dss_safe_name(name) == safe


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_float_raises(value):
    with pytest.raises(ValueError, match="not a finite number"):
        format_float(value)


@pytest.mark.parametrize("x, y", [(None, 1.0), (1.0, None), (math.nan, 1.0), (1.0, math.inf)])
def test_coordinates_that_are_not_two_finite_numbers_raise(x, y, tmp_path):
    model = DssReader(ATOMS / "buscoords" / "local.dss").read_all()
    model.list_by_class(schema.Buscoords)[0].x, model.list_by_class(schema.Buscoords)[0].y = x, y
    with pytest.raises(ValueError, match="Buscoords .*: coordinates .* are not two finite numbers"):
        DssWriter().write(model, tmp_path / "deck.dss")


def test_coordinates_name_the_bus_as_the_deck_does(tmp_path):
    """A bus name the writer sanitizes in ``bus1=`` is sanitized in the coordinates file too, or it has none."""
    model = DssReader(ATOMS / "buscoords" / "local.dss").read_all()
    model.add_to_graph(schema.Buscoords(name="bus 1", x=1.0, y=2.0))
    DssWriter().write(model, tmp_path / "deck.dss")
    assert "bus_1, 1.0, 2.0" in (tmp_path / "deck_buscoords.csv").read_text().splitlines()


def test_coordinates_file_name_is_quoted(tmp_path):
    """The engine reads ``Buscoords my deck_buscoords.csv`` as the file ``my``."""
    model = DssReader(ATOMS / "buscoords" / "local.dss").read_all()
    DssWriter().write(model, tmp_path / "my deck.dss")
    assert (tmp_path / "my deck.dss").read_text().splitlines()[-1] == 'Buscoords "my deck_buscoords.csv"'


def test_open_target_is_sanitized_as_its_definition(tmp_path):
    model = DssReader(ATOMS / "buscoords" / "local.dss").read_all()
    model.add_to_graph(schema.Line(name="sw 2", bus1="b1", bus2="b3", phases=3, Switch=True))
    model.list_by_class(schema.Options)[0].open_terminals = ["Line.sw 2 1"]
    DssWriter().write(model, tmp_path / "deck.dss")
    lines = (tmp_path / "deck.dss").read_text().splitlines()
    assert "Open Line.sw_2 1" in lines
    assert any(line.startswith("new Line.sw_2 ") for line in lines)


def test_nothing_is_written_when_a_record_fails(tmp_path):
    """A bad record late in the deck leaves no partial deck, class file or coordinates file behind."""
    model = DssReader(ATOMS / "buscoords" / "local.dss").read_all()
    model.add_to_graph(schema.Reactor(name="r", bus1="b1", kvar=math.nan))
    out = tmp_path / "out"
    for per_class in (False, True):
        with pytest.raises(ValueError, match="not a finite number"):
            DssWriter().write(model, out / "deck.dss", per_class=per_class)
        assert not out.exists()


def test_geometry_with_heights_and_no_x_writes_x_zero(tmp_path):
    """A conductor with no x is at x=0 in the engine (``nconds=`` puts every conductor at (0, 0),
    LineGeometry.pas:1075), so the writer writes x=0 and the deck reads back with it."""
    geometry = schema.Linegeometry(name="g", nconds=1, nphases=1, hs=[10.0], wires=["w"], units="ft")
    with pytest.raises(ValueError, match="LineGeometry g has positions"):
        DssWriter().serialize(geometry)
    assert DssWriter()._geometry(geometry, {"w": "wire"}).endswith(" cond=1 wire=w x=0 h=10 units=ft")
    model = DssReader(ATOMS / "buscoords" / "local.dss").read_all()
    model.add_to_graph(schema.Wiredata(name="w", diam=0.5, GMRac=0.2, Rac=0.3))
    model.add_to_graph(geometry)
    DssWriter().write(model, tmp_path / "deck.dss")
    [read_back] = DssReader(tmp_path / "deck.dss").read_all().list_by_class(schema.Linegeometry)
    assert (read_back.xs, read_back.hs) == ([0.0], [10.0])


def test_a_full_matrix_is_written_as_its_lower_triangle(tmp_path):
    """``rmatrix=[1 2 3 | 2 4 5 | 3 5 6]`` used to come back as ``[1 |2 3 |2 4 5]`` (the first six values)."""
    deck = tmp_path / "in.dss"
    deck.write_text("New Linecode.lc nphases=3 rmatrix=[1 2 3 | 2 4 5 | 3 5 6] xmatrix=[1 |0 1 |0 0 1]\n")
    [code] = DssReader(deck).read_all().list_by_class(schema.Linecode)
    assert "rmatrix=[1 |2 4 |3 5 6]" in DssWriter().serialize(code)

"""The RAW v34 reader and writer on the committed cases and on small hand-written files."""

from __future__ import annotations

from pathlib import Path

import pytest

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.raw34_reader import Raw34ParseError, Raw34Reader, tokenize
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


def _raw(tmp_path: Path, body: str, *, header: str = "0, 100.0, 34, 0, 0, 60.0") -> Path:
    """A small RAW file: case line, two blank titles, no system-wide data, then ``body``."""
    path = tmp_path / "case.raw"
    path.write_text(f"{header}\n\n\n0 / END OF SYSTEM-WIDE DATA, BEGIN BUS DATA\n{body}\n", encoding="utf-8")
    return path


# -- tokenizer ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("99,,345,,,3", ["99", None, "345", None, None, "3"]),  # the spec's own example
        ("1 2   3", ["1", "2", "3"]),  # blank-separated
        ("1, 2 ,3", ["1", "2", "3"]),
        ("1,'A, B / C',2", ["1", "A, B / C", "2"]),  # quotes hold commas, blanks and slashes
        ('RATING, 1, "RATE1 ", "SET 1"', ["RATING", "1", "RATE1 ", "SET 1"]),
        ("0, 100.00, 34,  ,  ,", ["0", "100.00", "34", None, None]),  # the WECC240 header
        ("0 / END OF BUS DATA, BEGIN LOAD DATA", ["0"]),  # a comment after /
        ("", []),
    ],
)
def test_tokenize(text, expected):
    assert tokenize(text) == expected


def test_tokenize_keeps_whether_a_field_was_quoted():
    tokens = tokenize("'1', 1")
    assert [token.quoted for token in tokens] == [True, False]


# -- the committed cases -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("case", "counts"),
    [
        (IEEE14, {schema.BusRecord: 14, schema.LoadRecord: 11, schema.FixedShuntRecord: 1, schema.GeneratorRecord: 5,
                  schema.BranchRecord: 17, schema.TransformerRecord: 3, schema.AreaInterchangeRecord: 1}),
        (WECC240, {schema.BusRecord: 243, schema.LoadRecord: 139, schema.GeneratorRecord: 146,
                   schema.BranchRecord: 329, schema.TransformerRecord: 122, schema.SwitchedShuntRecord: 7,
                   schema.ZoneRecord: 14}),
        (NODE_BREAKER, {schema.BusRecord: 2, schema.BranchRecord: 2, schema.SubstationRecord: 2,
                        schema.SubstationNodeRecord: 8, schema.StationSwitchingDeviceRecord: 7,
                        schema.EquipmentTerminalRecord: 4}),
    ],
    ids=["IEEE14", "WECC240", "node_breaker"],
)
def test_reads_every_record(case, counts):
    model = Raw34Reader(case).read_all()
    assert {cls: model.count(cls) for cls in counts} == counts


@pytest.mark.parametrize("case", [IEEE14, WECC240, NODE_BREAKER], ids=["IEEE14", "WECC240", "node_breaker"])
def test_read_write_read_is_lossless(case, tmp_path):
    model = Raw34Reader(case).read_all()
    out = tmp_path / "out.raw"
    Raw34Writer().write(model, str(out))
    assert _differences(model, Raw34Reader(out).read_all()) == []


def test_transformer_controls_are_read():
    """Line 3 past RATE1-12 (COD1 .. NOD1): the seed reader dropped these and kept schema defaults."""
    model = Raw34Reader(WECC240).read_all()
    transformer = model.graph[schema.TransformerRecord]["1001_1002_0_1"]
    assert (transformer.cod1, transformer.cont1, transformer.rma1, transformer.vmi1, transformer.ntp1) == (
        0, 1001, 1.1, 0.9, 989)
    assert model.graph[schema.TransformerRecord]["6103_6104_0_1"].vmi1 == 0.95


def test_a_blank_or_missing_field_is_none():
    """No defaults are filled (RAW-3): WECC240 leaves XFRRAT, NXFRAT and BASFRQ blank."""
    case = Raw34Reader(WECC240).read_all().first(schema.CaseIdentificationRecord)
    assert (case.transformer_ratings_units, case.branch_ratings_units, case.system_base_frequency) == (
        None, None, None)
    transformer = Raw34Reader(IEEE14).read_all().graph[schema.TransformerRecord]["4_7_0_1"]
    assert transformer.ang2 is None  # a 2-winding line 4 is WINDV2, NOMV2 only


def test_case_titles_and_ratings():
    case = Raw34Reader(IEEE14).read_all().first(schema.CaseIdentificationRecord)
    assert case.titles == [" 08/19/93 UW ARCHIVE           100.0  1962 W IEEE 14 BUS TES", ""]
    assert case.general == "GENERAL, THRSHZ=0.0001, PQBRAK=0.7, BLOWUP=5.0"
    assert len(case.ratings) == 12
    assert (case.ratings[0].rating_set_number, case.ratings[0].rating_name) == (1, "RATE1")


def test_extended_bus_names_resolve_to_numbers():
    model = Raw34Reader(NODE_BREAKER).read_all()
    branches = model.list_by_class(schema.BranchRecord)
    assert [(b.from_bus_number, b.to_bus_number, b.circuit) for b in branches] == [(1, 2, "1"), (1, 2, "2")]
    terminal = model.graph[schema.EquipmentTerminalRecord]["1_1_B_2__1"]
    assert (terminal.node_number, terminal.terminal_type, terminal.j_bus, terminal.identifier) == (3, "B", 2, "1")


def test_names_lose_their_padding():
    bus = Raw34Reader(WECC240).read_all().graph[schema.BusRecord]["1001"]
    assert bus.name == "FOURCORN"


# -- fail fast ---------------------------------------------------------------------------------------


def test_another_revision_raises(tmp_path):
    with pytest.raises(Raw34ParseError, match="v34 only"):
        Raw34Reader(_raw(tmp_path, "1,'A',115.0\n0\nQ", header="0, 100.0, 33")).read_all()


def test_a_duplicate_key_raises(tmp_path):
    body = ("1,'A',115.0\n2,'B',115.0\n0 / END OF BUS DATA\n0 / END OF LOAD DATA\n0 / END OF FIXED SHUNT DATA\n"
            "0 / END OF GENERATOR DATA\n1,2,'1',0.01,0.1\n1,2,'1 ',0.02,0.2\n0\nQ")
    with pytest.raises(Raw34ParseError, match=r"duplicate BranchRecord '1_2_1' \(first on line"):
        Raw34Reader(_raw(tmp_path, body)).read_all()


def test_an_unknown_extended_name_raises(tmp_path):
    body = "1,'A',115.0\n0 / END OF BUS DATA\n'B           115.0','1',1\n0\nQ"
    with pytest.raises(Raw34ParseError, match="matches no bus"):
        Raw34Reader(_raw(tmp_path, body)).read_all()


def test_too_many_fields_raise(tmp_path):
    with pytest.raises(Raw34ParseError, match="14 fields where the record has 13"):
        Raw34Reader(_raw(tmp_path, "1,'A',115.0,1,1,1,1,1.0,0.0,1.1,0.9,1.1,0.9,7\n0\nQ")).read_all()


def test_a_value_that_does_not_convert_raises(tmp_path):
    with pytest.raises(Raw34ParseError, match="BusRecord.base_voltage"):
        Raw34Reader(_raw(tmp_path, "1,'A',abc\n0\nQ")).read_all()


def test_a_missing_terminator_raises(tmp_path):
    with pytest.raises(Raw34ParseError, match="no 0 record"):
        Raw34Reader(_raw(tmp_path, "1,'A',115.0")).read_all()


def test_an_unknown_system_wide_record_raises(tmp_path):
    path = tmp_path / "case.raw"
    path.write_text("0, 100.0, 34\n\n\nSOLVERX, X=1\n0 / END OF SYSTEM-WIDE DATA\nQ\n", encoding="utf-8")
    with pytest.raises(Raw34ParseError, match="unknown system-wide data record 'SOLVERX'"):
        Raw34Reader(path).read_all()


def test_a_q_record_ends_the_data(tmp_path):
    model = Raw34Reader(_raw(tmp_path, "1,'A',115.0\n0 / END OF BUS DATA\nQ")).read_all()
    assert model.count(schema.BusRecord) == 1
    assert model.count(schema.LoadRecord) == 0


def test_a_phase_2_section_raises(tmp_path):
    terminators = "\n".join(["0"] * 9)  # the ends of bus .. two-terminal DC
    body = f"1,'A',115.0\n{terminators}\n'VSC1',1,0.5\n1,1,1,0.0\n0\nQ"
    with pytest.raises(NotImplementedError, match="VSC DC LINE section"):
        Raw34Reader(_raw(tmp_path, body)).read_all()

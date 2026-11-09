"""Export atoms: wire catalogs, LineCode, LineGeometry, Line and switches (EXPORT_MAPPING.md S6b), checked against the
original deck in the engine."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import numpy as np
import opendssdirect as dss
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.line_impedance import ImpedanceSource, get_line_sequence_impedance
from cimhub_opendss import DssImporter, DssReader
from cimhub_opendss.exporter.cim_to_dss import DssExporter, cim_to_dss
from cimhub_opendss.exporter.linegeometry import geometry_name
from cimhub_opendss.exporter.naming import Names
from cimhub_opendss.schema import opendss_schema as schema

from conftest import compile_deck
from engine_compare import assert_same_engine_state
from export_atoms import assert_matches_dss_golden, bus_names, export_atom, export_network

ATOMS = Path(__file__).parent / "atoms" / "line"
#: atom -> (elements whose YPrim differs, elements only in the export): every switch carries the invented 1 mOhm
#: (B3), and an open switch with no control gets a SwtControl (E6)
CASES = {
    "codes": ({"line.sw1", "line.fuse1", "line.rec1", "line.tie", "line.sect"}, {"swtcontrol.sect"}),
    "geometry": (set(), set()),
    "cables": (set(), set()),
    "states": ({"line.f_open", "line.r_open", "line.n_open"}, set()),
}


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _network(atom: str):
    path = ATOMS / f"{atom}.dss"
    return DssImporter(path.stem).to_cim(DssReader(path).read_all())


def _model(network, name_source="name"):
    return DssExporter().to_model(network, name_source=name_source)


def _record(model, native_class, name):
    return next(record for record in model.list_by_class(native_class) if str(record.name).lower() == name)


def _object(network, cim_class, name):
    return next(obj for obj in network.graph[cim_class].values() if obj.name == name)


@pytest.mark.parametrize("case", CASES)
def test_export_matches_the_original_in_the_engine(case, tmp_path):
    atom = ATOMS / f"{case}.dss"
    yprim_differs, added = CASES[case]
    written = export_atom(atom, tmp_path, name_source="name")
    assert_same_engine_state(atom, written, yprim_differs=frozenset(yprim_differs), added=frozenset(added))


@pytest.mark.parametrize("case", CASES)
def test_export_under_mrid_and_uri_solves_the_same(case, tmp_path):
    atom = ATOMS / f"{case}.dss"
    for name_source in ("mrid", "uri"):
        written, network = export_network(atom, tmp_path, name_source=name_source)
        assert_same_engine_state(atom, written, by_element=False, bus_names=bus_names(network, name_source))


@pytest.mark.parametrize("case", CASES)
def test_export_matches_golden(case, tmp_path):
    written = export_atom(ATOMS / f"{case}.dss", tmp_path, name_source="mrid")
    assert_matches_dss_golden(written, ATOMS / "export" / f"{case}.dss")


# catalogs ------------------------------------------------------------------------------------------------------

WIRE_PROPERTIES = ("Rdc", "Rac", "GMRac", "radius", "normamps", "emergamps")
CABLE_PROPERTIES = {"CNData": ("k", "DiaStrand", "GmrStrand", "Rstrand", "InsLayer", "DiaIns", "DiaCable"),
                    "TSData": ("DiaShield", "TapeLayer", "TapeLap", "InsLayer", "DiaIns", "DiaCable")}


def _catalog_values(path: Path, dss_class: str, name: str, properties) -> dict[str, float]:
    """The engine's properties of one catalog object, its lengths converted to metres by its own unit selectors."""
    compile_deck(path)
    dss.Text.Command(f"select {dss_class}.{name}")
    values = {slot: float(dss.Properties.Value(slot)) for slot in properties}
    per_metre = {"Rdc": "Runits", "Rac": "Runits", "Rstrand": "Runits", "GMRac": "GMRunits", "GmrStrand": "GMRunits"}
    for slot in values:
        if slot in ("normamps", "emergamps", "k", "TapeLap"):
            continue
        unit = dss.Properties.Value(per_metre.get(slot, "radunits"))
        factor = cim.Length(1.0, unit).to("m")
        values[slot] = values[slot] / factor if slot in ("Rdc", "Rac", "Rstrand") else values[slot] * factor
    return values


@pytest.mark.parametrize("dss_class, name", [("WireData", "CU_1/0"), ("WireData", "ACSR_1/0"),
                                             ("CNData", "CN_250"), ("TSData", "TS_1/0")])
def test_wire_values_match_the_engine(dss_class, name, tmp_path):
    atom = ATOMS / "cables.dss"
    written = export_atom(atom, tmp_path, name_source="name")
    properties = WIRE_PROPERTIES + CABLE_PROPERTIES.get(dss_class, ())
    expected = _catalog_values(atom, dss_class, name, properties)
    actual = _catalog_values(written, dss_class, name, properties)
    assert actual == pytest.approx(expected, rel=1e-9)


def test_unused_catalogs_are_exported():
    model = _model(_network("cables"))
    assert _record(model, schema.Wiredata, "acsr_1/0").normamps == 230.0
    assert _record(model, schema.Linecode, "mtx601").nphases == 3


def test_sequence_code_c_is_at_the_deck_frequency():
    code = _record(_model(_network("cables")), schema.Linecode, "3-1/0c_2/0cn_t")
    # c1 = 10.4308823411236 nF/km in the atom
    assert (code.units, float(code.baseFreq)) == ("m", 60.0)
    assert float(code.C1) == pytest.approx(10.4308823411236e-3, rel=1e-12)


def test_matrix_code_without_b_writes_zero_capacitance():
    network = _network("codes")
    code = _object(network, cim.PerLengthPhaseImpedance, "mtx603")
    for data in code.PhaseImpedanceData:
        data.b = None
    assert _record(_model(network), schema.Linecode, "mtx603").cmatrix == [0.0, 0.0, 0.0]


def test_calculated_frequency_other_than_the_deck_raises():
    network = _network("codes")
    _object(network, cim.PerLengthPhaseImpedance, "mtx603").calculatedFrequency = cim.Frequency(50.0)
    with pytest.raises(ValueError, match="calculatedFrequency 50.0 Hz differs from the network's 60.0 Hz"):
        _model(network)


def test_shunt_conductance_raises():
    network = _network("codes")
    code = _object(network, cim.PerLengthPhaseImpedance, "mtx603")
    for data in code.PhaseImpedanceData:
        data.g = cim.ConductancePerLength(1e-6)
    with pytest.raises(ValueError, match="no shunt conductance"):
        _model(network)


# geometry ------------------------------------------------------------------------------------------------------


def test_geometry_per_offset_is_its_own_record():
    network = _network("geometry")
    line = _object(network, cim.ACLineSegment, "g_m")
    line.spacingYOffset = cim.Length(1.5, "m")
    model = _model(network)
    lifted = _record(model, schema.Linegeometry, "601_1p5m")
    plain = _record(model, schema.Linegeometry, "601")
    assert lifted.hs == pytest.approx([h + 1.5 for h in plain.hs])
    assert _record(model, schema.Line, "g_m").geometry == "601_1p5m"


def test_geometry_name_at_offset_zero_is_the_configuration():
    configuration = cim.WireConfiguration(mRID="wc_x", name="x")
    names = Names("name")
    assert (geometry_name(configuration, 0.0, names), geometry_name(configuration, 9.144, names)) == ("x", "x_9p144m")


def test_geometry_neutral_is_reduced_and_off_the_bus():
    model = _model(_network("geometry"))
    assert _record(model, schema.Linegeometry, "601").reduce is True
    line = _record(model, schema.Line, "g601")
    assert (line.bus1, line.phases) == ("sourcebus.1.2.3", 3)


def test_bare_spacing_line_raises():
    network = _network("geometry")
    line = _object(network, cim.ACLineSegment, "g601")
    line.WireSpacing, line.WireConfiguration = line.WireConfiguration.WireSpacing, None
    with pytest.raises(ValueError, match="a WireSpacing without a WireConfiguration is not exported"):
        _model(network)


# lines ---------------------------------------------------------------------------------------------------------


def _lumped(network, name: str, *, with_length: bool):
    """Line ``name`` with its code replaced by the same whole-line lumped values."""
    line = _object(network, cim.ACLineSegment, name)
    whole = get_line_sequence_impedance(line, "ohm", derive=ImpedanceSource.PER_LENGTH_SEQ)
    line.PerLengthImpedance = None
    line.r, line.x, line.r0, line.x0 = (cim.Resistance(whole.r), cim.Reactance(whole.x), cim.Resistance(whole.r0),
                                        cim.Reactance(whole.x0))
    line.bch, line.b0ch = cim.Susceptance(whole.b), cim.Susceptance(whole.b0)
    if not with_length:
        line.length = None
    return line


def _yprim(path: Path, element: str) -> np.ndarray:
    compile_deck(path)
    dss.Solution.Solve()  # the engine builds YPrim at the first solution
    dss.Circuit.SetActiveElement(element)
    return np.array(dss.CktElement.YPrim())


@pytest.mark.parametrize("with_length", [True, False])
def test_lumped_line_is_written_per_km(with_length, tmp_path):
    """seq2 is 0.2 km: its whole-line values per km at 0.2 km, or the values themselves at length 1."""
    network = _network("codes")
    _lumped(network, "seq2", with_length=with_length)
    record = _record(_model(network), schema.Line, "seq2")
    assert (str(record.units), record.linecode) == ("km", None)
    assert record.length == pytest.approx(0.2 if with_length else 1.0)
    written = tmp_path / "lumped.dss"
    cim_to_dss(network, written, name_source="name")
    assert np.allclose(_yprim(written, "Line.seq2"), _yprim(ATOMS / "codes.dss", "Line.seq2"), rtol=1e-9)


def test_lumped_line_without_length_keeps_its_whole_values():
    network = _network("codes")
    line = _lumped(network, "seq2", with_length=False)
    record = _record(_model(network), schema.Line, "seq2")
    assert record.length == 1.0
    assert record.r1 == pytest.approx(line.r.to("ohm"), rel=1e-12)


def test_lumped_line_without_zero_sequence_raises():
    network = _network("codes")
    line = _lumped(network, "seq1", with_length=True)
    line.r0 = line.x0 = None
    with pytest.raises(ValueError, match=r"\['r0', 'x0'\] unset"):
        _model(network)


def test_sequence_code_on_one_phase_raises():
    network = _network("codes")
    line = _object(network, cim.ACLineSegment, "seq3")
    line.PerLengthImpedance = _object(network, cim.ACLineSegment, "seq1").PerLengthImpedance
    with pytest.raises(ValueError, match="1 phase conductors on PerLengthSequenceImpedance .* of 3"):
        _model(network)


def test_line_ratings_and_units():
    line = _record(_model(_network("codes")), schema.Line, "l2")
    assert (line.normamps, line.emergamps, str(line.units), line.length) == (200.0, 345.0, "m", pytest.approx(152.4))


# switches ------------------------------------------------------------------------------------------------------


def test_switch_carries_the_invented_impedance():
    line = _record(_model(_network("codes")), schema.Line, "fuse1")
    assert (line.Switch, line.r1, line.x1, line.length, str(line.units)) == (True, 1e-3, 0.0, 1.0, "m")


def test_switch_controls_and_states():
    model = _model(_network("states"))
    fuse = _record(model, schema.Fuse, "f_open")
    assert (fuse.MonitoredObj, fuse.RatedCurrent) == ("Line.f_open", 65.0)
    assert fuse.Normal == fuse.State == ["open"] * 3  # the engine sets a fuse per phase
    recloser = _record(model, schema.Recloser, "r_open")
    assert (recloser.Normal, recloser.State) == ("open", "open")
    control = _record(model, schema.Swtcontrol, "n_open")
    assert (control.SwitchedObj, control.Normal, control.State) == ("Line.n_open", "open", "closed")
    [options] = model.list_by_class(schema.Options)
    assert options.open_terminals == ["Line.f_open 1", "Line.r_open 1"]


def test_closed_switches_get_no_swtcontrol():
    model = _model(_network("codes"))
    assert sorted(record.name for record in model.list_by_class(schema.Swtcontrol)) == ["sect", "tie"]
    assert not _record(model, schema.Fuse, "fuse1").State

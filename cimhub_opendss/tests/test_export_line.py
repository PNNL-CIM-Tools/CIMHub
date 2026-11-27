"""Export atoms: wire catalogs, LineCode, LineGeometry, Line and switches (EXPORT_MAPPING.md S6b), checked against the
original deck in the engine."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import numpy as np
import opendssdirect as dss
import pytest

from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.line_impedance import ImpedanceSource, get_line_sequence_impedance
from cimhub_core.getters.wire import get_configuration_wires
from cimhub_opendss import DssImporter, DssReader
from cimhub_opendss.exporter import switch
from cimhub_opendss.exporter.cim_to_dss import DssExporter, cim_to_dss
from cimhub_opendss.exporter.linegeometry import geometry_name
from cimhub_opendss.exporter.options import EARTH_MODELS, earth_model
from cimhub_opendss.exporter.naming import Names
from cimhub_opendss.schema import opendss_schema as schema

from conftest import compile_deck
from engine_compare import assert_same_engine_state, engine_settings
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
    assert (code.units, code.baseFreq) == ("m", 60.0)
    assert code.C1 == pytest.approx(10.4308823411236e-3, rel=1e-12)


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


def test_a_template_line_code_beside_geometry_is_a_linecode_with_no_earth(tmp_path):
    """DSS-14: a LineCode's WireConfiguration has no WireSpacing, so it is no LineGeometry and names no earth model."""
    deck = tmp_path / "mixed.dss"
    deck.write_text((ATOMS / "geometry.dss").read_text()
                    + "New Linecode.c1 nphases=3 r1=0.3 x1=0.6 r0=0.6 x0=1.8 C1=10 C0=4 units=km\n"
                    + "New Line.c1 bus1=n2 bus2=n4 linecode=c1 length=1 units=km\n")
    network = DssImporter(deck.stem).to_cim(DssReader(deck).read_all())
    assert earth_model(network) == earth_model(_network("geometry"))
    model = _model(network)
    line = _record(model, schema.Line, "c1")
    assert (line.linecode, line.geometry) == ("c1", None)
    assert {str(record.name) for record in model.list_by_class(schema.Linegeometry)} == {"601", "s510"}


def test_geometry_per_offset_is_its_own_record():
    network = _network("geometry")
    line = _object(network, cim.ACLineSegment, "g_m")
    line.ySpacingOffset = cim.Length(1.5, "m")
    model = _model(network)
    lifted = _record(model, schema.Linegeometry, "601_1p5m")
    plain = _record(model, schema.Linegeometry, "601")
    assert lifted.hs == pytest.approx([h + 1.5 for h in plain.hs])
    assert _record(model, schema.Line, "g_m").geometry == "601_1p5m"


def test_geometry_name_at_offset_zero_is_the_configuration():
    configuration = cim.WireConfiguration(mRID="wc_x", name="x")
    names = Names("name")
    assert (geometry_name(configuration, 0.0, names), geometry_name(configuration, 9.144, names)) == ("x", "x_9p144m")


def test_geometry_name_rounds_the_offset_to_the_mm():
    configuration = cim.WireConfiguration(mRID="wc_x", name="x")
    assert geometry_name(configuration, 10.363199999999999, Names("name")) == "x_10p363m"


@pytest.mark.parametrize("offset", [0.0004, -0.0004])
def test_geometry_name_within_a_mm_of_zero_is_the_configuration(offset):
    """The name is the offset rounded to the mm, so one that rounds to 0 (or -0.0) has no suffix."""
    configuration = cim.WireConfiguration(mRID="wc_x", name="x")
    assert geometry_name(configuration, offset, Names("name")) == "x"


def test_two_offsets_within_a_mm_raise():
    network = _network("geometry")
    _object(network, cim.ACLineSegment, "g_m").ySpacingOffset = cim.Length(1.5, "m")
    _object(network, cim.ACLineSegment, "g601").ySpacingOffset = cim.Length(1.5002, "m")
    with pytest.raises(ValueError, match="share one LineGeometry name"):
        _model(network)


def test_geometry_neutral_is_reduced_and_off_the_bus():
    model = _model(_network("geometry"))
    assert _record(model, schema.Linegeometry, "601").reduce is True
    line = _record(model, schema.Line, "g601")
    assert (line.bus1, line.phases) == ("sourcebus.1.2.3", 3)


def test_bare_spacing_line_without_wire_info_raises():
    network = _network("geometry")
    line = _object(network, cim.ACLineSegment, "g601")
    line.WireSpacing, line.WireConfiguration = line.WireConfiguration.WireSpacing, None
    with pytest.raises(ValueError, match="has a WireSpacing but no ACLineSegmentPhase.WireInfo"):
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


@pytest.mark.parametrize("metres", [0.0, -200.0])
def test_lumped_line_of_length_zero_or_less_raises(metres):
    """A DSS line's impedance is per length: the engine cannot solve one of length 0, and solves a negative one
    silently (a voltage rise)."""
    network = _network("codes")
    line = _lumped(network, "seq2", with_length=True)
    line.length = cim.Length(metres, "m")
    with pytest.raises(ValueError, match=r"ACLineSegment.*seq2.*: length -?[\d.]+ km with lumped impedance"):
        _model(network)


@pytest.mark.parametrize("atom, name", [("codes", "l1"), ("codes", "seq1"), ("geometry", "g601"),
                                        ("geometry", "s510")])
@pytest.mark.parametrize("metres", [0.0, -10.0])
def test_line_of_length_zero_or_less_raises(atom, name, metres):
    """A template code, an own code, a geometry and a spacing line: the same rule as a lumped one."""
    network = _network(atom)
    _object(network, cim.ACLineSegment, name).length = cim.Length(metres, "m")
    with pytest.raises(ValueError, match=rf"ACLineSegment.*{name}.*: length -?[\d.]+ m; a DSS line needs a "
                                         r"positive length"):
        _model(network)


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


def test_a_lines_own_impedance_is_written_inline():
    """isTemplate=false is the line's own impedance (skill wire-configuration): inline on the Line, no LineCode."""
    model = _model(_network("codes"))
    line = _record(model, schema.Line, "seq1")
    assert (line.linecode, line.r1, line.x1, str(line.units)) == (None, pytest.approx(3e-4), pytest.approx(6e-4), "m")
    assert {str(code.name) for code in model.list_by_class(schema.Linecode)} == {"mtx601", "mtx603"}


def test_an_own_impedance_two_lines_use_raises():
    network = _network("codes")
    code = _object(network, cim.ACLineSegment, "seq1").PerLengthImpedance
    other = _object(network, cim.ACLineSegment, "seq2")
    other.PerLengthImpedance = code
    code.ACLineSegments.append(other)
    with pytest.raises(ValueError, match="isTemplate=false marks one line's own impedance, but 2 lines use it"):
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


def test_normal_switch_state_exports_an_as_built_model():
    network = _network("states")
    for cim_class in switch.CIM_CLASSES:
        for obj in network.graph.get(cim_class, {}).values():
            obj.open = None  # as built: only normalOpen is set
    with pytest.raises(ValueError, match="open is unset"):
        _model(network)
    model = DssExporter().to_model(network, name_source="name", switch_state="normal")
    control = _record(model, schema.Swtcontrol, "n_open")
    assert (control.Normal, control.State) == ("open", "open")
    [options] = model.list_by_class(schema.Options)
    assert options.open_terminals == ["Line.f_open 1", "Line.n_open 1", "Line.r_open 1"]


def test_unknown_switch_state_raises():
    with pytest.raises(ValueError, match="switch_state must be one of"):
        DssExporter().to_model(_network("states"), switch_state="nominal")


def test_closed_switches_get_no_swtcontrol():
    model = _model(_network("codes"))
    assert sorted(record.name for record in model.list_by_class(schema.Swtcontrol)) == ["sect", "tie"]
    assert not _record(model, schema.Fuse, "fuse1").State


# earth model and reclosures (EXPORT_MAPPING.md S6g) -------------------------------------------------------------------


@pytest.mark.parametrize("case", ["codes", "states"])
def test_reclosures_match_the_engine(case, tmp_path):
    atom = ATOMS / f"{case}.dss"
    properties = {"Recloser": ("Shots", "RecloseIntervals")}
    assert engine_settings(export_atom(atom, tmp_path, name_source="name"), properties) == \
        engine_settings(atom, properties)


def test_recloser_without_sequences_does_not_reclose():
    network = _network("codes")
    recloser = _object(network, cim.Recloser, "rec1")
    recloser.RecloseSequences.clear()
    record = _record(_model(network), schema.Recloser, "rec1")
    assert (record.Shots, record.RecloseIntervals) == (1, [])


def test_reclosures_on_another_switch_raise():
    breaker = cim.Breaker(mRID="sw_b1", name="b1", open=False, normalOpen=False)
    breaker.RecloseSequences.append(cim.RecloseSequence(mRID="sw_b1_rs1", recloseStep=1, ProtectedSwitch=breaker))
    with pytest.raises(ValueError, match="RecloseSequences on a Breaker"):
        switch._control(breaker, Names("name"), "actual")


def test_geometry_lines_write_their_earth():
    network = _network("geometry")
    model = _model(network)
    [options] = model.list_by_class(schema.Options)
    assert str(options.earthmodel) == "Deri"
    assert _record(model, schema.Line, "g601").rho == 100.0


def test_every_earth_model_kind_is_mapped():
    """earth_model looks EARTH_MODELS up without a guard: a kind a new profile adds must be mapped first."""
    assert set(EARTH_MODELS) == set(cim.EarthModelKind)


def test_two_earth_models_raise():
    network = _network("geometry")
    configuration = next(iter(network.graph[cim.WireConfiguration].values()))
    configuration.EarthResistivity = cim.EarthResistivity(mRID="earth_carson",
                                                          earthModelType=cim.EarthModelKind.carson)
    with pytest.raises(ValueError, match="WireConfigurations over earth models"):
        _model(network)


# spacing lines: a direct WireSpacing and a WireInfo on each ACLineSegmentPhase (the EPRI shape) -----------------------


def _as_spacing_lines(network):
    """Each WireConfiguration line rewritten as a spacing line: its configuration's spacing on the line, and each
    configuration wire on the phase of its sequence number."""
    for line in network.graph[cim.ACLineSegment].values():
        wires = dict(get_configuration_wires(line.WireConfiguration))
        line.WireSpacing, line.WireConfiguration = line.WireConfiguration.WireSpacing, None
        for phase in line.ACLineSegmentPhases:
            phase.WireInfo = wires[phase.sequenceNumber]


def test_spacing_lines_match_their_configuration_lines_in_the_engine(tmp_path):
    network = _network("geometry")
    _as_spacing_lines(network)
    written = tmp_path / "spacing.dss"
    cim_to_dss(network, written, name_source="name")
    assert_same_engine_state(ATOMS / "geometry.dss", written)


def test_wire_configuration_and_phase_wires_raise():
    network = _network("geometry")
    line = _object(network, cim.ACLineSegment, "g601")
    line.ACLineSegmentPhases[0].WireInfo = _object(network, cim.OverheadWireInfo, "ACSR_4/0")
    with pytest.raises(ValueError, match="has both a WireConfiguration and ACLineSegmentPhase.WireInfo"):
        _model(network)


# ln_1 and ln_2 share spacing, offset and wires; ln_3 has other wires, ln_4 another offset. ln_c1 and ln_c3 are the two
# circuits of a double-circuit spacing (ln_c3 is renumbered onto 8, 9, 10 and the shared neutral 4 where used).
SPACING_LINES = """Profile = cim18v17
Object BaseVoltage: mRID=bv, name=bv, nominalVoltage (kV)=12.47
Object Feeder: mRID=fdr, name=fdr
Object EarthResistivity: mRID=earth, name=earth, earthModelType=carson, rho (ohm)=100
Object EnergySource: mRID=src, name=src, node=n0, nominalVoltage (kV)=12.47, voltageMagnitude (kV)=12.47, voltageAngle (deg)=0, r (ohm)=0, x (ohm)=1, r0 (ohm)=0, x0 (ohm)=1, BaseVoltage=bv, EquipmentContainer=fdr
Table OverheadWireInfo: mRID, name, rAC25 (ohm/mi), gmr (ft), radius (in), ratedCurrent (A)
    wire_4/0, 4/0, 0.592, 0.00814, 0.2815, 340.0
    wire_1/0, 1/0, 1.12,  0.00446, 0.199,  230.0
Object XYSpacing: mRID=spc_arm, name=arm, isTemplate=true
Table WirePosition: mRID, XYSpacing=spc_arm, sequenceNumber, kind, xCoord (ft), yCoord (ft)
    spc_arm_1, 1, phase,   0,   0
    spc_arm_2, 2, phase,   2.5, 0
    spc_arm_3, 3, phase,   7,   0
    spc_arm_4, 4, neutral, 4,   -4
Object XYSpacing: mRID=spc_dbl, name=dbl, isTemplate=true
Table WirePosition: mRID, XYSpacing=spc_dbl, sequenceNumber, circuitNumber, kind, xCoord (ft), yCoord (ft)
    spc_dbl_1,  1,  1, phase,   -4, 0
    spc_dbl_2,  2,  1, phase,    0, 0
    spc_dbl_3,  3,  1, phase,    4, 0
    spc_dbl_8,  8,  3, phase,   -4, -4
    spc_dbl_9,  9,  3, phase,    0, -4
    spc_dbl_10, 10, 3, phase,    4, -4
    spc_dbl_4,  4,  0, neutral,  0, -8
Table ACLineSegment: mRID, name, node1, node2, phases, length (ft), ySpacingOffset (ft), WireSpacing, BaseVoltage, EquipmentContainer=fdr
    ln_1,  ln_1,  n0, n1, ABCN, 500, 28, spc_arm, bv
    ln_2,  ln_2,  n1, n2, ABCN, 300, 28, spc_arm, bv
    ln_3,  ln_3,  n2, n3, ABCN, 200, 28, spc_arm, bv
    ln_4,  ln_4,  n3, n4, ABCN, 200, 30, spc_arm, bv
    ln_c1, ln_c1, n4, n5, ABCN, 100, 40, spc_dbl, bv
    ln_c3, ln_c3, n5, n6, ABCN, 100, 40, spc_dbl, bv
Update Table ACLineSegmentPhase: mRID, WireInfo
    ln_1_A, wire_4/0
    ln_1_B, wire_4/0
    ln_1_C, wire_4/0
    ln_1_N, wire_1/0
    ln_2_A, wire_4/0
    ln_2_B, wire_4/0
    ln_2_C, wire_4/0
    ln_2_N, wire_1/0
    ln_3_A, wire_1/0
    ln_3_B, wire_1/0
    ln_3_C, wire_1/0
    ln_3_N, wire_1/0
    ln_4_A, wire_4/0
    ln_4_B, wire_4/0
    ln_4_C, wire_4/0
    ln_4_N, wire_1/0
    ln_c1_A, wire_4/0
    ln_c1_B, wire_4/0
    ln_c1_C, wire_4/0
    ln_c1_N, wire_1/0
    ln_c3_A, wire_1/0
    ln_c3_B, wire_1/0
    ln_c3_C, wire_1/0
    ln_c3_N, wire_1/0
"""


def _spacing_network(tmp_path):
    path = tmp_path / "spacing_lines.cimtbl"
    path.write_text(SPACING_LINES)
    network = load_model(path)
    for phase in _mrid(network, cim.ACLineSegment, "ln_c3").ACLineSegmentPhases:
        phase.sequenceNumber = {"A": 8, "B": 9, "C": 10, "N": 4}[phase.phase.value]
    return network


def _mrid(network, cim_class, mrid):
    return next(obj for obj in network.graph[cim_class].values() if obj.mRID == mrid)


def _spacing_model(network):
    """The .cimtbl names no nodes, so it is exported under mRIDs."""
    return _model(network, name_source="mrid")


def _geometries(model) -> dict[str, schema.Linegeometry]:
    return {str(record.name): record for record in model.list_by_class(schema.Linegeometry)}


def test_spacing_lines_share_a_geometry_only_with_the_same_spacing_offset_and_conductors(tmp_path):
    model = _spacing_model(_spacing_network(tmp_path))
    lines = {str(record.name): record.geometry for record in model.list_by_class(schema.Line)}
    assert lines == {"ln_1": "ln_1_geometry", "ln_2": "ln_1_geometry", "ln_3": "ln_3_geometry",
                     "ln_4": "ln_4_geometry", "ln_c1": "ln_c1_geometry", "ln_c3": "ln_c3_geometry"}
    assert sorted(_geometries(model)) == ["ln_1_geometry", "ln_3_geometry", "ln_4_geometry", "ln_c1_geometry",
                                          "ln_c3_geometry"]


def test_spacing_geometry_has_the_line_s_positions_wires_and_phases(tmp_path):
    geometry = _geometries(_spacing_model(_spacing_network(tmp_path)))["ln_1_geometry"]
    assert (geometry.nconds, geometry.nphases, geometry.reduce, str(geometry.units)) == (4, 3, True, "m")
    assert [str(wire) for wire in geometry.wires] == ["wire_4/0", "wire_4/0", "wire_4/0", "wire_1/0"]
    # the arm at 28 ft: phases at 28 ft, the neutral 4 ft below
    assert geometry.xs == pytest.approx([0.0, 2.5 * 0.3048, 7 * 0.3048, 4 * 0.3048])
    assert geometry.hs == pytest.approx([28 * 0.3048] * 3 + [24 * 0.3048])


def test_each_circuit_of_a_double_circuit_takes_its_own_positions(tmp_path):
    geometries = _geometries(_spacing_model(_spacing_network(tmp_path)))
    lower, upper = geometries["ln_c3_geometry"], geometries["ln_c1_geometry"]
    # circuit 3 hangs 4 ft below circuit 1, and both have the shared neutral last
    assert lower.hs == pytest.approx([36 * 0.3048] * 3 + [32 * 0.3048])
    assert upper.hs == pytest.approx([40 * 0.3048] * 3 + [32 * 0.3048])
    assert [str(wire) for wire in lower.wires] == ["wire_1/0"] * 4


def test_spacing_lines_take_the_network_earth(tmp_path):
    model = _spacing_model(_spacing_network(tmp_path))
    [options] = model.list_by_class(schema.Options)
    assert str(options.earthmodel) == "Carson"
    assert {record.rho for record in model.list_by_class(schema.Line)} == {100.0}


def test_spacing_line_without_an_earth_raises(tmp_path):
    network = _spacing_network(tmp_path)
    network.graph[cim.EarthResistivity].clear()
    with pytest.raises(ValueError, match="takes the network's one EarthResistivity .* the network has 0"):
        _spacing_model(network)


def test_spacing_lines_with_several_earths_raise(tmp_path):
    network = _spacing_network(tmp_path)
    network.add_to_graph(cim.EarthResistivity(mRID="earth_2", earthModelType=cim.EarthModelKind.deri))
    with pytest.raises(ValueError, match="takes the network's one EarthResistivity .* the network has 2"):
        _spacing_model(network)


def test_spacing_line_with_a_phase_without_a_wire_raises(tmp_path):
    network = _spacing_network(tmp_path)
    _mrid(network, cim.ACLineSegmentPhase, "ln_1_N").WireInfo = None
    with pytest.raises(ValueError, match="'ln_1_N' has no WireInfo, and other phases have one"):
        _spacing_model(network)


def test_spacing_line_with_a_phase_off_its_spacing_raises(tmp_path):
    network = _spacing_network(tmp_path)
    _mrid(network, cim.ACLineSegmentPhase, "ln_1_C").sequenceNumber = 9
    with pytest.raises(ValueError, match=r"on sequence numbers \[9\], which XYSpacing 'spc_arm' has no conductor"):
        _spacing_model(network)



# a MultiCircuitGroup with two lines in the network is one DSS line on the whole structure, with jumpers (H1) ----------
# ln_a on positions 1-3 and ln_b on 4-6 share the neutral on 7, both leaving n0: the boundary example's double circuit
COUPLED = """Profile = cim18v17
Object BaseVoltage: mRID=bv, name=bv, nominalVoltage (kV)=12.47
Object Feeder: mRID=fdr, name=fdr
Object EarthResistivity: mRID=earth, name=earth, earthModelType=carson, rho (ohm)=100
Object EnergySource: mRID=src, name=src, node=n0, nominalVoltage (kV)=12.47, voltageMagnitude (kV)=12.47, voltageAngle (deg)=0, r (ohm)=0.1, x (ohm)=1, r0 (ohm)=0.1, x0 (ohm)=1, BaseVoltage=bv, EquipmentContainer=fdr
Object LoadResponseCharacteristic: mRID=lrc, name=lrc, exponentModel=false, pConstantPower=1, pConstantCurrent=0, pConstantImpedance=0, qConstantPower=1, qConstantCurrent=0, qConstantImpedance=0
Table OverheadWireInfo: mRID, name, rAC25 (ohm/mi), gmr (ft), radius (in), ratedCurrent (A)
    wire_397, 397, 0.2357, 0.0265,  0.3915, 590.0
    wire_1/0, 1/0, 1.12,   0.00446, 0.199,  230.0
Object MultiCircuitGroup: mRID=dbl, name=dbl
Object XYSpacing: mRID=spc_dbl, name=spc_dbl, isTemplate=false, MultiCircuitGroup=dbl
Table WirePosition: mRID, XYSpacing=spc_dbl, sequenceNumber, circuitNumber, kind, xCoord (ft), yCoord (ft)
    pos_1, 1, 1, phase,   -4,   -3
    pos_2, 2, 1, phase,   -1.5, -3
    pos_3, 3, 1, phase,    4,   -3
    pos_4, 4, 2, phase,   -3.5,  0
    pos_5, 5, 2, phase,    0,    1.5
    pos_6, 6, 2, phase,    3.5,  0
    pos_7, 7,  , neutral,  0.5, -6
Object ACLineSegment: mRID=ln_a, name=ln_a, node1=n0, node2=a1, phases=ABCN, sequenceNumbers=1 2 3 7, length (ft)=500, ySpacingOffset (ft)=40, WireSpacing=spc_dbl, BaseVoltage=bv, EquipmentContainer=fdr, MultiCircuitGroup=dbl
Object ACLineSegment: mRID=ln_b, name=ln_b, node1=n0, node2=b1, phases=ABCN, sequenceNumbers=4 5 6 7, length (ft)=500, ySpacingOffset (ft)=40, WireSpacing=spc_dbl, BaseVoltage=bv, EquipmentContainer=fdr, MultiCircuitGroup=dbl
Update Table ACLineSegmentPhase: mRID, WireInfo, MultiCircuitGroup
    ln_a_A, wire_397,
    ln_a_B, wire_397,
    ln_a_C, wire_397,
    ln_a_N, wire_1/0, dbl
    ln_b_A, wire_397,
    ln_b_B, wire_397,
    ln_b_C, wire_397,
    ln_b_N, wire_1/0, dbl
Table EnergyConsumer: mRID, name, node, p (kW), q (kvar), phaseConnection=Y, grounded=true, LoadResponse=lrc, BaseVoltage=bv, EquipmentContainer=fdr
    ld_a, ld_a, a1, 800, 200
    ld_b, ld_b, b1, 500, 120
"""

#: the structure written by hand in DSS's own units: conductors 1-6 the two circuits, 7 the neutral, 40 ft up
COUPLED_REFERENCE = """Clear
New Circuit.ref basekv=12.47 bus1=x
Set earthmodel=Carson
New WireData.w397 Rac=0.2357 Runits=mi GMRac=0.0265 GMRunits=ft radius=0.3915 radunits=in
New WireData.w10 Rac=1.12 Runits=mi GMRac=0.00446 GMRunits=ft radius=0.199 radunits=in
New LineGeometry.ref nconds=7 nphases=6 reduce=yes
~ cond=1 wire=w397 x=-4 h=37 units=ft
~ cond=2 wire=w397 x=-1.5 h=37 units=ft
~ cond=3 wire=w397 x=4 h=37 units=ft
~ cond=4 wire=w397 x=-3.5 h=40 units=ft
~ cond=5 wire=w397 x=0 h=41.5 units=ft
~ cond=6 wire=w397 x=3.5 h=40 units=ft
~ cond=7 wire=w10 x=0.5 h=34 units=ft
New Line.ref bus1=x.1.2.3.4.5.6 bus2=y.1.2.3.4.5.6 phases=6 geometry=ref length=500 units=ft rho=100
"""


#: an underbuilt 240 V secondary in the group, on positions 8-10 below the neutral (record checks only: it is fed by
#: nothing)
UNDERBUILT = """Object BaseVoltage: mRID=bv_s, name=bv_s, nominalVoltage (kV)=0.24
Table WirePosition: mRID, XYSpacing=spc_dbl, sequenceNumber, circuitNumber, kind, xCoord (ft), yCoord (ft)
    pos_8,  8,  3, phase,   -0.5, -9
    pos_9,  9,  3, phase,    0.5, -9
    pos_10, 10, 3, neutral,  0,   -9.5
Object ACLineSegment: mRID=ln_s, name=ln_s, node1=s0, node2=s1, phases=s1s2N, sequenceNumbers=8 9 10, length (ft)=300, ySpacingOffset (ft)=40, WireSpacing=spc_dbl, BaseVoltage=bv_s, EquipmentContainer=fdr, MultiCircuitGroup=dbl
Update Table ACLineSegmentPhase: mRID, WireInfo=wire_1/0
    ln_s_s1
    ln_s_s2
    ln_s_N
"""


#: the double circuit on a template spacing (the boundary example's reference shape): a WireConfiguration per
#: circuit, each on its own positions of the one spacing, the neutral on 7 in both
CONFIGURATIONS = """Object WireConfiguration: mRID=wc_a, name=wc_a, numberOfPhases=3, WireSpacing=spc_dbl, EarthResistivity=earth
Object WireConfiguration: mRID=wc_b, name=wc_b, numberOfPhases=3, WireSpacing=spc_dbl, EarthResistivity=earth
Table WireSequenceConfiguration: mRID, sequenceNumber, WireConfiguration, WireInfo
    wc_a_1, 1, wc_a, wire_397
    wc_a_2, 2, wc_a, wire_397
    wc_a_3, 3, wc_a, wire_397
    wc_a_7, 7, wc_a, wire_1/0
    wc_b_4, 4, wc_b, wire_397
    wc_b_5, 5, wc_b, wire_397
    wc_b_6, 6, wc_b, wire_397
    wc_b_7, 7, wc_b, wire_1/0
"""


def _configured(text: str, configured: tuple[str, ...]) -> str:
    """``text`` on the template spacing, each line in ``configured`` on its circuit's WireConfiguration with no
    ACLineSegmentPhase.WireInfo; the others stay spacing lines."""
    text = text.replace("isTemplate=false, MultiCircuitGroup=dbl", "isTemplate=true")
    text = text.replace("Object ACLineSegment: mRID=ln_a,", CONFIGURATIONS + "Object ACLineSegment: mRID=ln_a,")
    rows = []
    for row in text.splitlines():
        for line in configured:
            if row.startswith(f"Object ACLineSegment: mRID={line},"):
                row = row.replace("WireSpacing=spc_dbl", f"WireConfiguration=wc_{line[-1]}")
            if row.startswith(f"    {line}_"):
                row = row.replace("wire_397", "").replace("wire_1/0", "")
        rows.append(row)
    return "\n".join(rows)


def _coupled_network(tmp_path, *, lone: bool = False, underbuilt: bool = False, configured: tuple[str, ...] = ()):
    """The double circuit; with ``lone`` only ln_a and its load (s1-f2 exported on its own); with ``underbuilt`` a
    secondary in the group too; the lines in ``configured`` on WireConfigurations (``_configured``)."""
    text = _configured(COUPLED, configured) if configured else COUPLED
    if lone:
        text = "\n".join(row for row in text.splitlines() if "ln_b" not in row and "ld_b" not in row)
    if underbuilt:
        text += UNDERBUILT
    path = tmp_path / "coupled.cimtbl"
    path.write_text(text)
    return load_model(path)


def _lines(model) -> dict[str, schema.Line]:
    return {str(record.name): record for record in model.list_by_class(schema.Line)}


def test_coupled_group_is_one_line_on_the_whole_structure(tmp_path):
    model = _spacing_model(_coupled_network(tmp_path))
    geometry = _geometries(model)["dbl_geometry"]
    assert list(_geometries(model)) == ["dbl_geometry"]
    assert (geometry.nconds, geometry.nphases, geometry.reduce) == (7, 6, True)
    assert [str(wire) for wire in geometry.wires] == ["wire_397"] * 6 + ["wire_1/0"]
    assert geometry.xs == pytest.approx([x * 0.3048 for x in (-4, -1.5, 4, -3.5, 0, 3.5, 0.5)])
    assert geometry.hs == pytest.approx([h * 0.3048 for h in (37, 37, 37, 40, 41.5, 40, 34)])
    lines = _lines(model)
    assert sorted(lines) == ["dbl", "ln_a_jumper1", "ln_a_jumper2", "ln_b_jumper1", "ln_b_jumper2"]
    coupled = lines["dbl"]
    assert (coupled.geometry, coupled.phases, coupled.bus1, coupled.bus2, coupled.rho) == (
        "dbl_geometry", 6, "dbl_1.1.2.3.4.5.6", "dbl_2.1.2.3.4.5.6", 100.0)
    assert coupled.length == pytest.approx(500 * 0.3048)
    jumpers = {name: (line.bus1, line.bus2, line.phases, line.r1) for name, line in lines.items() if name != "dbl"}
    assert jumpers == {"ln_a_jumper1": ("n0.1.2.3", "dbl_1.1.2.3", 3, 1e-3),
                       "ln_a_jumper2": ("dbl_2.1.2.3", "a1.1.2.3", 3, 1e-3),
                       "ln_b_jumper1": ("n0.1.2.3", "dbl_1.4.5.6", 3, 1e-3),
                       "ln_b_jumper2": ("dbl_2.4.5.6", "b1.1.2.3", 3, 1e-3)}


def test_coupled_line_matches_the_structure_written_in_dss(tmp_path):
    written, reference = tmp_path / "coupled.dss", tmp_path / "reference.dss"
    cim_to_dss(_coupled_network(tmp_path), written, name_source="mrid")
    reference.write_text(COUPLED_REFERENCE)
    exported = _yprim(written, "Line.dbl")
    assert dss.Solution.Converged()
    assert exported == pytest.approx(_yprim(reference, "Line.ref"), rel=1e-9)
    # the circuits are coupled: terminal 1's block between circuit a (rows 1-3) and circuit b (columns 4-6)
    matrix = exported.reshape(12, 24)[:, 0::2] + 1j * exported.reshape(12, 24)[:, 1::2]
    assert np.abs(matrix[0:3, 3:6]).min() > 0.01 * np.abs(matrix[0:3, 0:3]).max()


def test_a_lone_line_of_a_group_takes_its_own_positions(tmp_path):
    model = _spacing_model(_coupled_network(tmp_path, lone=True))
    assert sorted(_lines(model)) == ["ln_a"]
    geometry = _geometries(model)["ln_a_geometry"]
    assert (geometry.nconds, geometry.nphases) == (4, 3)
    assert geometry.hs == pytest.approx([h * 0.3048 for h in (37, 37, 37, 34)])


def test_a_longer_line_goes_on_as_its_own_section(tmp_path):
    """H4: the group is coupled over the shortest line; the rest of ln_b is its own section on its own positions."""
    network = _coupled_network(tmp_path)
    _mrid(network, cim.ACLineSegment, "ln_b").length = cim.Length(600, "ft")
    model = _spacing_model(network)
    lines = _lines(model)
    assert sorted(lines) == ["dbl", "ln_a_jumper1", "ln_a_jumper2", "ln_b", "ln_b_jumper1"]
    assert lines["dbl"].length == pytest.approx(500 * 0.3048)
    rest = lines["ln_b"]
    assert (rest.bus1, rest.bus2, rest.phases, rest.geometry) == ("dbl_2.4.5.6", "b1.1.2.3", 3, "ln_b_geometry")
    assert rest.length == pytest.approx(100 * 0.3048)
    assert _geometries(model)["ln_b_geometry"].nconds == 4
    written = tmp_path / "coupled.dss"
    cim_to_dss(network, written, name_source="mrid")
    compile_deck(written)
    dss.Solution.Solve()
    assert dss.Solution.Converged()


#: three capacitor controls, each monitoring one end of a coupled line: ln_a's two jumpers and ln_b's remainder
COUPLED_CONTROLS = """
Table LinearShuntCompensator: mRID, name, node, phases, phaseConnection, grounded, nomQ (kVAr), nomU (kV), bPerSection (mS), maximumSections, normalSections, sections, BaseVoltage=bv, EquipmentContainer=fdr
    cap_a1, cap_a1, a1, ABC, Y, true, 300, 12.47, 1.93, 1, 1, 1
    cap_a2, cap_a2, a1, ABC, Y, true, 300, 12.47, 1.93, 1, 1, 1
    cap_b,  cap_b,  b1, ABC, Y, true, 300, 12.47, 1.93, 1, 1, 1
Table RegulatingControl: mRID, name, mode=voltage, discrete=true, enabled=true, monitoredPhase=A, ptRatio=60, targetValue (V)=7200, targetDeadband (V)=240, Terminal
    cc_a1, cc_a1, ln_a_T1
    cc_a2, cc_a2, ln_a_T2
    cc_b,  cc_b,  ln_b_T2
Update Table LinearShuntCompensator: mRID, RegulatingControl
    cap_a1, cc_a1
    cap_a2, cc_a2
    cap_b,  cc_b
"""


def test_a_capcontrol_on_a_coupled_line_monitors_the_line_that_carries_its_end(tmp_path):
    """Terminal 1 of a coupled line is its _jumper1's, terminal 2 its _jumper2's or its remainder's (H1, H4)."""
    path = tmp_path / "coupled.cimtbl"
    path.write_text(COUPLED.replace("ln_b, name=ln_b, node1=n0, node2=b1, phases=ABCN, sequenceNumbers=4 5 6 7, "
                                    "length (ft)=500", "ln_b, name=ln_b, node1=n0, node2=b1, phases=ABCN, "
                                    "sequenceNumbers=4 5 6 7, length (ft)=600") + COUPLED_CONTROLS)
    network = load_model(path)
    controls = {str(record.name): (record.element, record.terminal)
                for record in _spacing_model(network).list_by_class(schema.Capcontrol)}
    assert controls == {"cc_a1": ("Line.ln_a_jumper1", 1), "cc_a2": ("Line.ln_a_jumper2", 2),
                        "cc_b": ("Line.ln_b", 2)}
    written = tmp_path / "coupled.dss"
    cim_to_dss(network, written, name_source="mrid")
    compile_deck(written)
    dss.CapControls.First()
    elements = set()
    for _ in range(dss.CapControls.Count()):
        elements.add((dss.CapControls.MonitoredObj().lower(), dss.CapControls.MonitoredTerm()))
        dss.CapControls.Next()
    assert elements == {("line.ln_a_jumper1", 1), ("line.ln_a_jumper2", 2), ("line.ln_b", 2)}


def test_shared_neutral_needs_no_shared_phases(tmp_path):
    """H6: a position on several lines is one conductor, as the EPRI ConductorPosition model has it."""
    network = _coupled_network(tmp_path)
    for name in ("ln_a_N", "ln_b_N"):
        _mrid(network, cim.ACLineSegmentPhase, name).MultiCircuitGroup = None
    geometry = _geometries(_spacing_model(network))["dbl_geometry"]
    assert (geometry.nconds, geometry.nphases) == (7, 6)


def test_underbuilt_secondary_stays_on_its_own_positions(tmp_path):
    """H5: only the group's lines at its highest voltage are coupled."""
    model = _spacing_model(_coupled_network(tmp_path, underbuilt=True))
    assert sorted(_lines(model)) == ["dbl", "ln_a_jumper1", "ln_a_jumper2", "ln_b_jumper1", "ln_b_jumper2", "ln_s"]
    assert (_geometries(model)["dbl_geometry"].nconds, _geometries(model)["ln_s_geometry"].nconds) == (7, 3)
    assert _lines(model)["ln_s"].bus1 == "s0.1.2"


def test_series_pieces_leave_the_group_uncoupled(tmp_path, caplog):
    """H7: two lines on one phase position cannot be one coupled line."""
    network = _coupled_network(tmp_path)
    _phase_on_a_phase(network)
    with caplog.at_level("WARNING"):
        model = _spacing_model(network)
    assert sorted(_lines(model)) == ["ln_a", "ln_b"]
    assert "MultiCircuitGroup 'dbl': ['ln_a', 'ln_b'] name phase positions [1] of one another" in caplog.text


def _phase_on_a_phase(network):
    _mrid(network, cim.ACLineSegmentPhase, "ln_b_A").sequenceNumber = 1


def _other_wire(network):
    _mrid(network, cim.ACLineSegmentPhase, "ln_b_N").WireInfo = _mrid(network, cim.OverheadWireInfo, "wire_397")


def _other_offset(network):
    _mrid(network, cim.ACLineSegment, "ln_b").ySpacingOffset = cim.Length(45, "ft")


def _by_code(network):
    line = _mrid(network, cim.ACLineSegment, "ln_b")
    line.WireSpacing = None
    for phase in line.ACLineSegmentPhases:
        phase.WireInfo = None


def _no_length(network):
    _mrid(network, cim.ACLineSegment, "ln_a").length = cim.Length(0, "ft")


def _other_group(network):
    _mrid(network, cim.ACLineSegmentPhase, "ln_b_N").MultiCircuitGroup = cim.MultiCircuitGroup(mRID="other")


@pytest.mark.parametrize("mutate, message", [
    (_other_group, r"ACLineSegmentPhase 'ln_b_N' of ACLineSegment 'ln_b' in MultiCircuitGroup 'dbl': is a shared "
                   r"phase of MultiCircuitGroup 'other'"),
    (_other_wire, r"sequence number 7 is OverheadWireInfo 'wire_1/0' on one line and OverheadWireInfo 'wire_397'"),
    (_other_offset, r"its lines' ySpacingOffsets \(m, to the mm\) differ"),
    (_by_code, r"ACLineSegment 'ln_b': one of 2 lines of MultiCircuitGroup 'dbl', but has no geometry"),
    (_no_length, r"MultiCircuitGroup 'dbl': its shortest line is 0 m; a DSS line needs a positive length"),
], ids=lambda value: value.__name__.strip("_") if callable(value) else "")
def test_coupled_group_that_one_line_cannot_carry_raises(mutate, message, tmp_path):
    network = _coupled_network(tmp_path)
    mutate(network)
    with pytest.raises(ValueError, match=message):
        _spacing_model(network)


@pytest.mark.parametrize("configured", [("ln_a", "ln_b"), ("ln_a",)], ids=["configurations", "mixed"])
def test_configuration_lines_couple_as_spacing_lines(configured, tmp_path):
    """Lines on WireConfigurations of one template spacing, or one of them and a spacing line, are coupled on the
    same structure as two spacing lines."""
    spacing = _spacing_model(_coupled_network(tmp_path))
    model = _spacing_model(_coupled_network(tmp_path, configured=configured))
    assert _geometries(model)["dbl_geometry"] == _geometries(spacing)["dbl_geometry"]
    assert _lines(model) == _lines(spacing)


def _no_earth(network):
    _mrid(network, cim.WireConfiguration, "wc_b").EarthResistivity = None


def _neutral_off_its_phase(network):
    _mrid(network, cim.WireSequenceConfiguration, "wc_b_7").sequenceNumber = 8


@pytest.mark.parametrize("mutate, message", [
    (_no_earth, r"its lines' earth resistivities \(ohm-m\) differ \{'ln_a': 100.0, 'ln_b': None\}"),
    (_neutral_off_its_phase, r"ACLineSegment 'ln_b' of MultiCircuitGroup 'dbl': wires on sequence numbers "
                             r"\[4, 5, 6, 8\], ACLineSegmentPhases on \[4, 5, 6, 7\] of 4"),
], ids=lambda value: value.__name__.strip("_") if callable(value) else "")
def test_coupled_configuration_lines_that_one_line_cannot_carry_raise(mutate, message, tmp_path):
    network = _coupled_network(tmp_path, configured=("ln_a", "ln_b"))
    mutate(network)
    with pytest.raises(ValueError, match=message):
        _spacing_model(network)


def test_an_unused_configuration_is_written_on_its_own_positions(tmp_path):
    """A template spacing holds both circuits: with ln_a alone, wc_b is written at offset 0 on its positions 4-7,
    not on all seven of the spacing's."""
    network = _coupled_network(tmp_path, lone=True, configured=("ln_a", "ln_b"))
    geometries = _geometries(_spacing_model(network))
    assert sorted(geometries) == ["wc_a_12p192m", "wc_b"]
    unused = geometries["wc_b"]
    assert (unused.nconds, unused.nphases) == (4, 3)
    assert unused.xs == pytest.approx([x * 0.3048 for x in (-3.5, 0, 3.5, 0.5)])
    assert unused.hs == pytest.approx([h * 0.3048 for h in (0, 1.5, 0, -6)])
    _neutral_off_its_phase(network)
    with pytest.raises(ValueError, match=r"WireConfiguration 'wc_b': wires on sequence numbers \[4, 5, 6, 8\], "
                                         r"positions on \[4, 5, 6\]"):
        _spacing_model(network)

# a plain CableInfo (an underground secondary's insulated conductors) is a WireData mirrored above grade (B7) ----------
BURIED = """Profile = cim18v17
Object BaseVoltage: mRID=bv, name=bv, nominalVoltage (kV)=0.208
Object Feeder: mRID=fdr, name=fdr
Object EarthResistivity: mRID=earth, name=earth, earthModelType=carson, rho (ohm)=100
Object EnergySource: mRID=src, name=src, node=n0, nominalVoltage (kV)=0.208, voltageMagnitude (kV)=0.208, voltageAngle (deg)=0, r (ohm)=0, x (ohm)=0.01, r0 (ohm)=0, x0 (ohm)=0.01, BaseVoltage=bv, EquipmentContainer=fdr
Table {wire_class}: mRID, name, rAC25 (ohm/mi), gmr (in), radius (in), insulated, insulationThickness (in)
    wire_ug, ug_4/0, 0.44, 0.1892, 0.2608, true, 0.06
Object XYSpacing: mRID=spc_ug, name=ug, isTemplate=true
Table WirePosition: mRID, XYSpacing=spc_ug, sequenceNumber, kind, xCoord (in), yCoord (ft)
    spc_ug_1, 1, phase,   -0.5, {y}
    spc_ug_2, 2, phase,    0.5, {y}
    spc_ug_3, 3, phase,    0,   {y_up}
    spc_ug_4, 4, neutral,  0,   {y_down}
Object ACLineSegment: mRID=ln_ug, name=ln_ug, node1=n0, node2=n1, phases=ABCN, length (ft)=100, WireSpacing=spc_ug, BaseVoltage=bv, EquipmentContainer=fdr
Update Table ACLineSegmentPhase: mRID, WireInfo
    ln_ug_A, wire_ug
    ln_ug_B, wire_ug
    ln_ug_C, wire_ug
    ln_ug_N, wire_ug
"""


def _buried_network(tmp_path, wire_class, sign):
    path = tmp_path / f"{wire_class}_{sign}.cimtbl"
    path.write_text(BURIED.format(wire_class=wire_class, y=sign * 2.5, y_up=sign * 2.45, y_down=sign * 2.55))
    return load_model(path)


def test_buried_plain_cable_is_wiredata_above_grade(tmp_path):
    model = _spacing_model(_buried_network(tmp_path, "CableInfo", -1))
    [wire] = model.list_by_class(schema.Wiredata)
    assert str(wire.name) == "wire_ug"
    assert _geometries(model)["ln_ug_geometry"].hs == pytest.approx([0.762, 0.762, 0.74676, 0.77724])


def test_buried_plain_cable_matches_the_wire_above_grade_in_the_engine(tmp_path):
    buried, above = tmp_path / "buried.dss", tmp_path / "above.dss"
    cim_to_dss(_buried_network(tmp_path, "CableInfo", -1), buried, name_source="mrid")
    cim_to_dss(_buried_network(tmp_path, "OverheadWireInfo", 1), above, name_source="mrid")
    assert_same_engine_state(above, buried)


def test_closed_tie_across_phases_raises():
    """A tie from B to C (SwitchPhase, GLM S6-9) is written only open: closed, it would join two phases."""
    tie = cim.LoadBreakSwitch(mRID="tie", open=False, normalOpen=True)
    tie.Terminals = [cim.Terminal(mRID=f"tie_T{number}", sequenceNumber=number, phases=code)
                     for number, code in ((1, cim.PhaseCode.B), (2, cim.PhaseCode.C))]
    tie.SwitchPhase = [cim.SwitchPhase(mRID="tie_B", phaseSide1=cim.SinglePhaseKind.B,
                                       phaseSide2=cim.SinglePhaseKind.C)]
    with pytest.raises(ValueError, match=r"a tie from \['B'\] to \['C'\] that is closed \(normal or actual\)"):
        switch._line(tie, Names("mrid"), "actual")


def test_a_floating_earth_writes_the_earthmodel(tmp_path):
    """A deck without geometry keeps its Set earthmodel as an EarthResistivity no line names; the export writes it."""
    path = tmp_path / "deck.dss"
    path.write_text("Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus\nSet earthmodel=carson\n"
                    "New Line.a bus1=sourcebus bus2=b r1=0.1 x1=0.2\n")
    network = DssImporter("atom").to_cim(DssReader(path).read_all())
    assert earth_model(network) == "Carson"

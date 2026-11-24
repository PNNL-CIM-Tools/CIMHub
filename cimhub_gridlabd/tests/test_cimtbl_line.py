"""S3a: lines and switches: classification, the atom, fail fast; the decks run in
test_cimtbl_sweep.py."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden
from cimhub_core.getters.line_impedance import get_line_geometry
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.cimtbl import line, switch
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim
from cimhub_gridlabd.schema import gridlabd as schema

ATOM = Path(__file__).parent / "atoms" / "line"
PARTS = ("overhead_line", "underground_line", "triplex_line", "switch", "fuse", "recloser")
FIELDS = {**line.FIELDS, **switch.FIELDS}


def read(path: Path, **kwargs):
    return GlmReader(path, **kwargs).read_all()


def parts(model, name: str) -> dict:
    return {part.name: part for part in GlmImporter(name).to_cimtbl(model).parts}


@pytest.mark.parametrize("native_cls", FIELDS, ids=lambda cls: cls.__name__)
def test_every_slot_is_classified(native_cls):
    check_fields(FIELDS[native_cls], native_cls)


def spacing_phases(segment) -> dict[int, str]:
    """``{position: phase}`` of a segment's spacing, from its ConductorDistance ends (S2-3)."""
    positions = {}
    for row in segment.WireConfiguration.WireSpacing.ConductorDistance:
        positions[row.sequenceNumber1] = row.fromPhase.value
        if row.sequenceNumber2 is not None:
            positions[row.sequenceNumber2] = row.toPhase.value
    return positions


def segment_phases(segment) -> dict[int, str]:
    return {phase.sequenceNumber: phase.phase.value for phase in segment.ACLineSegmentPhases}


# -- import and bind: the atom ------------------------------------------------------------------------------------

def test_atom_goldens():
    documents = parts(read(ATOM / "line.glm"), "line")
    for name in PARTS:
        assert_matches_golden(documents[name], ATOM / f"line.{name}.cimtbl")


def test_atom_binds(scope):
    network = glm_to_cim(read(ATOM / "line.glm"), name="line")
    segments = {str(s.mRID): s for s in network.list_by_class(cim.ACLineSegment)}
    assert sorted(segments) == ["ln_l1", "ln_line_l2", "ln_line_u1", "ln_overhead_line:3", "ln_tl_1", "ln_tl_2"]
    # every geometry line's ACLineSegmentPhase k is its spacing's position k (S2-3, S3a-3)
    for name in ("ln_l1", "ln_overhead_line:3", "ln_line_u1", "ln_tl_1"):
        assert segment_phases(segments[name]) == spacing_phases(segments[name]), name
    assert segment_phases(segments["ln_tl_1"]) == {1: "s1", 2: "s2", 3: "N"}
    assert segment_phases(segments["ln_line_l2"]) == {1: "A", 2: "C"}  # written CA; matrix rows A, C
    # a matrix configuration is a template its lines share through a WireConfiguration with no spacing
    matrix = segments["ln_line_l2"].WireConfiguration
    assert segments["ln_line_l2"].PerLengthImpedance is None and matrix.WireSpacing is None
    assert (matrix.PerLengthImpedance.conductorCount, matrix.PerLengthImpedance.isTemplate) == (2, True)
    assert float(segments["ln_overhead_line:3"].length.to("m")) == pytest.approx(21.0)
    # the child node n3 lands on its root n2 (GLM-4)
    terminals = {t.sequenceNumber: str(t.ConnectivityNode.mRID) for t in segments["ln_line_u1"].Terminals}
    assert terminals == {1: "n2", 2: "n6"}

    def limits(equipment) -> list[float]:
        return sorted(float(v.normalValue.to("A")) for s in equipment.OperationalLimitSet
                      for v in s.OperationalLimitValue)

    assert limits(segments["ln_line_l2"]) == [230.0, 600.0]
    assert limits(segments["ln_tl_2"]) == [1200.0, 1200.0]  # from its configuration (S3a-4)
    assert limits(segments["ln_l1"]) == []  # conductor ratings stay on the WireInfo

    devices = {str(d.mRID): d for cls in (cim.LoadBreakSwitch, cim.Fuse, cim.Recloser)
               for d in network.list_by_class(cls)}
    assert {name: type(d).__name__ for name, d in devices.items()} == {
        "sw_swt_s1": "LoadBreakSwitch", "sw_swt_s2": "LoadBreakSwitch", "sw_fuse_1": "Fuse", "sw_fuse_2": "Fuse",
        "sw_recloser_1": "Recloser"}
    assert devices["sw_swt_s2"].open and devices["sw_swt_s2"].normalOpen
    assert not devices["sw_swt_s1"].open and limits(devices["sw_swt_s1"]) == [400.0, 600.0]
    assert float(devices["sw_fuse_1"].ratedCurrent.to("A")) == 50000.0 and devices["sw_fuse_2"].ratedCurrent is None
    assert [p.phaseSide1.value for p in devices["sw_recloser_1"].SwitchPhase] == ["C"]  # N dropped (S3a-7)


# -- fail fast -------------------------------------------------------------------------------------------------------

def raises(tmp_path, text: str, match: str):
    """The atom plus ``text`` must raise ``match``."""
    path = tmp_path / "model.glm"
    path.write_text(f'#include "{ATOM / "line.glm"}"\nobject node {{ name nx; phases ABCN; nominal_voltage 2401.78; }}\n'
                    + text)
    with pytest.raises(ValueError, match=match):
        GlmImporter("m").to_cimtbl(read(path))


def test_phases_other_than_the_conductors_raise(tmp_path):
    raises(tmp_path, "object overhead_line { name x; phases AN; from n1; to nx; length 10; configuration lcon_601; }",
           r"overhead_line x: phases AN are not the phases ABCN of configuration lcon_601 \(S3a-3\)")


def bind(tmp_path, text: str):
    """The atom plus ``text``, bound."""
    path = tmp_path / "model.glm"
    path.write_text(f'#include "{ATOM / "line.glm"}"\nobject node {{ name nx; phases ABCN; nominal_voltage 2401.78; }}\n'
                    + text)
    return glm_to_cim(read(path), name="m")


def segment(network, mrid: str):
    return next(s for s in network.list_by_class(cim.ACLineSegment) if str(s.mRID) == mrid)


def test_matrix_line_drops_its_neutral(tmp_path, scope):
    """GridLAB-D's matrix is the Kron-reduced A, B, C one: a matrix line never reads N (line.cpp:226), S6."""
    network = bind(tmp_path, "object overhead_line { name x; phases ACN; from n1; to nx; length 10; "
                             "configuration lcon_mtx604_AC; }")
    assert segment_phases(segment(network, "ln_x")) == {1: "A", 2: "C"}


ZERO_DIAGONAL = ("object line_configuration { name zc; z11 0+0j; z12 0+0j; z13 0+0j; z21 0+0j; z22 0+0j; "
                 "z23 0+0j; z31 0+0j; z32 0+0j; z33 0.3+0.6j; }\n")


def test_a_written_zero_diagonal_is_no_phase(tmp_path, scope):
    """A written 0 is GridLAB-D's default: the Milsoft exports write all nine terms (S6)."""
    network = bind(tmp_path, ZERO_DIAGONAL + "object overhead_line { name x; phases CN; from n1; to nx; length 10; "
                                             "configuration zc; }")
    line = segment(network, "ln_x")
    assert segment_phases(line) == {1: "C"}
    assert line.WireConfiguration.PerLengthImpedance.conductorCount == 1


def test_a_mutual_term_on_a_zero_diagonal_raises(tmp_path):
    raises(tmp_path, ZERO_DIAGONAL.replace("z13 0+0j; ", "z13 0.1+0.1j; ").replace("z31 0+0j; ", "z31 0.1+0.1j; ")
           + "object overhead_line { name x; phases CN; from n1; to nx; length 10; configuration zc; }",
           "z13 is set without z11 and z33")


def test_overhead_line_on_underground_conductors_raises(tmp_path):
    raises(tmp_path, "object overhead_line { name x; phases AN; from n1; to nx; length 10; configuration lcon_607; }",
           "has conductor_A tscab_ts_1/0 \\(underground_line_conductor\\).*needs overhead_line_conductors")


def test_mixed_phase_cables_raise(tmp_path):
    raises(tmp_path, """
object line_spacing { name sx; distance_AB 6.0 in; distance_AN 6.0 in; distance_BN 6.0 in; }
object line_configuration { name cx; spacing sx; conductor_A cncab_cn_250; conductor_B "tscab_ts_1/0";
  conductor_N "ugwire_cu_1/0"; }
object underground_line { name x; phases ABN; from n1; to nx; length 10; configuration cx; }
""", "mixes phase cables")


def test_line_without_length_raises(tmp_path):
    raises(tmp_path, "object overhead_line { name x; phases ABCN; from n1; to nx; configuration lcon_601; }",
           "overhead_line x: length unset")


def test_triplex_configuration_on_an_overhead_line_raises(tmp_path):
    raises(tmp_path, "object overhead_line { name x; phases ABCN; from n1; to nx; length 10; configuration tc_rated; }",
           "configuration tc_rated is a triplex_line_configuration, not a line_configuration")


def test_per_phase_ratings_that_differ_raise(tmp_path):
    raises(tmp_path, "object overhead_line { name x; phases ABCN; from n1; to nx; length 10; configuration lcon_601; "
                     "continuous_rating_A 400; continuous_rating_B 300; }",
           "continuous_rating_A=400.0, continuous_rating_B=300.0; one rating per link")


def test_line_rating_other_than_its_configurations_raises(tmp_path):
    raises(tmp_path, "object triplex_meter { name tmx; phases AS; nominal_voltage 120; }\n"
                     "object triplex_line { name x; phases AS; from tn1; to tmx; length 30; configuration tc_rated; "
                     "continuous_rating_A 900; }", "differ from its configuration tc_rated's")


def test_triplex_line_on_two_phases_raises(tmp_path):
    raises(tmp_path, "object triplex_meter { name tmx; phases AS; nominal_voltage 120; }\n"
                     "object triplex_line { name x; phases ABS; from tn1; to tmx; length 30; "
                     "configuration tc_rated; }", "phases ABS are not all on its from")


def test_open_tie_across_phases_takes_two_sides(tmp_path, scope):
    """CIM's SwitchPhase.phaseSide1/phaseSide2 hold a tie GridLAB-D cannot load (link.cpp:649), S6-9."""
    network = bind(tmp_path, "object switch { name x; phases AN; from n5; to n8; status OPEN; }")
    tie = next(sw for sw in network.list_by_class(cim.LoadBreakSwitch) if str(sw.mRID) == "sw_x")
    assert [(p.phaseSide1.value, p.phaseSide2.value) for p in tie.SwitchPhase] == [("A", "C")]
    assert sorted(t.phases.value for t in tie.Terminals) == ["A", "C"]


def test_closed_tie_across_phases_raises(tmp_path):
    raises(tmp_path, "object switch { name x; phases AN; from n5; to n8; status CLOSED; }",
           r"phases AN are not all on its to node n8 \(CN\)")


def test_phase_state_other_than_status_raises(tmp_path):
    raises(tmp_path, "object recloser { name x; phases ABCN; from n1; to nx; status CLOSED; phase_B_state OPEN; }",
           r"recloser x: phase_B_state OPEN but status CLOSED; a per-phase state is not mapped \(S3a-6\)")


def test_blown_fuse_phase_raises(tmp_path):
    raises(tmp_path, "object fuse { name x; phases ABCN; from n1; to nx; status CLOSED; phase_C_status BLOWN; }",
           r"fuse x: phase_C_status BLOWN")


# -- the deck sweep's check (test_cimtbl_sweep.py) -----------------------------------------------------------------

def assert_lines_and_switches(model, network) -> None:
    """Every line and switching device is written, and each geometry line's phases are its spacing's positions
    (S3a)."""
    segments = network.list_by_class(cim.ACLineSegment)
    assert len(segments) == sum(model.count(cls) for cls, _, _ in line.LINES)
    for segment in segments:  # an all-zero spacing (S2-4) names no positions
        geometry = get_line_geometry(segment)
        if geometry is not None and geometry.WireSpacing.ConductorDistance:
            assert segment_phases(segment) == spacing_phases(segment), segment.mRID
    assert len(network.list_by_class(cim.LoadBreakSwitch)) == model.count(schema.Switch)
    assert len(network.list_by_class(cim.Fuse)) == model.count(schema.Fuse)
    assert len(network.list_by_class(cim.Recloser)) == model.count(schema.Recloser)
    switches = {str(sw.mRID): sw for cls in (cim.LoadBreakSwitch, cim.Fuse, cim.Recloser)
                for sw in network.list_by_class(cls)}
    for native_class, _, _ in switch.SWITCHES:  # each side's phases on its GLM end (an open tie across phases, S6-9)
        for device in model.list_by_class(native_class):
            sides = [(p.phaseSide1.value, p.phaseSide2.value) for p in switches[f"sw_{device.name}"].SwitchPhase]
            for index, slot in enumerate(("from_node", "to")):
                end = set(str(model.by_name(getattr(device, slot)).phases))
                assert {pair[index] for pair in sides} <= end, (device.name, slot, sides)

"""cimhub_core.getters.spacing: conductor positions and distances of XYSpacing and ConductorDistanceSpacing, and a
line's conductor heights (spacingYOffset)."""

import math
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.derived.spacing import positions_from_distances
from cimhub_core.getters.spacing import get_line_conductor_xy, get_spacing_distances, get_spacing_xy

PHASE, NEUTRAL = cim.ConductorPositionKind.phase, cim.ConductorPositionKind.neutral
SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"

# IEEE 13 spacing 500 (ft): phases at x 0, 2.5, 7 and 28 ft up, the neutral at x 4, 24 ft up
SPACING_500_XY = ((0.0, 28.0), (2.5, 28.0), (7.0, 28.0), (4.0, 24.0))
# the same spacing as GridLAB-D writes it: distance_AB ... distance_CN, 6 digits
SPACING_500_DISTANCES = {(1, 2): 2.5, (1, 3): 7.0, (2, 3): 4.5, (1, 4): 5.656854, (2, 4): 4.272002, (3, 4): 5.0}


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _get(network, cls, mrid):
    return next(obj for obj in network.graph[cls].values() if obj.mRID == mrid)


def _spacing_500():
    network = load_model(SHAPES / "line_by_wire_configuration.cimtbl")
    return _get(network, cim.XYSpacing, "spc_500")


def _atom(tmp_path, body):
    path = tmp_path / "atom.cimtbl"
    path.write_text("Profile = cim18v17\n" + body)
    return load_model(path)


def _distance_atom(tmp_path, rows, line=""):
    """A ConductorDistanceSpacing ``cds`` from ``(mRID, sequenceNumber1, kind1, sequenceNumber2, kind2, ft)``."""
    lines = "\n".join("    " + ", ".join(str(value) for value in row) for row in rows)
    network = _atom(tmp_path, f"""Object ConductorDistanceSpacing: mRID=cds, name=cds, isTemplate=true
Table ConductorDistance: mRID, ConductorDistanceSpacing=cds, sequenceNumber1, conductorKind1, sequenceNumber2, conductorKind2, distance (ft)
{lines}
{line}""")
    return _get(network, cim.ConductorDistanceSpacing, "cds")


# spacing 500 on a crossarm: the origin at the crossarm, the pole height on the line
CROSSARM = """Object XYSpacing: mRID=spc_arm, name=arm, isTemplate=true
Table XYConductorPosition: mRID, XYSpacing=spc_arm, sequenceNumber, xCoord (ft), yCoord (ft), kind
    spc_arm_1, 1, 0,   0,  phase
    spc_arm_2, 2, 2.5, 0,  phase
    spc_arm_3, 3, 7,   0,  phase
    spc_arm_4, 4, 4,   -4, neutral
"""


def _flat(positions):
    return _flat_xy((position.x, position.y) for position in positions)


def _flat_xy(pairs):
    return [value for pair in pairs for value in pair]


def _spacing_500_rows(distances=SPACING_500_DISTANCES):
    kinds = {1: "phase", 2: "phase", 3: "phase", 4: "neutral"}
    heights = [(f"h{number}", number, kinds[number], "", "earth", y)
               for number, (_, y) in enumerate(SPACING_500_XY, start=1)]
    pairs = [(f"d{first}{second}", first, kinds[first], second, kinds[second], distance)
             for (first, second), distance in distances.items()]
    return heights + pairs


# XYSpacing -------------------------------------------------------------------------------------------------------


def test_xy_positions_as_stored():
    positions = get_spacing_xy(_spacing_500(), "ft")
    assert [position.sequence_number for position in positions] == [1, 2, 3, 4]
    assert [position.kind for position in positions] == [PHASE, PHASE, PHASE, NEUTRAL]
    assert _flat(positions) == pytest.approx(_flat_xy(SPACING_500_XY))


def test_xy_in_metres():
    assert get_spacing_xy(_spacing_500())[0].y == pytest.approx(28 * 0.3048)


def test_xy_distances():
    distances = get_spacing_distances(_spacing_500(), "ft")
    assert distances == pytest.approx(SPACING_500_DISTANCES, rel=1e-6)
    assert list(distances) == [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]


def test_unset_coordinate_raises():
    spacing = _spacing_500()
    spacing.XYConductorPosition[3].yCoord = None
    with pytest.raises(ValueError, match="XYConductorPosition 'spc_500_4' of XYSpacing 'spc_500': xCoord and "
                                         "yCoord must be set"):
        get_spacing_xy(spacing)


def test_duplicate_sequence_number_raises():
    spacing = _spacing_500()
    spacing.XYConductorPosition[3].sequenceNumber = 1
    with pytest.raises(ValueError, match="two positions have sequenceNumber 1"):
        get_spacing_distances(spacing)


def test_empty_spacing_raises():
    with pytest.raises(ValueError, match="XYSpacing 'spc_x': has no XYConductorPosition"):
        get_spacing_xy(cim.XYSpacing(mRID="spc_x"))


def test_equivalent_distance_spacing_raises():
    with pytest.raises(ValueError, match="EquivalentDistanceSpacing 'eds': has no conductor positions"):
        get_spacing_xy(cim.EquivalentDistanceSpacing(mRID="eds"))


# ConductorDistanceSpacing ----------------------------------------------------------------------------------------


def test_distances_give_the_xy_positions(tmp_path):
    positions = get_spacing_xy(_distance_atom(tmp_path, _spacing_500_rows()), "ft")
    assert [position.kind for position in positions] == [PHASE, PHASE, PHASE, NEUTRAL]
    assert _flat(positions) == pytest.approx(_flat_xy(SPACING_500_XY), abs=1e-5)


def test_stored_distances(tmp_path):
    distances = get_spacing_distances(_distance_atom(tmp_path, _spacing_500_rows()), "ft")
    assert distances == pytest.approx(SPACING_500_DISTANCES)


def test_a_missing_pair_raises_for_distances_but_not_positions(tmp_path):
    rows = _spacing_500_rows({pair: d for pair, d in SPACING_500_DISTANCES.items() if pair != (1, 3)})
    spacing = _distance_atom(tmp_path, rows)
    assert get_spacing_xy(spacing, "ft")[2].x == pytest.approx(7.0, abs=1e-5)
    with pytest.raises(ValueError, match=r"has no distance between conductors \[\(1, 3\)\]"):
        get_spacing_distances(spacing)


def test_missing_height_raises(tmp_path):
    rows = [row for row in _spacing_500_rows() if row[0] != "h4"]
    with pytest.raises(ValueError, match=r"conductors \[4\] have no height"):
        get_spacing_xy(_distance_atom(tmp_path, rows))


def test_inconsistent_distances_raise(tmp_path):
    rows = _spacing_500_rows({**SPACING_500_DISTANCES, (1, 3): 6.0})
    with pytest.raises(ValueError, match="ConductorDistanceSpacing 'cds': conductors 1-3: distance"):
        get_spacing_xy(_distance_atom(tmp_path, rows), "ft")


def test_phase_keyed_rows_raise(tmp_path):
    rows = [("d12", "", "phase", 2, "phase", 2.5)]
    with pytest.raises(ValueError, match="a conductor end has no sequence number"):
        get_spacing_xy(_distance_atom(tmp_path, rows))


# get_line_conductor_xy -------------------------------------------------------------------------------------------


def test_line_without_offset_has_its_spacing_at_ground():
    network = load_model(SHAPES / "line_by_wire_configuration.cimtbl")
    positions = get_line_conductor_xy(_get(network, cim.ACLineSegment, "ln_g1"), "ft")
    assert _flat(positions) == pytest.approx(_flat_xy(SPACING_500_XY))


def test_offset_lifts_a_crossarm_to_the_pole_height(tmp_path):
    network = _atom(tmp_path, CROSSARM + "Object ACLineSegment: mRID=ln_x, name=x, WireSpacing=spc_arm, "
                                         "spacingYOffset (ft)=28\n")
    line = _get(network, cim.ACLineSegment, "ln_x")
    assert _flat(get_line_conductor_xy(line, "ft")) == pytest.approx(_flat_xy(SPACING_500_XY))
    # the spacing itself stays in its own frame, and its distances do not depend on the offset
    assert get_spacing_xy(line.WireSpacing, "ft")[3].y == pytest.approx(-4.0)
    assert get_spacing_distances(line.WireSpacing, "ft") == pytest.approx(SPACING_500_DISTANCES, rel=1e-6)


def test_offset_through_a_wire_configuration(tmp_path):
    network = _atom(tmp_path, CROSSARM + """Object WireConfiguration: mRID=wc_x, name=x, WireSpacing=spc_arm
Object ACLineSegment: mRID=ln_x, name=x, WireConfiguration=wc_x, spacingYOffset (ft)=30
""")
    assert get_line_conductor_xy(_get(network, cim.ACLineSegment, "ln_x"), "ft")[3].y == pytest.approx(26.0)


def test_two_different_spacings_raise(tmp_path):
    network = load_model(SHAPES / "line_by_wire_configuration.cimtbl")
    line = _get(network, cim.ACLineSegment, "ln_g1")
    line.WireSpacing = cim.XYSpacing(mRID="spc_other")
    with pytest.raises(ValueError, match="its WireSpacing XYSpacing 'spc_other' is not its WireConfiguration's "
                                         "XYSpacing 'spc_500'"):
        get_line_conductor_xy(line)


def test_line_without_spacing_raises():
    with pytest.raises(ValueError, match="ACLineSegment 'ln_x': has no WireSpacing"):
        get_line_conductor_xy(cim.ACLineSegment(mRID="ln_x"))


def test_distance_spacing_line_has_its_heights(tmp_path):
    spacing = _distance_atom(tmp_path, _spacing_500_rows(), "Object ACLineSegment: mRID=ln_x, name=x, "
                                                            "WireSpacing=cds\n")
    positions = get_line_conductor_xy(spacing.ACLineSegment[0], "ft")
    assert [position.y for position in positions] == pytest.approx([28.0, 28.0, 28.0, 24.0])


def test_offset_on_a_distance_spacing_line_raises(tmp_path):
    spacing = _distance_atom(tmp_path, _spacing_500_rows(), "Object ACLineSegment: mRID=ln_x, name=x, "
                                                            "WireSpacing=cds, spacingYOffset (ft)=28\n")
    with pytest.raises(ValueError, match="has a spacingYOffset, but its ConductorDistanceSpacing 'cds' holds "
                                         "heights above ground"):
        get_line_conductor_xy(spacing.ACLineSegment[0])


# derived.spacing -------------------------------------------------------------------------------------------------


def test_second_conductor_goes_right_and_mirrors_stay_right():
    # a vertical stack (1 over 2) leaves 3's side open: it goes right
    positions = positions_from_distances({1: 10.0, 2: 8.0, 3: 9.0}, {(1, 2): 2.0, (1, 3): math.hypot(1, 1),
                                                                     (2, 3): math.hypot(1, 1)}, rel_tol=1e-9)
    assert _flat_xy(positions.values()) == pytest.approx([0.0, 10.0, 0.0, 8.0, 1.0, 9.0])


def test_left_of_the_first_conductor():
    # 2 is right of 1; 3 is 1 m left of 1, which only its distance to 2 decides
    positions = positions_from_distances({1: 10.0, 2: 10.0, 3: 10.0}, {(1, 2): 1.0, (1, 3): 1.0, (2, 3): 2.0},
                                         rel_tol=1e-9)
    assert positions[3] == pytest.approx((-1.0, 10.0))


def test_distance_shorter_than_the_rise_raises():
    with pytest.raises(ValueError, match="conductors 1-2: distance 1.0 is shorter than their height difference 2.0"):
        positions_from_distances({1: 10.0, 2: 8.0}, {(1, 2): 1.0}, rel_tol=1e-9)


def test_unplaceable_conductor_raises():
    with pytest.raises(ValueError, match=r"conductor 3: no distance to a conductor placed before it \[1, 2\]"):
        positions_from_distances({1: 10.0, 2: 10.0, 3: 10.0}, {(1, 2): 1.0}, rel_tol=1e-9)

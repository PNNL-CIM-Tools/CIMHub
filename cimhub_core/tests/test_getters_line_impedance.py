"""cimhub_core.getters.line_impedance: the sequence and phase-matrix getters on the line shapes and inline atoms.

Expected values are hand-computed from the shape text, not from the getter.
"""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import BusBranchModel, load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.derived.sequence import phase_matrix
from cimhub_core.getters.line_impedance import (
    ImpedanceSource,
    MatrixSource,
    get_line_phase_impedance_matrix,
    get_line_sequence_impedance,
    get_line_sequence_impedance_per_length,
)

A, B, C, N = cim.SinglePhaseKind.A, cim.SinglePhaseKind.B, cim.SinglePhaseKind.C, cim.SinglePhaseKind.N

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"
FEET_PER_MILE = 5280

HEADER = """Profile = cim18v17
Object Feeder: mRID=fdr, name=fdr
Object BaseVoltage: mRID=bv_4p16kv, nominalVoltage (kV)=4.16
"""


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _line(network, mrid):
    return next(line for line in network.graph[cim.ACLineSegment].values() if line.mRID == mrid)


def _load_atom(tmp_path, body):
    path = tmp_path / "atom.cimtbl"
    path.write_text(HEADER + body)
    return load_model(path)


@pytest.fixture
def bus_branch():
    return load_model(SHAPES / "line_bus_branch.cimtbl", model_cls=BusBranchModel)


@pytest.fixture
def by_impedance():
    return load_model(SHAPES / "line_by_impedance.cimtbl")


# step 1: lumped ------------------------------------------------------------------------------------------------


def test_lumped_pu_returns_the_pu_it_was_written_in(bus_branch):
    z = get_line_sequence_impedance(_line(bus_branch, "ln_1_2_1"), "pu", base_power=bus_branch.base_power)
    assert (z.r, z.x, z.b) == pytest.approx((0.0194, 0.0592, 0.0528))
    assert (z.g, z.r0, z.x0, z.b0, z.g0) == (None,) * 5
    assert z.source is ImpedanceSource.LUMPED


def test_lumped_ohm_is_on_the_base_voltage_and_system_base(bus_branch):
    z_base = 115e3**2 / 100e6  # 132.25 ohm
    z = get_line_sequence_impedance(_line(bus_branch, "ln_1_2_1"))
    assert (z.r, z.x, z.b) == pytest.approx((0.0194 * z_base, 0.0592 * z_base, 0.0528 / z_base))


def test_lumped_r_without_x_raises(tmp_path):
    network = _load_atom(tmp_path, "Object ACLineSegment: mRID=ln, node1=a, node2=b, phases=ABC, r (ohm)=1, "
                                   "BaseVoltage=bv_4p16kv, EquipmentContainer=fdr\n")
    with pytest.raises(ValueError, match="r and x must be set together"):
        get_line_sequence_impedance(_line(network, "ln"))


# step 2: sequence code -----------------------------------------------------------------------------------------


def test_sequence_code_times_length(by_impedance):
    km = 500 * 0.3048 / 1000
    z = get_line_sequence_impedance(_line(by_impedance, "ln_l2"), derive=ImpedanceSource.PER_LENGTH_SEQ)
    assert (z.r, z.x, z.r0, z.x0) == pytest.approx((0.3489 * km, 0.426198 * km, 0.588811 * km, 1.29612 * km))
    assert (z.b, z.b0) == pytest.approx((3932.35e-9 * km, 1690.81e-9 * km))
    assert (z.g, z.g0) == (None, None)
    assert z.source is ImpedanceSource.PER_LENGTH_SEQ


def test_sequence_code_in_pu(by_impedance):
    km, z_base = 500 * 0.3048 / 1000, 4160**2 / 100e6
    z = get_line_sequence_impedance(_line(by_impedance, "ln_l2"), "pu", base_power=by_impedance.base_power,
                                    derive=ImpedanceSource.PER_LENGTH_SEQ)
    assert (z.r, z.b) == pytest.approx((0.3489 * km / z_base, 3932.35e-9 * km * z_base))


def test_default_derive_reads_lumped_only(by_impedance):
    with pytest.raises(ValueError, match="within derive=LUMPED .*PerLengthSequenceImpedance"):
        get_line_sequence_impedance(_line(by_impedance, "ln_l2"))


# step 3: phase matrix reduced ----------------------------------------------------------------------------------


def test_two_phase_matrix_reduces_to_sequence(by_impedance):
    miles = 300 / FEET_PER_MILE
    z = get_line_sequence_impedance(_line(by_impedance, "ln_l1"), derive=ImpedanceSource.MATRIX_REDUCED)
    # mtx604: Zs = mean diagonal, Zm = the one mutual; positive Zs - Zm, zero Zs + 2 Zm
    assert (z.r, z.r0) == pytest.approx(((1.3266 - 0.2066) * miles, (1.3266 + 2 * 0.2066) * miles))
    assert (z.x, z.x0) == pytest.approx(((1.352 - 0.4591) * miles, (1.352 + 2 * 0.4591) * miles))
    assert (z.b, z.b0) == pytest.approx(((4628.095 + 899.07) * 1e-9 * miles, (4628.095 - 2 * 899.07) * 1e-9 * miles))
    assert z.source is ImpedanceSource.MATRIX_REDUCED


def test_matrix_needs_derive_matrix_reduced(by_impedance):
    with pytest.raises(ValueError, match="within derive=PER_LENGTH_SEQ"):
        get_line_sequence_impedance(_line(by_impedance, "ln_l1"), derive=ImpedanceSource.PER_LENGTH_SEQ)


def _matrix_atom(tmp_path, phases, rows):
    data = "\n".join(f"    d_{row}{column}, {row}, {column}, {r}, {x}, {b}" for row, column, r, x, b in rows)
    return _load_atom(tmp_path, f"""
Object PerLengthPhaseImpedance: mRID=mtx, conductorCount={len(phases)}
Table PhaseImpedanceData: identifier, PhaseImpedance=mtx, row, column, r (ohm/mi), x (ohm/mi), b (uS/mi)
{data}
Object ACLineSegment: mRID=ln, node1=a, node2=b, phases={phases}, length (mi)=1, PerLengthImpedance=mtx, BaseVoltage=bv_4p16kv, EquipmentContainer=fdr
""")


def test_ieee13_config_601_positive_sequence(tmp_path):
    # Kersting's IEEE 13 configuration 601; its published Z1 is 0.1859 + j0.5968 ohm/mi
    network = _matrix_atom(tmp_path, "BAC", [
        (1, 1, 0.3465, 1.0179, 6.2998), (2, 1, 0.1560, 0.5017, -1.9958), (2, 2, 0.3375, 1.0478, 5.9597),
        (3, 1, 0.1580, 0.4236, -1.2595), (3, 2, 0.1535, 0.3849, -0.7417), (3, 3, 0.3414, 1.0348, 5.6386)])
    z = get_line_sequence_impedance(_line(network, "ln"), derive=ImpedanceSource.MATRIX_REDUCED)
    assert (z.r, z.x) == pytest.approx((0.1859, 0.5968), abs=1e-4)


def test_one_conductor_is_positive_sequence_only(tmp_path):
    network = _matrix_atom(tmp_path, "C", [(1, 1, 1.3292, 1.3475, 4.5193)])
    z = get_line_sequence_impedance(_line(network, "ln"), derive=ImpedanceSource.MATRIX_REDUCED)
    assert (z.r, z.x, z.b) == pytest.approx((1.3292, 1.3475, 4.5193e-6))
    assert (z.r0, z.x0, z.b0) == (None, None, None)


def test_reduction_inverts_derived_phase_matrix(tmp_path):
    r = phase_matrix(0.30, 0.90, 2)
    x = phase_matrix(0.60, 1.80, 2)
    network = _matrix_atom(tmp_path, "AB", [(row, column, r[row, column], x[row, column], 1.0)
                                             for row, column in sorted(r)])
    z = get_line_sequence_impedance(_line(network, "ln"), derive=ImpedanceSource.MATRIX_REDUCED)
    assert (z.r, z.r0, z.x, z.x0) == pytest.approx((0.30, 0.90, 0.60, 1.80))


def test_kersting_example_4_1_neutral_is_kron_reduced(tmp_path):
    # Kersting, Distribution System Modeling, Example 4.1: the 4-wire primitive matrix (ohm/mi). His published
    # sequence values are z1 = 0.3061 + j0.6270 and z0 = 0.7735 + j1.9373 ohm/mi.
    network = _matrix_atom(tmp_path, "ABCN", [
        (1, 1, 0.4013, 1.4133, 0), (2, 1, 0.0953, 0.8515, 0), (2, 2, 0.4013, 1.4133, 0),
        (3, 1, 0.0953, 0.7266, 0), (3, 2, 0.0953, 0.7802, 0), (3, 3, 0.4013, 1.4133, 0),
        (4, 1, 0.0953, 0.7524, 0), (4, 2, 0.0953, 0.7865, 0), (4, 3, 0.0953, 0.7674, 0), (4, 4, 0.6873, 1.5465, 0)])
    z = get_line_sequence_impedance(_line(network, "ln"), derive=ImpedanceSource.MATRIX_REDUCED)
    assert (z.r, z.x, z.r0, z.x0) == pytest.approx((0.3061, 0.6270, 0.7735, 1.9373), abs=2e-4)


def test_neutral_shunt_keeps_the_phase_block(tmp_path):
    # V_n = 0: the reduced C is the phase block of C, so the neutral's b entries drop out
    network = _matrix_atom(tmp_path, "ABN", [(1, 1, 1, 1, 6), (2, 1, 0.1, 0.1, -2), (2, 2, 1, 1, 6),
                                             (3, 1, 0.1, 0.1, -1), (3, 2, 0.1, 0.1, -1), (3, 3, 1, 1, 5)])
    z = get_line_sequence_impedance(_line(network, "ln"), derive=ImpedanceSource.MATRIX_REDUCED)
    assert (z.b, z.b0) == pytest.approx((8e-6, 2e-6))


def test_split_phase_conductors_raise(tmp_path):
    network = _matrix_atom(tmp_path, "s1s2", [(1, 1, 1, 1, 1), (2, 1, 0.1, 0.1, 0), (2, 2, 1, 1, 1)])
    with pytest.raises(ValueError, match=r"conductors \['s1', 's2'\] have no sequence values"):
        get_line_sequence_impedance(_line(network, "ln"), derive=ImpedanceSource.MATRIX_REDUCED)


def test_missing_matrix_entry_raises(tmp_path):
    network = _matrix_atom(tmp_path, "AB", [(1, 1, 1, 1, 1), (2, 2, 1, 1, 1)])
    with pytest.raises(ValueError, match="lower triangle"):
        get_line_sequence_impedance(_line(network, "ln"), derive=ImpedanceSource.MATRIX_REDUCED)


# precedence and conflicts --------------------------------------------------------------------------------------


def _lumped_and_code_atom(tmp_path, lumped_r):
    return _load_atom(tmp_path, f"""
Object PerLengthSequenceImpedance: mRID=seq, r (ohm/km)=0.5, x (ohm/km)=1.0
Object ACLineSegment: mRID=ln, node1=a, node2=b, phases=ABC, length (km)=2, r (ohm)={lumped_r}, x (ohm)=2.0, PerLengthImpedance=seq, BaseVoltage=bv_4p16kv, EquipmentContainer=fdr
""")


def test_lumped_wins_when_both_agree(tmp_path):
    line = _line(_lumped_and_code_atom(tmp_path, 1.0), "ln")
    z = get_line_sequence_impedance(line, derive=ImpedanceSource.PER_LENGTH_SEQ)
    assert (z.r, z.x, z.source) == (pytest.approx(1.0), pytest.approx(2.0), ImpedanceSource.LUMPED)


def test_disagreeing_sources_raise(tmp_path):
    line = _line(_lumped_and_code_atom(tmp_path, 1.5), "ln")
    assert get_line_sequence_impedance(line).r == pytest.approx(1.5)  # LUMPED never reads the code
    with pytest.raises(ValueError, match="lumped r=1.5 disagrees with PER_LENGTH_SEQ r=1.0"):
        get_line_sequence_impedance(line, derive=ImpedanceSource.PER_LENGTH_SEQ)


# step 4 and input checks ---------------------------------------------------------------------------------------


def test_geometry_is_not_built_yet():
    network = load_model(SHAPES / "line_by_wire_configuration.cimtbl")
    line = next(iter(network.graph[cim.ACLineSegment].values()))
    with pytest.raises(ValueError, match="WireConfiguration: set"):
        get_line_sequence_impedance(line, derive=ImpedanceSource.MATRIX_REDUCED)
    with pytest.raises(NotImplementedError, match="step 4"):
        get_line_sequence_impedance(line, derive=ImpedanceSource.GEOMETRY)


def test_unknown_unit_raises(bus_branch):
    with pytest.raises(ValueError, match="unit must be one of"):
        get_line_sequence_impedance(_line(bus_branch, "ln_1_2_1"), "ohm/mi")


# get_line_sequence_impedance_per_length ------------------------------------------------------------------------


def test_per_length_sequence_code_in_its_own_units(by_impedance):
    z = get_line_sequence_impedance_per_length(_line(by_impedance, "ln_l2"), "ohm/km", "nS/km")
    assert (z.r, z.x, z.r0, z.x0) == pytest.approx((0.3489, 0.426198, 0.588811, 1.29612))
    assert (z.b, z.b0, z.g, z.g0) == (pytest.approx(3932.35), pytest.approx(1690.81), None, None)
    assert z.source is ImpedanceSource.PER_LENGTH_SEQ


def test_per_length_times_length_is_the_whole_line(by_impedance):
    line = _line(by_impedance, "ln_l2")
    per_metre = get_line_sequence_impedance_per_length(line)
    whole = get_line_sequence_impedance(line, derive=ImpedanceSource.PER_LENGTH_SEQ)
    assert (whole.r, whole.b0) == pytest.approx((per_metre.r * 152.4, per_metre.b0 * 152.4))


def test_per_length_matrix_needs_derive_matrix_reduced(by_impedance):
    line = _line(by_impedance, "ln_l1")
    with pytest.raises(ValueError, match="within derive=PER_LENGTH_SEQ"):
        get_line_sequence_impedance_per_length(line, "ohm/mi", "nS/mi")
    z = get_line_sequence_impedance_per_length(line, "ohm/mi", "nS/mi", derive=ImpedanceSource.MATRIX_REDUCED)
    assert (z.r, z.x, z.r0) == pytest.approx((1.3266 - 0.2066, 1.352 - 0.4591, 1.3266 + 2 * 0.2066))
    assert z.b == pytest.approx(4628.095 + 899.07)


def test_per_length_has_no_lumped_step(by_impedance):
    with pytest.raises(ValueError, match="start at derive=PER_LENGTH_SEQ, not LUMPED"):
        get_line_sequence_impedance_per_length(_line(by_impedance, "ln_l2"), derive=ImpedanceSource.LUMPED)


def test_per_length_on_a_lumped_line_raises(bus_branch):
    with pytest.raises(ValueError, match="lumped r/x: set, PerLengthImpedance: none"):
        get_line_sequence_impedance_per_length(_line(bus_branch, "ln_1_2_1"))


# get_line_phase_impedance_matrix -------------------------------------------------------------------------------


def test_phase_code_as_stored_in_conductor_order(by_impedance):
    m = get_line_phase_impedance_matrix(_line(by_impedance, "ln_l1"), "ohm/mi", "nS/mi")
    assert m.phases == (C, B)
    assert m.r == pytest.approx({(1, 1): 1.3238, (2, 1): 0.2066, (2, 2): 1.3294})
    assert m.x == pytest.approx({(1, 1): 1.3569, (2, 1): 0.4591, (2, 2): 1.3471})
    assert m.b == pytest.approx({(1, 1): 4710.84, (2, 1): -899.07, (2, 2): 4545.35})
    assert m.g is None
    assert m.source is MatrixSource.PHASE_CODE


def test_phase_code_keeps_neutral_and_split_phase_conductors(tmp_path):
    rows = [(1, 1, 1.0, 2.0, 3.0), (2, 1, 0.1, 0.2, -0.3), (2, 2, 1.1, 2.1, 3.1)]
    m = get_line_phase_impedance_matrix(_line(_matrix_atom(tmp_path, "s1s2", rows), "ln"), "ohm/mi", "uS/mi")
    assert m.phases == (cim.SinglePhaseKind.s1, cim.SinglePhaseKind.s2)
    assert m.r == pytest.approx({(1, 1): 1.0, (2, 1): 0.1, (2, 2): 1.1})

    network = _matrix_atom(tmp_path, "AN", rows)
    assert get_line_phase_impedance_matrix(_line(network, "ln"), "ohm/mi", "uS/mi").phases == (A, N)


def test_sequence_code_expands_only_when_asked(by_impedance):
    line = _line(by_impedance, "ln_l2")
    with pytest.raises(ValueError, match="pass expand_sequence=True"):
        get_line_phase_impedance_matrix(line)
    m = get_line_phase_impedance_matrix(line, "ohm/km", "nS/km", expand_sequence=True)
    r_self, r_mutual = (2 * 0.3489 + 0.588811) / 3, (0.588811 - 0.3489) / 3
    b_self, b_mutual = (2 * 3932.35 + 1690.81) / 3, (1690.81 - 3932.35) / 3
    assert m.phases == (A, B, C)
    assert m.r == pytest.approx({(1, 1): r_self, (2, 1): r_mutual, (2, 2): r_self,
                                 (3, 1): r_mutual, (3, 2): r_mutual, (3, 3): r_self})
    assert m.b[3, 3] == pytest.approx(b_self) and m.b[2, 1] == pytest.approx(b_mutual)
    assert m.g is None
    assert m.source is MatrixSource.SEQUENCE_EXPANDED


def _sequence_atom(tmp_path, phases, zero_sequence):
    return _load_atom(tmp_path, f"""
Object PerLengthSequenceImpedance: mRID=seq, r (ohm/km)=0.3, x (ohm/km)=0.6{zero_sequence}
Object ACLineSegment: mRID=ln, node1=a, node2=b, phases={phases}, length (km)=1, PerLengthImpedance=seq, BaseVoltage=bv_4p16kv, EquipmentContainer=fdr
""")


def test_one_phase_expansion_is_the_positive_sequence(tmp_path):
    m = get_line_phase_impedance_matrix(_line(_sequence_atom(tmp_path, "B", ""), "ln"), "ohm/km",
                                        expand_sequence=True)
    assert (m.phases, m.r, m.x) == ((B,), {(1, 1): pytest.approx(0.3)}, {(1, 1): pytest.approx(0.6)})


def test_two_phase_expansion_needs_the_zero_sequence(tmp_path):
    with pytest.raises(ValueError, match="2 conductors need r0 to expand r"):
        get_line_phase_impedance_matrix(_line(_sequence_atom(tmp_path, "AC", ""), "ln"), expand_sequence=True)
    network = _sequence_atom(tmp_path, "AC", ", r0 (ohm/km)=0.9, x0 (ohm/km)=1.8")
    m = get_line_phase_impedance_matrix(_line(network, "ln"), "ohm/km", expand_sequence=True)
    assert m.r == pytest.approx(phase_matrix(0.3, 0.9, 2))


def test_matrix_of_a_geometry_line_raises():
    network = load_model(SHAPES / "line_by_wire_configuration.cimtbl")
    line = next(iter(network.graph[cim.ACLineSegment].values()))
    with pytest.raises(ValueError, match="export its geometry"):
        get_line_phase_impedance_matrix(line)


def test_matrix_of_a_lumped_line_raises(bus_branch):
    with pytest.raises(ValueError, match="has no PerLengthImpedance"):
        get_line_phase_impedance_matrix(_line(bus_branch, "ln_1_2_1"))

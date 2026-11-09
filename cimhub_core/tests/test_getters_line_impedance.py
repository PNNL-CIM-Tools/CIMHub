"""cimhub_core.getters.line_impedance: get_line_sequence_impedance on the line shapes and inline atoms.

Expected values are hand-computed from the shape text, not from the getter.
"""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import BusBranchModel, load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.derived.sequence import phase_matrix
from cimhub_core.getters.line_impedance import ImpedanceSource, get_line_sequence_impedance

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


def test_neutral_conductor_raises(tmp_path):
    network = _matrix_atom(tmp_path, "AN", [(1, 1, 1, 1, 1), (2, 1, 0.1, 0.1, 0), (2, 2, 1, 1, 1)])
    with pytest.raises(ValueError, match="Kron reduction"):
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

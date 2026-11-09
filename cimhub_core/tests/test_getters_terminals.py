"""cimhub_core.getters.terminals: terminal nodes and conductor phases on the core shapes."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import BusBranchModel, load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.terminals import get_conductor_phases, get_terminal_nodes, get_terminal_phases

A, B, C, N = cim.SinglePhaseKind.A, cim.SinglePhaseKind.B, cim.SinglePhaseKind.C, cim.SinglePhaseKind.N
S1, S2 = cim.SinglePhaseKind.s1, cim.SinglePhaseKind.s2

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _shape(name, **kwargs):
    return load_model(SHAPES / f"{name}.cimtbl", **kwargs)


def _get(network, cls, mrid):
    return next(obj for obj in network.graph[cls].values() if obj.mRID == mrid)


def _mrids(objects):
    return tuple(obj.mRID for obj in objects)


# get_terminal_nodes --------------------------------------------------------------------------------------------


def test_nodes_in_terminal_order():
    network = _shape("line_by_impedance")
    assert _mrids(get_terminal_nodes(_get(network, cim.ACLineSegment, "ln_l1"))) == ("n1", "n3")


def test_one_terminal_equipment_has_one_node():
    network = _shape("load")
    assert _mrids(get_terminal_nodes(_get(network, cim.EnergyConsumer, "ld_y1"))) == ("n1",)


def test_transformer_nodes_are_in_end_order():
    network = _shape("transformer_by_ends")
    assert _mrids(get_terminal_nodes(_get(network, cim.PowerTransformer, "xf_sub"))) == ("sourcebus", "n0")


def test_bus_branch_nodes_are_topological():
    network = _shape("line_bus_branch", model_cls=BusBranchModel)
    line = _get(network, cim.ACLineSegment, "ln_1_2_1")
    assert _mrids(get_terminal_nodes(line, topological=True)) == ("bus_1", "bus_2")
    with pytest.raises(ValueError, match="ln_1_2_1_T1' of ACLineSegment 'ln_1_2_1': has no ConnectivityNode"):
        get_terminal_nodes(line)


def test_equipment_without_terminals_raises():
    with pytest.raises(ValueError, match="ACLineSegment 'bare': has no Terminals"):
        get_terminal_nodes(cim.ACLineSegment(mRID="bare"))


# get_conductor_phases ------------------------------------------------------------------------------------------


def test_line_conductors_in_sequence_order():
    network = _shape("line_by_impedance")
    assert get_conductor_phases(_get(network, cim.ACLineSegment, "ln_l1")) == (C, B)
    assert get_conductor_phases(_get(network, cim.ACLineSegment, "ln_l2")) == (A, B, C)


def test_line_neutral_is_a_conductor():
    network = _shape("line_by_wire_configuration")
    assert get_conductor_phases(_get(network, cim.ACLineSegment, "ln_g1")) == (A, B, C, N)


def test_balanced_device_is_three_phase():
    network = _shape("switch")
    assert get_conductor_phases(_get(network, cim.Breaker, "sw_brkr")) == (A, B, C)
    assert get_conductor_phases(_get(network, cim.Fuse, "sw_f1")) == (C,)


def test_load_conductors():
    network = _shape("load")
    assert get_conductor_phases(_get(network, cim.EnergyConsumer, "ld_d1")) == (B, C)  # delta: one child, phase B
    assert get_conductor_phases(_get(network, cim.EnergyConsumer, "ld_s1")) == (S1, S2)
    assert get_conductor_phases(_get(network, cim.EnergyConsumer, "ld_s2")) == (S2,)


def test_transformer_ends_differ_so_read_each_terminal():
    network = _shape("transformer_by_ends")
    transformer = _get(network, cim.PowerTransformer, "xf_sub")
    with pytest.raises(ValueError, match=r"terminals have different phases \[\['A', 'B', 'C'\], \['A', 'B', 'C', 'N'\]\]"):
        get_conductor_phases(transformer)
    terminals = sorted(transformer.Terminals, key=lambda terminal: terminal.sequenceNumber)
    assert [get_terminal_phases(terminal) for terminal in terminals] == [(A, B, C), (A, B, C, N)]


def test_split_phase_code_reads_back_as_tokens():
    terminal = cim.Terminal(mRID="t", phases=cim.PhaseCode.s12N)
    assert get_terminal_phases(terminal) == (S1, S2, N)


def test_line_children_must_match_its_terminals():
    network = _shape("line_by_impedance")
    line = _get(network, cim.ACLineSegment, "ln_l1")
    for terminal in line.Terminals:
        terminal.phases = cim.PhaseCode.AC
    with pytest.raises(ValueError, match=r"ACLineSegmentPhases \['C', 'B'\] are not the conductors \['A', 'C'\]"):
        get_conductor_phases(line)


def test_unknown_phase_code_raises():
    with pytest.raises(ValueError, match="Terminal 't': phases 'XY' are not conductors"):
        get_terminal_phases(cim.Terminal(mRID="t", phases=cim.PhaseCode.XY))

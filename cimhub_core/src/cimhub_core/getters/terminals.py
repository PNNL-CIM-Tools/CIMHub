"""Where equipment connects: its terminals' nodes and its conductors' phases (skill `export-getters`).

Phases come from ``Terminal.phases``, the unordered PhaseCode of the conductors at a terminal. A blank one is CIM's
balanced three-phase default, ABC (cimtables writes no phases for a balanced device: CIMHub upstream request U10).
Only a line orders its conductors: ``ACLineSegmentPhase.sequenceNumber`` is the row and column order of its
impedance matrix. Spoke spellings (GLM ``BCN``, DSS ``.3.2``) are built from the tokens in the spoke.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.connectivity import parse_phases

from cimhub_core.getters import describe

BALANCED_THREE_PHASE = (cim.SinglePhaseKind.A, cim.SinglePhaseKind.B, cim.SinglePhaseKind.C)


def get_terminal_nodes(
    equipment: cim.ConductingEquipment, *, topological: bool = False
) -> tuple[cim.ConnectivityNode | cim.TopologicalNode, ...]:
    """Each terminal's ConnectivityNode, or its TopologicalNode with ``topological=True`` (a bus-branch model), in
    ``Terminal.sequenceNumber`` order. Raises when a terminal has no node of that kind."""
    node_field = "TopologicalNode" if topological else "ConnectivityNode"
    nodes = []
    for terminal in _terminals(equipment):
        node = getattr(terminal, node_field)
        if node is None:
            raise ValueError(f"{describe(terminal)} of {describe(equipment)}: has no {node_field}")
        nodes.append(node)
    return tuple(nodes)


def get_conductor_phases(equipment: cim.ConductingEquipment) -> tuple[cim.SinglePhaseKind, ...]:
    """The equipment's conductors: a line's in ``ACLineSegmentPhase.sequenceNumber`` order (e.g. (C, B)), any
    other's in PhaseCode order (A, B, C, s1, s2, N). Every terminal must have the same phases; a transformer's ends
    differ, so read each end's terminal with ``get_terminal_phases``. A line's ACLineSegmentPhases must be the
    conductors at its terminals."""
    terminals = _terminals(equipment)
    phase_sets = {get_terminal_phases(terminal) for terminal in terminals}
    if len(phase_sets) != 1:
        raise ValueError(f"{describe(equipment)}: its terminals have different phases "
                         f"{[_values(get_terminal_phases(terminal)) for terminal in terminals]}")
    [phases] = phase_sets
    if not isinstance(equipment, cim.ACLineSegment) or not equipment.ACLineSegmentPhases:
        return phases

    line_phases = tuple(child.phase for child in sorted(equipment.ACLineSegmentPhases,
                                                        key=lambda child: _sequence_number(child, equipment)))
    if len(line_phases) != len(phases) or set(line_phases) != set(phases):
        raise ValueError(f"{describe(equipment)}: ACLineSegmentPhases {_values(line_phases)} are not the "
                         f"conductors {_values(phases)} at its terminals")
    return line_phases


def get_switch_sides(switch: cim.Switch) -> tuple[tuple[cim.SinglePhaseKind, ...], tuple[cim.SinglePhaseKind, ...]]:
    """Side 1's and side 2's conductors, paired by position. A switch whose terminals agree has its conductors on
    both sides (``get_conductor_phases``). One between laterals on different phases (a tie, GLM S6-9) pairs them in
    its SwitchPhases, ``phaseSide1`` -> ``phaseSide2``, in side 1's PhaseCode order; the pairs must be exactly its
    two terminals' conductors."""
    terminals = _terminals(switch)
    sides = [get_terminal_phases(terminal) for terminal in terminals]
    if len(set(sides)) == 1:
        phases = get_conductor_phases(switch)
        return phases, phases
    pairs = [(child.phaseSide1, child.phaseSide2) for child in switch.SwitchPhase]
    across = dict(pairs)
    if (len(terminals) != 2 or len(across) != len(pairs) or set(across) != set(sides[0])
            or sorted(_values(tuple(across.values()))) != sorted(_values(sides[1]))):
        raise ValueError(f"{describe(switch)}: its terminals have different phases "
                         f"{[_values(side) for side in sides]} and its SwitchPhases (phaseSide1, phaseSide2) "
                         f"{[[_values((one,)), _values((two,))] for one, two in pairs]} do not pair them")
    return sides[0], tuple(across[phase] for phase in sides[0])


def get_terminal_phases(terminal: cim.Terminal) -> tuple[cim.SinglePhaseKind, ...]:
    """One terminal's conductors in PhaseCode order (A, B, C, s1, s2, N); a blank PhaseCode is ABC."""
    if terminal.phases is None:
        return BALANCED_THREE_PHASE
    return phase_code_tokens(terminal.phases, terminal)


def phase_code_tokens(code: cim.PhaseCode, owner) -> tuple[cim.SinglePhaseKind, ...]:
    """A PhaseCode's conductors in PhaseCode order; ``owner`` names the holder in the error."""
    written = code.value.replace("s12", "s1s2")  # the inverse of cimtables.connectivity.phase_code
    try:
        tokens = parse_phases(written)
    except ValueError as error:
        raise ValueError(f"{describe(owner)}: phases {code.value!r} are not conductors A, B, C, s1, s2, N") from error
    return tuple(cim.SinglePhaseKind(token) for token in tokens)


def _terminals(equipment: cim.ConductingEquipment) -> list[cim.Terminal]:
    if not equipment.Terminals:
        raise ValueError(f"{describe(equipment)}: has no Terminals")
    return sorted(equipment.Terminals, key=lambda terminal: _sequence_number(terminal, equipment))


def _sequence_number(item, equipment: cim.ConductingEquipment) -> int:
    if item.sequenceNumber is None:
        raise ValueError(f"{describe(item)} of {describe(equipment)}: has no sequenceNumber")
    return item.sequenceNumber


def _values(phases: tuple[cim.SinglePhaseKind, ...]) -> list[str]:
    return [phase.value for phase in phases]

"""DSS bus references, ``650.1.2.3`` (``EXPORT_MAPPING.md#bus-references``, decision E7)."""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

from cimhub_opendss.exporter.naming import Names

_NODE = {
    cim.SinglePhaseKind.A: 1, cim.SinglePhaseKind.B: 2, cim.SinglePhaseKind.C: 3,
    cim.SinglePhaseKind.s1: 1, cim.SinglePhaseKind.s2: 2,
}


def bus_ref(node, phases: tuple[cim.SinglePhaseKind, ...], names: Names) -> str:
    """``<bus>.<n>...``: the phase conductors in their order, A/B/C as 1/2/3 and s1/s2 as 1/2, never bare. A neutral
    raises until the windings bring its grounding rule (S6c)."""
    unknown = [phase for phase in phases if phase not in _NODE]
    if unknown or not phases:
        raise ValueError(f"bus {node.mRID!r}: phases {[phase.value for phase in phases]} have no DSS node yet "
                         "(a neutral comes with the windings, S6c)")
    return ".".join([names.bus(node), *(str(_NODE[phase]) for phase in phases)])

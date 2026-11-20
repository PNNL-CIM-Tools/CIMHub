"""DSS bus references, ``650.1.2.3`` (``EXPORT_MAPPING.md#bus-references``, decision E7).

A BusbarSection is its node's bus (``BUS_CLASSES``): DSS has no element for it, so it writes no record (H3).
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

from cimhub_opendss.exporter.naming import Names

#: conducting equipment that is only its node's bus in DSS, and writes no record (H3)
BUS_CLASSES = (cim.BusbarSection,)

_NODE = {
    cim.SinglePhaseKind.A: 1, cim.SinglePhaseKind.B: 2, cim.SinglePhaseKind.C: 3,
    cim.SinglePhaseKind.s1: 1, cim.SinglePhaseKind.s2: 2,
}


def bus_ref(node, phases: tuple[cim.SinglePhaseKind, ...], names: Names, *, neutral: int | None = None) -> str:
    """``<bus>.<n>...``: the conductors in their order, A/B/C as 1/2/3 and s1/s2 as 1/2, never bare. A neutral is
    written on node ``neutral``, which only a winding gives (its grounding rule, E7/T6); without one it raises."""
    nodes = {**_NODE, cim.SinglePhaseKind.N: neutral} if neutral is not None else _NODE
    unknown = [phase for phase in phases if phase not in nodes]
    if unknown or not phases:
        raise ValueError(f"bus {node.mRID!r}: phases {[phase.value for phase in phases]} have no DSS node here "
                         "(only a winding places a neutral)")
    return ".".join([names.bus(node), *(str(nodes[phase]) for phase in phases)])

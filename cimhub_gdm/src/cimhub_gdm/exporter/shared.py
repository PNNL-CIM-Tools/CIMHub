"""What the exporter modules share: the export context, phases and containers (``EXPORT_MAPPING.md``)."""

from __future__ import annotations

import json
from collections import Counter
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimhub_core.cimtbl import lookup
from cimhub_core.getters import describe
from cimhub_core.getters.in_service import get_in_service
from gdm.systems.distribution.enums import ConnectionType, Phase

from cimhub_gdm.exporter.naming import Names

#: CIM conductor → GDM phase; the inverse of the importer's ``shared.PHASE``.
PHASE = {
    cim.SinglePhaseKind.A: Phase.A, cim.SinglePhaseKind.B: Phase.B, cim.SinglePhaseKind.C: Phase.C,
    cim.SinglePhaseKind.N: Phase.N, cim.SinglePhaseKind.s1: Phase.S1, cim.SinglePhaseKind.s2: Phase.S2,
}

#: The order a bus lists its phases in (decision X6).
BUS_PHASE_ORDER = (Phase.A, Phase.B, Phase.C, Phase.S1, Phase.S2, Phase.N)


class ExportContext(NamedTuple):
    network: object
    names: Names
    made: dict  # CIM uri() -> the GDM component exported from it
    catalogs: dict  # (CIM catalog uri(), the equipment's values) -> the shared GDM equipment made for it (X3)
    filled: Counter  # 'GdmClass.field' -> how many times a fill was written (X4)

    def fill(self, field: str, value):
        """``value``, a neutral fill from ``fills.py`` for the required GDM ``field``, counted for the WARNING."""
        self.filled[field] += 1
        return value

    def gdm(self, obj):
        """The GDM component already exported from the CIM object ``obj``."""
        component = self.made.get(obj.uri())
        if component is None:
            raise ValueError(f"{describe(obj)}: not exported before the object that refers to it")
        return component


#: CIM shunt connection → GDM ConnectionType; the importer writes wye as Y (grounded), and Yn is a wye too.
CONNECTION = {
    cim.PhaseShuntConnectionKind.Y: ConnectionType.STAR, cim.PhaseShuntConnectionKind.Yn: ConnectionType.STAR,
    cim.PhaseShuntConnectionKind.D: ConnectionType.DELTA,
}


def connection_type(connection, owner) -> ConnectionType:
    """A load's or shunt's ``phaseConnection`` as a GDM ConnectionType; unset, I and G raise."""
    if connection is None:
        raise ValueError(f"{describe(owner)}: phaseConnection is unset")
    return lookup(CONNECTION, connection, slot="phaseConnection", record_id=owner.mRID)


def in_service(equipment) -> bool:
    """``get_in_service(which='actual')``: GDM's other states (a switch's is_closed) are actual states too; unset is
    in service, GDM's default."""
    value = get_in_service(equipment, which="actual")
    return True if value is None else value


def gdm_phases(phases: tuple[cim.SinglePhaseKind, ...], owner) -> list[Phase]:
    """CIM conductors as GDM phases, in the same order."""
    return [lookup(PHASE, phase, slot="phases", record_id=owner.mRID) for phase in phases]


def containers(container, context: ExportContext) -> dict:
    """``feeder`` and ``substation`` for a component in the CIM ``container``, as written: a Feeder gives the feeder,
    a Substation (or a VoltageLevel, standing for its Substation) the substation; CIM holds one container, so the
    other is None. Any other container class raises."""
    if container is None:
        return {"feeder": None, "substation": None}
    if isinstance(container, cim.Feeder):
        return {"feeder": context.gdm(container), "substation": None}
    if isinstance(container, cim.VoltageLevel):
        container = container.Substation
    if isinstance(container, cim.Substation):
        return {"feeder": None, "substation": context.gdm(container)}
    raise ValueError(f"{describe(container)}: no GDM feeder or substation for this container class")


def shared_equipment(context: ExportContext, catalog, equipment):
    """The shared GDM equipment of the CIM ``catalog`` with ``equipment``'s values (decision X3).

    GDM puts some instance values on its equipment (a line's ampacity, a transformer's taps), so one GDM equipment is
    made per (catalog, values): the first is named ``<catalog>``, each later one ``<catalog>_<n>``, in export order.
    ``equipment`` is built with any name; an equal one already made is returned instead.
    """
    key = (catalog.uri(), _values(equipment))
    if key not in context.catalogs:
        variant = 1 + sum(1 for catalog_uri, _ in context.catalogs if catalog_uri == catalog.uri())
        suffix = "" if variant == 1 else f"_{variant}"
        name = context.names.name(catalog, type(equipment), suffix=suffix)
        context.catalogs[key] = equipment.model_copy(update={"name": name})
    return context.catalogs[key]


def _values(equipment) -> str:
    """Every field of ``equipment`` but its name and the uuids, as comparable text."""
    def without_uuids(value):
        if isinstance(value, dict):
            return {key: without_uuids(item) for key, item in value.items() if key != "uuid"}
        if isinstance(value, list):
            return [without_uuids(item) for item in value]
        return value

    return json.dumps(without_uuids(equipment.model_dump(mode="json", exclude={"name"})), sort_keys=True)

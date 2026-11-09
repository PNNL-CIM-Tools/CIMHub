"""Rules shared by every GDM family: units, voltages, phases, containers and identity.

Every derived value here is a named function with a unit test (docs/GDM_MAPPING.md §5). Nothing here builds CIM
objects (I5); the family modules pass these values to CIM-Builder.
"""

from __future__ import annotations

import math

from cimhub_core.cimtbl import lookup, mrid
from cimprofiles.identity import as_uuid
from cimtables.units import Qty
from gdm.distribution.enums import Phase, VoltageTypes

#: CIM model authority for every GDM import (plan D7). The model name is the GDM system's name.
AUTHORITY = "https://github.com/PNNL-CIM-Tools/CIMHub"

#: GDM carries no frequency; its own conversions assume 60 Hz (OPEN_DECISIONS 4).
FREQUENCY_HZ = 60

#: GDM unit spellings the CIM unit registry does not define. Everything else goes to pint unchanged.
UNIT_SPELLINGS = {"kilova": "kVA", "va": "VA"}

FEEDER_PREFIX = "fdr_"
SUBSTATION_PREFIX = "sub_"
BASE_VOLTAGE_PREFIX = "bv_"

PHASE = {Phase.A: "A", Phase.B: "B", Phase.C: "C", Phase.N: "N", Phase.S1: "s1", Phase.S2: "s2"}
BALANCED_PHASES = {"A", "B", "C"}
SPLIT_PHASES = {Phase.S1, Phase.S2}


def qty(quantity) -> Qty:
    """A GDM (pint) quantity as a builder ``Qty``, in GDM's own unit (I2)."""
    unit = str(quantity.units)
    return Qty(float(quantity.magnitude), UNIT_SPELLINGS.get(unit, unit))


def round_significant(value: float, digits: int = 4) -> float:
    """``value`` rounded to ``digits`` significant figures."""
    if value == 0:
        return 0.0
    return round(value, digits - 1 - math.floor(math.log10(abs(value))))


def system_voltage(voltage, voltage_type, phases):
    """The system (line-to-line) voltage of a GDM rating, as a pint quantity in GDM's unit.

    ``line-to-line`` is taken as is. ``line-to-ground`` is doubled on a split-phase bus (120 V → 240 V) and
    multiplied by √3 otherwise (7.2 kV → 12.47 kV).
    """
    if VoltageTypes(voltage_type) is VoltageTypes.LINE_TO_LINE:
        return voltage
    if SPLIT_PHASES & {Phase(p) for p in phases}:
        return voltage * 2
    return voltage * math.sqrt(3)


def base_voltage_mrid(voltage) -> str:
    """``bv_4p16kv`` / ``bv_480v``: 4 significant figures, kV at and above 1 kV, else V (OPEN_DECISIONS 5).

    The conversion to kV only names the BaseVoltage; the value written is the rounded voltage in GDM's own unit.
    """
    kilovolts = round_significant(voltage.to("kV").magnitude)
    if kilovolts >= 1:
        text, unit = f"{kilovolts:g}", "kv"
    else:
        text, unit = f"{round_significant(kilovolts * 1000):g}", "v"
    return BASE_VOLTAGE_PREFIX + text.replace(".", "p") + unit


def phases_text(phases) -> str:
    """GDM phases as CIM phase text, in written order: ``[S1, S2, N]`` → ``s1s2N``."""
    return "".join(lookup(PHASE, Phase(p), slot="phases", record_id=phases) for p in phases)


def builder_phases(phases) -> str | None:
    """The ``phases`` a builder gets: ``None`` for balanced three-phase ABC (no per-phase children, user decision
    2026-11-08), else the phase text."""
    text = phases_text(phases)
    if len(text) == 3 and set(text) == BALANCED_PHASES:
        return None
    return text


def components(system, cls) -> list:
    """The system's objects of exactly ``cls``, sorted by name. infrasys ``get_components`` also returns subclasses,
    so ``PowerTransformerEquipment`` would otherwise be handled twice."""
    return sorted((c for c in system.get_components(cls) if type(c) is cls), key=lambda c: c.name)


def bus_base_voltage(bus) -> str:
    """The BaseVoltage mRID of a GDM bus."""
    return base_voltage_mrid(system_voltage(bus.rated_voltage, bus.voltage_type, bus.phases))


def bus_mrid(bus) -> str:
    """A bus's ConnectivityNode mRID: its name, bare (no prefix)."""
    return mrid("", bus.name)


def container_mrid(component, system_name: str) -> str:
    """The component's EquipmentContainer: its feeder, else its substation, else the system Feeder (OPEN_DECISIONS 1)."""
    if component.feeder is not None:
        return mrid(FEEDER_PREFIX, component.feeder.name)
    if component.substation is not None:
        return mrid(SUBSTATION_PREFIX, component.substation.name)
    return mrid(FEEDER_PREFIX, system_name)


def require_in_service(component) -> None:
    """CIM has no home for a modelled but out-of-service GDM component (GDM_MAPPING.md §10)."""
    if not component.in_service:
        raise ValueError(f"{type(component).__name__} {component.name!r}: in_service=False has no CIM home")


def check_names(components) -> None:
    """Raise unless every component has a non-empty, non-GUID name, unique within its class.

    An empty, GUID or clashing name needs CIM-Builder's ``rehash_mrid`` (B18; OPEN_DECISIONS 9, 10).
    """
    seen: dict[tuple[str, str], object] = {}
    for component in components:
        cls = type(component).__name__
        name = component.name
        if not name or not name.strip():
            raise ValueError(f"{cls} {component.uuid}: empty name; needs rehash_mrid (B18)")
        if as_uuid(name) is not None:
            raise ValueError(f"{cls} {name!r}: the name is a GUID; needs rehash_mrid (B18)")
        other = seen.setdefault((cls, name), component)
        if other is not component:
            raise ValueError(f"{cls} {name!r}: used by {other.uuid} and {component.uuid}; needs rehash_mrid (B18)")

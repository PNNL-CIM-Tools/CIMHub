"""Rules shared by every GDM family: units, voltages, phases, containers and identity.

Every derived value here is a named function with a unit test (docs/GDM_MAPPING.md §5). Nothing here builds CIM
objects (I5); the family modules pass these values to CIM-Builder.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cimbuilder.network import rehash_mrid
from cimhub_core.cimtbl import Field, lookup, mrid
from cimprofiles.identity import as_uuid
from cimtables.units import Qty
from gdm.distribution.enums import ConnectionType, Phase, VoltageTypes

#: CIM model authority for every GDM import (plan D7). The model name is the GDM system's name.
AUTHORITY = "https://github.com/PNNL-CIM-Tools/CIMHub"

#: GDM carries no frequency; its own conversions assume 60 Hz (OPEN_DECISIONS 4).
FREQUENCY_HZ = 60

#: GDM unit spellings the CIM unit registry does not define. Everything else goes to pint unchanged.
UNIT_SPELLINGS = {"kilova": "kVA", "va": "VA"}

FEEDER_PREFIX = "fdr_"
SUBSTATION_PREFIX = "sub_"
BASE_VOLTAGE_PREFIX = "bv_"

#: The ``uuid`` and ``name`` classification every named GDM class shares (OPEN_DECISIONS 9, 10).
UUID_FIELD = Field("structural", note="never copied; the rehashed mRID when the name is empty or clashes (B18)")


def name_field(prefix: str) -> Field:
    """``name`` → mRID (``prefix`` + name, or rehashed when it is a GUID) and name."""
    return Field("copied", (("create", "mRID", None), ("create", "name", None)),
                 note=f"mRID = {prefix or '(no prefix)'} + name; a GUID name is rehashed (B18)")


#: GDM ConnectionType → (phaseConnection, grounded), as the DSS wave writes loads and capacitors: wye is grounded.
#: OPEN_DELTA, OPEN_STAR and ZIG_ZAG have no PhaseShuntConnectionKind and raise.
SHUNT_CONNECTION = {ConnectionType.STAR: ("Y", True), ConnectionType.DELTA: ("D", False)}

PHASE = {Phase.A: "A", Phase.B: "B", Phase.C: "C", Phase.N: "N", Phase.S1: "s1", Phase.S2: "s2"}
BALANCED_PHASES = {"A", "B", "C"}
SPLIT_PHASES = {Phase.S1, Phase.S2}


#: The unit-name endings of each power quantity. W, VA and VAr convert into each other in the CIM unit registry, so
#: a power in the wrong quantity is caught only by its unit's name (GDM_MAPPING.md §4).
POWER_UNIT_ENDINGS = {"active": ("watt",), "reactive": ("var",), "apparent": ("va", "volt_ampere")}


def qty(quantity) -> Qty:
    """A GDM (pint) quantity as a builder ``Qty``, in GDM's own unit (I2)."""
    unit = str(quantity.units)
    return Qty(float(quantity.magnitude), UNIT_SPELLINGS.get(unit, unit))


def power_qty(quantity, kind: str, *, label: str) -> Qty:
    """``qty`` for a power, raising unless its unit names the ``kind`` of power (active, reactive, apparent)."""
    unit = str(quantity.units)
    if not unit.endswith(POWER_UNIT_ENDINGS[kind]):
        raise ValueError(f"{label}: {quantity} is not an {kind} power unit")
    return qty(quantity)


def active_power_unit(apparent: Qty) -> str:
    """The active power unit with an apparent power's prefix: kVA → kW, volt_ampere → watt."""
    return apparent.unit.replace("VA", "W").replace("volt_ampere", "watt")


def susceptance(capacitance, frequency: float = FREQUENCY_HZ) -> Qty:
    """b = 2πf·C, in GDM's capacitance unit times hertz (10 nF/km at 60 Hz → 3769.9 nF·Hz/km = 3.7699e-9 S/m)."""
    return Qty(2 * math.pi * frequency * float(capacitance.magnitude), f"hertz * {capacitance.units}")


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


def children_by_phase(parent_mrid: str, children, phases) -> list:
    """A builder's per-phase children (``<parent>_<phase>``) in the order of the GDM ``phases``."""
    by_mrid = {child.mRID: child for child in children}
    return [by_mrid[f"{parent_mrid}_{PHASE[Phase(phase)]}"] for phase in phases]


def components(system, cls) -> list:
    """The system's objects of exactly ``cls``, sorted by name. infrasys ``get_components`` also returns subclasses,
    so ``PowerTransformerEquipment`` would otherwise be handled twice."""
    return sorted((c for c in system.get_components(cls) if type(c) is cls), key=lambda c: c.name)


def bus_base_voltage(bus) -> str:
    """The BaseVoltage mRID of a GDM bus."""
    return base_voltage_mrid(system_voltage(bus.rated_voltage, bus.voltage_type, bus.phases))


@dataclass(frozen=True)
class Naming:
    """What an add function needs to name CIM objects besides its component: the system name (the container
    fallback) and the uuids of the components whose name cannot be their mRID (empty, or shared within the class)."""

    system_name: str
    clashing: frozenset = frozenset()


def name_clashes(components) -> frozenset:
    """The uuids of the components whose name is empty or used by another component of the same class."""
    by_name: dict[tuple[type, str], list] = {}
    for component in components:
        by_name.setdefault((type(component), component.name.strip()), []).append(component.uuid)
    return frozenset(uuid for (_, name), uuids in by_name.items() if not name or len(uuids) > 1 for uuid in uuids)


def object_mrid(prefix: str, component, cim_class: str, naming: Naming) -> str:
    """``prefix`` + the component's name (OPEN_DECISIONS 9), or a rehashed UUID (B18):
    of its uuid when its name is empty or clashes (OPEN_DECISIONS 10), of its name when the name is a GUID."""
    token = str(component.uuid) if component.uuid in naming.clashing else component.name
    if as_uuid(token) is not None:
        return rehash_mrid(cim_class, token)
    return mrid(prefix, token)


def bus_mrid(bus, naming: Naming) -> str:
    """A bus's ConnectivityNode mRID: its name, bare (no prefix)."""
    return object_mrid("", bus, "ConnectivityNode", naming)


def container_mrid(component, naming: Naming) -> str:
    """The component's EquipmentContainer: its feeder, else its substation, else the system Feeder (OPEN_DECISIONS 1).

    Feeder and substation names are plain text (``check_shell_name``), so they need no rehash.
    """
    if component.feeder is not None:
        return mrid(FEEDER_PREFIX, component.feeder.name)
    if component.substation is not None:
        return mrid(SUBSTATION_PREFIX, component.substation.name)
    return mrid(FEEDER_PREFIX, naming.system_name)


def require_in_service(component) -> None:
    """CIM has no home for a modelled but out-of-service GDM component (GDM_MAPPING.md §10)."""
    if not component.in_service:
        raise ValueError(f"{type(component).__name__} {component.name!r}: in_service=False has no CIM home")


def check_shell_name(component, naming: Naming) -> None:
    """Raise unless a Feeder or Substation name can be its mRID. Their mRIDs are fixed before ``new_feeder_model``
    sets the model scope that ``rehash_mrid`` seeds from, so an empty, GUID or clashing name has no mRID yet."""
    if component.uuid in naming.clashing or as_uuid(component.name) is not None:
        raise ValueError(f"{type(component).__name__} {component.name!r} ({component.uuid}): an empty, GUID or "
                         "clashing feeder or substation name is not supported")

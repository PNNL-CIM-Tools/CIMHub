"""EnergyConsumer -> OpenDSS ``Load`` (``EXPORT_MAPPING.md#load``).

p and q are written as kW and kvar. ``kV`` is the bus's (CIM gives a load no rating: p is at the BaseVoltage, S4-2),
so a deck's rounded kV (2.4 on a 4.16 kV bus) comes back as the bus's phase voltage. The voltage response is one
pure ZIP model (1, 2, 5) or the exponential model 4. Unequal per-phase values give one 1-phase Load per phase (E8).
A ConformLoad whose group's schedule is a LoadShape (``loadshape.py``) names it as ``yearly``; a ConformLoad whose
group has no schedule or no points, or days by season and day type (a GridLAB-D schedule's: DSS has no calendar),
and a NonConformLoad, are written static, their groups named in one warning (S8).
"""

from __future__ import annotations

import logging
import math

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.load import LoadResponse, get_load_response, get_phase_loads
from cimhub_core.getters.load_schedule import get_load_schedule
from cimhub_opendss.exporter import loadshape
from cimhub_opendss.exporter.injection import device_connection, device_kv, equal_phases
from cimhub_opendss.exporter.naming import Names
from cimhub_core.export_slots import Slot, with_default
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.EnergyConsumer, cim.ConformLoad, cim.NonConformLoad, cim.StationSupply)
NATIVE_CLASS = schema.Load
NAMESPACE = "Load"
#: DSS model -> the LoadResponse fractions (p, q) that are 1 in it
PURE_MODELS = {"ConstantPQ": ("p_power", "q_power"), "ConstantZ": ("p_impedance", "q_impedance"),
               "ConstantI": ("p_current", "q_current")}
EXPONENTIAL_MODEL = "CVR"

_SOLVER = "DSS solution control; untranscribed on import, the engine's default"
_NOT_IN_CIM = "untranscribed or raising on import; not in CIM"
SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "Names; one load per phase is <name>_<phase> (E8)"),
    "bus1": Slot("written", "bus_ref of the phase conductors; a wye's neutral is node 0, so it must be grounded"),
    "phases": Slot("written", "the phase conductors; a delta across two is 1"),
    "kV": Slot("written", "the BaseVoltage: LL for delta and 2-3 phases, LN for 1-phase wye; a split-phase leg half "
                          "the coil, a 2-phase wye leg pair x sqrt 3 (E9, DSS-5)"),
    "kW": Slot("written", "get_phase_loads total p (kW); per phase when the phases differ (E8)"),
    "kvar": Slot("written", "get_phase_loads total q (kVAr); per phase when the phases differ (E8)"),
    "pf": Slot("not mapped", "kvar carries q"),
    "kVA": Slot("not mapped", "kW and kvar carry the power"),
    "model": Slot("written", "get_load_response: a pure ZIP 1 (PQ), 2 (Z), 5 (I); exponential 4 (CVR); a mix raises"),
    "CVRwatts": Slot("written", "pVoltageExponent; model 4 only"),
    "CVRvars": Slot("written", "qVoltageExponent; model 4 only"),
    "ZIPV": Slot("not mapped", "model 8 raises, as on import"),
    "conn": Slot("written", "phaseConnection Y/Yn -> wye, D -> delta; others raise"),
    "NumCust": Slot("written", "customerCount; unset -> not written; per phase on the first load, 0 on the others"),
    "enabled": Slot("written", "get_in_service(which='normal'); unset -> not written"),
    "yearly": Slot("written", "a ConformLoad's group LoadShape (S8); unset otherwise"),
    **{slot: Slot("unset", _SOLVER) for slot in ("status", "Vminpu", "Vmaxpu", "Vminnorm", "Vminemerg", "Vlowpu")},
    "xfkVA": Slot("not mapped", "kW carries p"), "allocationfactor": Slot("not mapped", "kW carries p"),
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", _NOT_IN_CIM))}


_log = logging.getLogger(__name__)


def export(context) -> list[schema.Load]:
    """One Load per EnergyConsumer, or one per phase when its phases differ (E8)."""
    records, static = [], set()
    for consumer in context.objects(*CIM_CLASSES):
        records += _loads(consumer, context.names, _shape(context, consumer, static))
    if static:
        _log.warning("%d load group(s) are written static (no schedule, no points, days by season and day type, or a "
                     "NonConformLoad's): %s", len(static), sorted(static))
    return records


def _shape(context, consumer, static: set) -> str | None:
    """The LoadShape the consumer names as ``yearly``, or None; ``static`` collects the groups written static. A
    schedule with points is a shape (``loadshape.export`` reads and checks them)."""
    found = get_load_schedule(consumer)
    if found is None:
        return None
    if found.conform and found.schedule is not None and found.group.uri() in context.shapes.by_owner:
        return loadshape.shape_name(context, found.schedule)
    static.add(str(found.group.name or found.group.mRID))
    return None


def _loads(consumer: cim.EnergyConsumer, names: Names, yearly: str | None) -> list[schema.Load]:
    loads = get_phase_loads(consumer, "kW", "kVAr")
    common = dict(**_model(consumer, get_load_response(consumer)), enabled=get_in_service(consumer, which="normal"),
                  yearly=yearly)
    if loads.split or equal_phases(loads.per_phase):
        name = names.name(consumer, NAMESPACE)
        return [_load(consumer, loads, name, loads.phases, loads.total, consumer.customerCount, common, names)]
    if loads.connection is cim.PhaseShuntConnectionKind.D:
        raise ValueError(f"{describe(consumer)}: a delta load with unequal phases; a CIM phase on a delta load names "
                         f"no branch (E8)")
    records = []
    for number, (phase, power) in enumerate(loads.per_phase.items()):
        # the count stays the consumer's total: on the first phase's load, 0 on the others
        customers = consumer.customerCount if number == 0 or consumer.customerCount is None else 0
        name = names.name(consumer, NAMESPACE, suffix=f"_{phase.value.lower()}")
        records.append(_load(consumer, loads, name, (phase,), power, customers, common, names))
    return records


def _load(consumer, loads, name: str, conductors, power, customers: int | None, common: dict,
          names: Names) -> schema.Load:
    connection = device_connection(consumer, conductors, loads.connection, loads.grounded, names)
    return NATIVE_CLASS(name=name, bus1=connection.bus1, phases=connection.phases, conn=connection.conn,
                        kV=device_kv(consumer, conductors, connection.conn), kW=power.p, kvar=power.q,
                        NumCust=customers, **common)


def _model(consumer, response: LoadResponse) -> dict:
    """``model`` (and the CVR exponents): one pure ZIP, or the exponential model."""
    if response.exponential:
        return dict(model=EXPONENTIAL_MODEL, CVRwatts=response.p_exponent, CVRvars=response.q_exponent)
    for model, (p_fraction, q_fraction) in PURE_MODELS.items():
        if math.isclose(getattr(response, p_fraction), 1.0) and math.isclose(getattr(response, q_fraction), 1.0):
            return dict(model=model)
    fractions = {name: getattr(response, name) for names in PURE_MODELS.values() for name in names}
    raise ValueError(f"{describe(consumer)}: ZIP fractions {fractions} are no one DSS model (1, 2, 5); ZIPV (model 8) "
                     f"is not mapped, as on import")

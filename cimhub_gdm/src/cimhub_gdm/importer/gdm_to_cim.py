"""GDM DistributionSystem → cim18v17 FeederModel, built through CIM-Builder (builder-native, D11).

Every GDM class sits in exactly one list: the shell, ``ORDER`` (mapped, in build order), ``INLINE`` (read through its
parent), ``UNTRANSCRIBED`` (no CIM home) or ``PENDING`` (a later phase or a builder). ``check_coverage`` raises on
anything else before a single object is built.
"""

from __future__ import annotations

import logging

from cimgraph.models import FeederModel
from cimhub_core.base import FormatImporter
from gdm.distribution import common as M
from gdm.distribution import components as C
from gdm.distribution import controllers as K
from gdm.distribution import equipment as E
from infrasys import Component

from cimhub_gdm.importer import bus, source, switch
from cimhub_gdm.importer.network import (FIELDS_DistributionFeeder, FIELDS_DistributionSubstation,
                                         new_network)
from cimhub_gdm.importer.shared import check_names, components

log = logging.getLogger(__name__)

#: Built by ``new_network``, before ``ORDER``.
SHELL = {
    C.DistributionSubstation: FIELDS_DistributionSubstation,
    C.DistributionFeeder: FIELDS_DistributionFeeder,
}

#: (class, add function, FIELDS), in build order (GDM_MAPPING.md §1).
ORDER = [
    (C.DistributionBus, bus.add_bus, bus.FIELDS_DistributionBus),
    (C.DistributionVoltageSource, source.add_source, source.FIELDS_DistributionVoltageSource),
    (C.MatrixImpedanceSwitch, switch.add_switch, switch.FIELDS_MatrixImpedanceSwitch),
    (C.SequenceImpedanceSwitch, switch.add_switch, switch.FIELDS_SequenceImpedanceSwitch),
    (C.MatrixImpedanceFuse, switch.add_switch, switch.FIELDS_MatrixImpedanceFuse),
    (C.MatrixImpedanceRecloser, switch.add_switch, switch.FIELDS_MatrixImpedanceRecloser),
]

#: Read through their parent; each must have one.
INLINE = {
    E.VoltageSourceEquipment: source.FIELDS_VoltageSourceEquipment,
    E.PhaseVoltageSourceEquipment: source.FIELDS_PhaseVoltageSourceEquipment,
    E.MatrixImpedanceSwitchEquipment: switch.FIELDS_MatrixImpedanceSwitchEquipment,
    E.SequenceImpedanceSwitchEquipment: switch.FIELDS_SequenceImpedanceSwitchEquipment,
    E.CircuitBreakerEquipment: switch.FIELDS_CircuitBreakerEquipment,
    E.DisconnectorEquipment: switch.FIELDS_DisconnectorEquipment,
    E.MatrixImpedanceFuseEquipment: switch.FIELDS_MatrixImpedanceFuseEquipment,
    E.MatrixImpedanceRecloserEquipment: switch.FIELDS_MatrixImpedanceRecloserEquipment,
    K.DistributionSwitchController: switch.FIELDS_DistributionSwitchController,
}

#: No CIM home (GDM_MAPPING.md §10).
UNTRANSCRIBED = {
    M.Location: "bus coordinates: ConnectivityNode is not a PowerSystemResource (B14)",
    M.VoltageLimitSet: "bus voltage limits: an OperationalLimitSet hangs on equipment, not a ConnectivityNode",
    M.ThermalLimitSet: "no GDM field references it",
    M.TimeCurrentCurve: "no FuseCharacteristicCurve in cim18v17",
    M.Curve: "until the Curve builder (B12)",
    E.RecloserControllerEquipment: "no RecloseSequence in cim18v17",
    K.DistributionRecloserController: "no RecloseSequence in cim18v17",
}

_PHASE_2 = "Phase 2 (lines, loads, capacitors)"
_PHASE_3 = "Phase 3 (transformers, regulators)"
_PHASE_4 = "Phase 4 (DER, reactors)"

#: Not mapped yet: the phase or the builder each waits for.
PENDING = {
    C.GeometrySwitch: _PHASE_2,
    C.MatrixImpedanceBranch: _PHASE_2,
    C.SequenceImpedanceBranch: _PHASE_2,
    C.GeometryBranch: _PHASE_2,
    E.MatrixImpedanceBranchEquipment: _PHASE_2,
    E.SequenceImpedanceBranchEquipment: _PHASE_2,
    E.GeometryBranchEquipment: _PHASE_2,
    E.BareConductorEquipment: _PHASE_2,
    E.ConcentricCableEquipment: _PHASE_2,
    C.DistributionLoad: _PHASE_2,
    E.LoadEquipment: _PHASE_2,
    E.PhaseLoadEquipment: _PHASE_2,
    C.DistributionCapacitor: _PHASE_2,
    E.CapacitorEquipment: _PHASE_2,
    E.PhaseCapacitorEquipment: _PHASE_2,
    K.VoltageCapacitorController: _PHASE_2,
    K.CurrentCapacitorController: _PHASE_2,
    K.ActivePowerCapacitorController: _PHASE_2,
    K.ReactivePowerCapacitorController: _PHASE_2,
    K.DailyTimedCapacitorController: _PHASE_2,
    C.DistributionTransformer: _PHASE_3,
    C.DistributionRegulator: _PHASE_3,
    E.DistributionTransformerEquipment: _PHASE_3,
    E.PowerTransformerEquipment: _PHASE_3,
    E.WindingEquipment: _PHASE_3,
    K.RegulatorController: _PHASE_3,
    C.DistributionSolar: _PHASE_4,
    C.DistributionBattery: _PHASE_4,
    C.DistributionReactor: _PHASE_4,
    E.SolarEquipment: _PHASE_4,
    E.BatteryEquipment: _PHASE_4,
    E.InverterEquipment: _PHASE_4,
    E.ReactorEquipment: _PHASE_4,
    K.InverterController: _PHASE_4,
    K.CapacityFirmingControlSetting: _PHASE_4,
    K.DemandChargeControlSetting: _PHASE_4,
    K.PeakShavingBaseLoadingControlSetting: _PHASE_4,
    K.PowerfactorControlSetting: _PHASE_4,
    K.SelfConsumptionControlSetting: _PHASE_4,
    K.TimeBasedControlSetting: _PHASE_4,
    K.TimeOfUseControlSetting: _PHASE_4,
    K.VoltVarControlSetting: _PHASE_4,
    K.VoltWattControlSetting: _PHASE_4,
    E.EarthingSwitchEquipment: "the GroundDisconnector builder (B19)",
}


def classified() -> set[type]:
    """Every GDM class in a list."""
    return set(SHELL) | {cls for cls, _, _ in ORDER} | set(INLINE) | set(UNTRANSCRIBED) | set(PENDING)


class GdmImporter(FormatImporter):
    """GDM ``DistributionSystem`` → cim18v17 ``FeederModel`` through CIM-Builder keyword methods."""

    model_cls = FeederModel

    def to_cim(self, model, *, network=None) -> FeederModel:
        """Import ``model`` (a GDM ``DistributionSystem``) into a new FeederModel."""
        if network is not None:
            raise ValueError("GdmImporter builds its own network; importing into an existing one is not supported")
        system = model
        check_coverage(system)
        drop_time_series(system)
        check_names(_named_components(system))

        feeder_model = new_network(system)
        for cls, add, fields in ORDER:
            for component in components(system, cls):
                log_untranscribed(fields, component)
                add(feeder_model, component, system.name)
        return feeder_model


def gdm_to_cim(system) -> FeederModel:
    """Import a GDM ``DistributionSystem`` into a cim18v17 FeederModel."""
    return GdmImporter().to_cim(system)


def check_coverage(system) -> None:
    """Raise, naming each class and count, on a pending, unclassified or orphan class, or supplemental attributes."""
    counts: dict[type, int] = {}
    for component in system.iter_all_components():
        counts[type(component)] = counts.get(type(component), 0) + 1
    known = classified()
    problems = [f"{cls.__name__} x{n}: pending, {PENDING[cls]}" for cls, n in counts.items() if cls in PENDING]
    problems += [f"{cls.__name__} x{n}: not classified" for cls, n in counts.items() if cls not in known]
    referenced = _referenced_uuids(system)
    for cls in INLINE:
        orphans = [c for c in components(system, cls) if c.uuid not in referenced]
        if orphans:
            problems.append(f"{cls.__name__} x{len(orphans)}: inline equipment with no parent")
    if system.get_num_supplemental_attributes():
        problems.append(f"{system.get_num_supplemental_attributes()} supplemental attributes: not mapped")
    if problems:
        raise ValueError("GDM system cannot be imported:\n  " + "\n  ".join(sorted(problems)))


def _referenced_uuids(system) -> set:
    """UUIDs of every component reachable through the fields of a non-inline component.

    infrasys ``list_parent_components`` misses components held in lists (``VoltageSourceEquipment.sources``) and
    components nested in an equipment (a switch controller), so the references are walked here.
    """
    referenced = set()
    stack = [c for c in system.iter_all_components() if type(c) not in INLINE]
    while stack:
        parent = stack.pop()
        for name in type(parent).model_fields:
            value = getattr(parent, name)
            for item in value if isinstance(value, (list, tuple)) else [value]:
                if isinstance(item, Component) and item.uuid not in referenced:
                    referenced.add(item.uuid)
                    stack.append(item)
    return referenced


def drop_time_series(system) -> None:
    """Log one WARNING listing every time series, which the first pass drops (OPEN_DECISIONS 2)."""
    dropped = []
    for component in system.iter_all_components():
        if system.has_time_series(component):
            for metadata in system.list_time_series_metadata(component):
                dropped.append(f"{type(component).__name__} {component.name!r}: {metadata.name} "
                               f"({type(metadata).__name__}, {metadata.time_series_uuid}, {metadata.features})")
    if dropped:
        log.warning("dropping %d time series (no CIM schedule profile yet; OPEN_DECISIONS 2):\n  %s",
                    len(dropped), "\n  ".join(dropped))


def log_untranscribed(fields, component) -> None:
    """DEBUG: the component's untranscribed values, for a caller's log file (OPEN_DECISIONS 11)."""
    if not log.isEnabledFor(logging.DEBUG):
        return
    values = [f"{slot}={getattr(component, slot)!r:.80}" for slot, field in fields.items()
              if field.kind == "untranscribed" and getattr(component, slot) not in (None, [], "")]
    if values:
        log.debug("%s %r untranscribed: %s", type(component).__name__, component.name, ", ".join(values))


def _named_components(system) -> list:
    """Every component whose name becomes an mRID."""
    named = [c for cls in SHELL for c in components(system, cls)]
    for cls, _, _ in ORDER:
        named += components(system, cls)
    return named

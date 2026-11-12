"""GDM DistributionSystem → cim18v17 FeederModel, built through CIM-Builder (builder-native, D11).

Every GDM class sits in exactly one list: the shell, ``ORDER`` (mapped, in build order), ``INLINE`` (read through its
parent), ``UNTRANSCRIBED`` (no CIM home) or ``PENDING`` (a later phase or a builder). ``check_coverage`` raises on
anything else before a single object is built.
"""

from __future__ import annotations

import logging

from cimgraph.models import FeederModel
from cimhub_core.base import FormatImporter
from gdm.systems.distribution import common as M
from gdm.systems.distribution import components as C
from gdm.systems.distribution import controllers as K
from gdm.systems.distribution import equipment as E
from infrasys import Component

from cimbuilder.object_builder.schedule import TIME_POINT_CLASS

from cimhub_gdm.importer import (
    bus,
    capacitor,
    der,
    line,
    load,
    reactor,
    regulator,
    source,
    switch,
    time_series,
    transformer,
)
from cimhub_gdm.importer.network import FIELDS_DistributionFeeder, FIELDS_DistributionSubstation, new_network
from cimhub_gdm.importer.shared import Naming, components, name_clashes

log = logging.getLogger(__name__)

#: Built by ``new_network``, before ``ORDER``.
SHELL = {
    C.DistributionSubstation: FIELDS_DistributionSubstation,
    C.DistributionFeeder: FIELDS_DistributionFeeder,
}

#: (class, add function, FIELDS), in build order (GDM_MAPPING.md §1).
ORDER = [
    (C.DistributionBus, bus.add_bus, bus.FIELDS_DistributionBus),
    (E.BareConductorEquipment, line.add_wire, line.FIELDS_BareConductorEquipment),
    (E.ConcentricCableEquipment, line.add_cable, line.FIELDS_ConcentricCableEquipment),
    (E.GeometryBranchEquipment, line.add_geometry, line.FIELDS_GeometryBranchEquipment),
    (E.MatrixImpedanceBranchEquipment, line.add_matrix_impedance, line.FIELDS_MatrixImpedanceBranchEquipment),
    (E.SequenceImpedanceBranchEquipment, line.add_sequence_impedance, line.FIELDS_SequenceImpedanceBranchEquipment),
    (E.DistributionTransformerEquipment, transformer.add_tank_configuration,
     transformer.FIELDS_DistributionTransformerEquipment),
    (E.PowerTransformerEquipment, transformer.add_tank_configuration, transformer.FIELDS_PowerTransformerEquipment),
    (C.DistributionVoltageSource, source.add_source, source.FIELDS_DistributionVoltageSource),
    (C.MatrixImpedanceSwitch, switch.add_switch, switch.FIELDS_MatrixImpedanceSwitch),
    (C.SequenceImpedanceSwitch, switch.add_switch, switch.FIELDS_SequenceImpedanceSwitch),
    (C.GeometrySwitch, switch.add_switch, switch.FIELDS_GeometrySwitch),
    (C.MatrixImpedanceFuse, switch.add_switch, switch.FIELDS_MatrixImpedanceFuse),
    (C.MatrixImpedanceRecloser, switch.add_switch, switch.FIELDS_MatrixImpedanceRecloser),
    (C.MatrixImpedanceBranch, line.add_line, line.FIELDS_MatrixImpedanceBranch),
    (C.SequenceImpedanceBranch, line.add_line, line.FIELDS_SequenceImpedanceBranch),
    (C.GeometryBranch, line.add_line, line.FIELDS_GeometryBranch),
    (C.DistributionTransformer, transformer.add_transformer, transformer.FIELDS_DistributionTransformer),
    (C.DistributionRegulator, regulator.add_regulator, regulator.FIELDS_DistributionRegulator),
    (C.DistributionReactor, reactor.add_reactor, reactor.FIELDS_DistributionReactor),
    (C.DistributionLoad, load.add_load, load.FIELDS_DistributionLoad),
    (C.DistributionCapacitor, capacitor.add_capacitor, capacitor.FIELDS_DistributionCapacitor),
    (C.DistributionSolar, der.add_solar, der.FIELDS_DistributionSolar),
    (C.DistributionBattery, der.add_battery, der.FIELDS_DistributionBattery),
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
    E.LoadEquipment: load.FIELDS_LoadEquipment,
    E.PhaseLoadEquipment: load.FIELDS_PhaseLoadEquipment,
    E.CapacitorEquipment: capacitor.FIELDS_CapacitorEquipment,
    E.PhaseCapacitorEquipment: capacitor.FIELDS_PhaseCapacitorEquipment,
    K.VoltageCapacitorController: capacitor.FIELDS_VoltageCapacitorController,
    K.CurrentCapacitorController: capacitor.FIELDS_CurrentCapacitorController,
    K.ActivePowerCapacitorController: capacitor.FIELDS_ActivePowerCapacitorController,
    K.ReactivePowerCapacitorController: capacitor.FIELDS_ReactivePowerCapacitorController,
    E.WindingEquipment: transformer.FIELDS_WindingEquipment,
    K.RegulatorController: regulator.FIELDS_RegulatorController,
    E.SolarEquipment: der.FIELDS_SolarEquipment,
    E.BatteryEquipment: der.FIELDS_BatteryEquipment,
    E.InverterEquipment: der.FIELDS_InverterEquipment,
    E.ReactorEquipment: reactor.FIELDS_ReactorEquipment,
}

#: Inline classes whose name becomes an mRID (an AssetInfo built the first time a parent names it).
NAMED_INLINE = (E.BatteryEquipment, E.InverterEquipment)

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

_INVERTER_CONTROL = "inverter controls: function_block_control has classes but no builder (OPEN_DECISIONS 12)"

#: Not mapped yet: the decision or the builder each waits for.
PENDING = {
    K.DailyTimedCapacitorController: "a schedule: no CIM time-of-day control yet (OPEN_DECISIONS 12)",
    K.InverterController: _INVERTER_CONTROL,
    K.CapacityFirmingControlSetting: _INVERTER_CONTROL,
    K.DemandChargeControlSetting: _INVERTER_CONTROL,
    K.PeakShavingBaseLoadingControlSetting: _INVERTER_CONTROL,
    K.PowerfactorControlSetting: _INVERTER_CONTROL,
    K.SelfConsumptionControlSetting: _INVERTER_CONTROL,
    K.TimeBasedControlSetting: _INVERTER_CONTROL,
    K.TimeOfUseControlSetting: _INVERTER_CONTROL,
    K.VoltVarControlSetting: _INVERTER_CONTROL,
    K.VoltWattControlSetting: _INVERTER_CONTROL,
    E.EarthingSwitchEquipment: "the GroundDisconnector builder (B19)",
}


def classified() -> set[type]:
    """Every GDM class in a list."""
    return set(SHELL) | {cls for cls, _, _ in ORDER} | set(INLINE) | set(UNTRANSCRIBED) | set(PENDING)


class GdmImporter(FormatImporter):
    """GDM ``DistributionSystem`` → cim18v17 ``FeederModel`` through CIM-Builder keyword methods.

    ``time_points``: a dict the caller owns, keyed by TimePoint class name. Given one, each load's P/Q series becomes
    an ``EnergyConnectionSchedule`` in the network and its points a ``pyarrow.Table`` under
    ``time_points['EnergyConnectionTimePoint']`` (TIMESERIES_NEEDS.md T6; ``write_time_points`` writes it beside the
    XML). Without one, every series is dropped with one WARNING, as before schedules existed.
    """

    model_cls = FeederModel

    def __init__(self, time_points: dict | None = None):
        self.time_points = time_points

    def to_cim(self, model, *, network=None) -> FeederModel:
        """Import ``model`` (a GDM ``DistributionSystem``) into a new FeederModel."""
        if network is not None:
            raise ValueError("GdmImporter builds its own network; importing into an existing one is not supported")
        system = model
        check_coverage(system)
        if self.time_points is None:
            drop_time_series(system)
        naming = Naming(system.name, name_clashes(_named_components(system)))

        feeder_model = new_network(system, naming)
        for cls, add, fields in ORDER:
            for component in components(system, cls):
                log_untranscribed(fields, component)
                add(feeder_model, component, naming)
        if self.time_points is not None:
            points = time_series.add_time_series(feeder_model, system, naming)
            if points is not None:
                self.time_points[TIME_POINT_CLASS] = points
        return feeder_model


def gdm_to_cim(system, *, time_points: dict | None = None) -> FeederModel:
    """Import a GDM ``DistributionSystem`` into a cim18v17 FeederModel; ``time_points`` as ``GdmImporter``."""
    return GdmImporter(time_points).to_cim(system)


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
    """Log one WARNING listing every time series, dropped when the caller keeps no time points (OPEN_DECISIONS 2)."""
    dropped = [time_series.describe(component, metadata)
               for component in system.iter_all_components() if system.has_time_series(component)
               for metadata in time_series.time_series_metadata(system, component)]
    time_series.warn_dropped(dropped, "no time_points given to keep them in")


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
    for cls in [cls for cls, _, _ in ORDER] + list(NAMED_INLINE):
        named += components(system, cls)
    return named
